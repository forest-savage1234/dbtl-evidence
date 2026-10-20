"""Import the verified original release ancestry into a new publication repository.

Only --publish changes remote refs. The operation is fast-forward and atomic;
it retains the publication tree and never force-updates existing work.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY="forest-savage1234/dbtl-evidence"
RELEASE="512d2c26804f61795a17c52330281727a2826848"


def git(*args,check=True):
    result=subprocess.run(["git",*args],cwd=ROOT,capture_output=True,text=True)
    if check and result.returncode:raise RuntimeError("git "+args[0]+" failed: "+result.stderr.strip())
    return result


def run(publish=False):
    config=json.loads((ROOT/"evidence/github-history-publication.json").read_text())
    if config["schema"]!="dbtl-history-publication/1" or config["repository"]!=REPOSITORY or config["release_commit"]!=RELEASE:
        raise ValueError("Unexpected publication identity")
    if os.environ.get("GITHUB_REPOSITORY",REPOSITORY)!=REPOSITORY:raise ValueError("Wrong target repository")
    bundle=ROOT/"history.bundle"
    if sha256(bundle.read_bytes()).hexdigest()!=config["bundle_sha256"]:raise ValueError("History bundle bytes differ")
    if git("status","--porcelain","--untracked-files=no").stdout.strip():raise ValueError("Tracked publication files have uncommitted changes")
    git("bundle","verify",str(bundle))
    git("fetch",str(bundle),"refs/heads/main:refs/remotes/dbtl-release/main","refs/tags/*:refs/tags/*")
    if git("rev-parse","refs/remotes/dbtl-release/main").stdout.strip()!=RELEASE:raise ValueError("Wrong original release head")
    for tag,expected in config["tags"].items():
        if git("rev-parse","refs/tags/"+tag).stdout.strip()!=expected:raise ValueError("Original tag differs: "+tag)
    receipt=json.loads(git("show",RELEASE+":"+config["source_gate"]).stdout)
    if receipt["status"]!="passed" or receipt["tests_run"]!=147 or receipt["failures"] or receipt["skipped"]:
        raise ValueError("Incomplete original gate")
    for name,expected in receipt["source_hashes"].items():
        if sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError("Tested source changed: "+name)
    if not publish:return {"status":"checked","source_hashes":len(receipt["source_hashes"]),"original_tags":len(config["tags"])}
    if git("symbolic-ref","--short","HEAD").stdout.strip()!="main":raise ValueError("Publication requires main")
    git("fetch","origin","main")
    remote=git("rev-parse","refs/remotes/origin/main").stdout.strip()
    remote_tags={line.split()[1].removeprefix("refs/tags/"):line.split()[0] for line in git("ls-remote","--tags","origin").stdout.splitlines()}
    for tag,expected in config["tags"].items():
        if tag in remote_tags and remote_tags[tag]!=expected:raise ValueError("Refuse to replace remote tag: "+tag)
    if git("merge-base","--is-ancestor",RELEASE,remote,check=False).returncode==0:
        if all(remote_tags.get(t)==v for t,v in config["tags"].items()):return {"status":"already_published","commit":remote,"original_tags":len(config["tags"])}
        raise ValueError("Existing ancestry has incomplete tags; review before repair")
    if git("rev-parse","HEAD").stdout.strip()!=remote:raise ValueError("Remote main changed; use a fresh checkout, no overwrite attempted")
    git("-c","user.name=github-actions[bot]","-c","user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "merge","--allow-unrelated-histories","--strategy=ours","--no-edit","-m","Preserve original DBTL release ancestry and tags",RELEASE)
    git("push","--atomic","origin","HEAD:refs/heads/main",*("refs/tags/"+t+":refs/tags/"+t for t in sorted(config["tags"])))
    return {"status":"published","commit":git("rev-parse","HEAD").stdout.strip(),"original_tags":len(config["tags"])}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--publish",action="store_true");args=parser.parse_args()
    print(json.dumps(run(args.publish),indent=2))
