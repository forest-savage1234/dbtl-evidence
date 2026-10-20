import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction

from dbtl.core import Instrument,IntegrityError
from dbtl.demo2 import seed,add_culture,support,run_demo2
from dbtl.packets import freeze,replay,status,render
from dbtl.pools import snapshot,compute_snapshot
from dbtl.watches import watch,status as watch_status
from dbtl.assessments import assess
from dbtl.backup import backup,restore
from dbtl.uncertainty import propagate
from .test_assessments import dimensions
from .test_pools import register,make_pool


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=Instrument(self.root/"state")

    def tearDown(self):self.db.close();self.temp.cleanup()

    def setup_packet(self,enrich=True):
        s=seed(self.db,self.root/"inputs",enrich=enrich)
        p=freeze(self.db,"packet:test",s["cohort"]["id"],s["policy"]["id"],s["snapshot"]["id"])
        return s,p

    def test_scoped_packet_is_replayable_with_two_assessed_units_per_strain(self):
        s,p=self.setup_packet();result=p["payload"]["result"]
        self.assertEqual(result["state"],"ready_for_scoped_human_review")
        self.assertEqual({r["strain_id"]:r["mean_g_l"] for r in result["summaries"]},{"demo2:strain:A":"0.6","demo2:strain:B":"0.5"})
        self.assertTrue(replay(self.db,p["id"])["ok"]);self.assertFalse(status(self.db,p["id"])["requires_reassessment"])
        self.db.capture("advance:test","advance",{"packet_version":p["id"],"selected_strain_versions":[s["strains"]["A"]["id"]],"rationale":"SYNTHETIC reviewed selection"})

    def test_missing_evidence_withholds_ranks_and_blocks_selection(self):
        s,p=self.setup_packet(enrich=False);result=p["payload"]["result"]
        self.assertEqual(result["state"],"withheld");self.assertTrue(all("descriptive_rank" not in r for r in result["summaries"]))
        self.assertTrue({i["scope"] for i in result["issues"]}>={"measurement","physical_units","genotype","assay","process"})
        with self.assertRaises(IntegrityError):self.db.capture("advance:bad","advance",{"packet_version":p["id"],"selected_strain_versions":[s["strains"]["A"]["id"]],"rationale":"Cannot bypass missing evidence"})

    def test_new_candidate_outside_dependency_graph_reopens_packet(self):
        s,p=self.setup_packet();w=watch(self.db,"watch:test",p["id"],s["snapshot"]["id"],basis="SYNTHETIC")
        add_culture(self.db,self.root/"inputs","outsider",s["strains"]["A"],s["protocol"],s["extraction"],s["calibration"],s["context"],"3010",enrich=False)
        self.assertTrue(watch_status(self.db,w["id"])["requires_reassessment"])
        new=freeze(self.db,"packet:omits-new",s["cohort"]["id"],s["policy"]["id"],s["snapshot"]["id"])
        self.assertEqual(new["payload"]["result"]["state"],"withheld");self.assertTrue(replay(self.db,p["id"])["ok"])

    def test_new_conflicting_review_outside_old_closure_reopens_watch(self):
        s,p=self.setup_packet();w=watch(self.db,"watch:test",p["id"],s["snapshot"]["id"],basis="SYNTHETIC")
        ds=dimensions();ds["measurement"].update(status="conflict",basis="SYNTHETIC independent reviewer disagreement")
        assess(self.db,"assessment:new-conflict",s["parts"][0]["measurement"],ds,criteria_id="synthetic:2")
        self.assertTrue(status(self.db,p["id"])["requires_reassessment"]);self.assertTrue(watch_status(self.db,w["id"])["requires_reassessment"])
        self.assertTrue(replay(self.db,p["id"])["ok"])

    def test_unknown_access_and_withdrawal_withhold_without_claiming_biological_falsity(self):
        s,p=self.setup_packet()
        self.db.capture("availability:unknown","availability",{"measurement_version":s["parts"][0]["measurement"],"state":"inaccessible","category":"unknown","basis":"SYNTHETIC unresolved upstream access"})
        self.assertTrue(status(self.db,p["id"])["requires_reassessment"])
        snap=snapshot(self.db,"pool:unknown",s["pool"]["id"])
        new=freeze(self.db,"packet:unknown",s["cohort"]["id"],s["policy"]["id"],snap["id"])
        self.assertEqual(new["payload"]["result"]["state"],"withheld")

    def test_fresh_snapshot_cannot_reintroduce_a_withdrawn_reading_into_ranked_means(self):
        s,p=self.setup_packet();v=s["parts"][0]["measurement"]
        self.db.capture("availability:withdrawn","availability",{"measurement_version":v,"state":"withdrawn","category":"measurement","basis":"SYNTHETIC withdrawal"})
        snap=snapshot(self.db,"pool:withdrawn",s["pool"]["id"])
        new=freeze(self.db,"packet:withdrawn",s["cohort"]["id"],s["policy"]["id"],snap["id"])["payload"]["result"]
        self.assertEqual(new["state"],"withheld")
        self.assertNotIn(v,[r["measurement_version"] for r in new["measurement_checks"]])
        self.assertIn("pool:excluded",next(r["reasons"] for r in new["excluded"] if r["measurement_version"]==v))

    def test_unrelated_capture_does_not_reopen_packet(self):
        s,p=self.setup_packet();before=status(self.db,p["id"])
        self.db.capture("design:unrelated","design",{"name":"SYNTHETIC unrelated"})
        after=status(self.db,p["id"]);self.assertEqual(before["fingerprint"],after["fingerprint"]);self.assertFalse(after["requires_reassessment"])

    def test_forged_result_and_past_capture_watermark_rejected(self):
        s,p=self.setup_packet();q=p["payload"];q["result"]["state"]="verified"
        with self.assertRaises(IntegrityError):self.db.capture("packet:forged","packet",q,artifacts=p["artifacts"])
        self.assertTrue(replay(self.db,p["id"])["ok"])

    def test_calibration_correction_preserves_history_and_blocks_new_selection(self):
        s,p=self.setup_packet();c=s["calibration"]
        self.db.capture(c["entity_id"],"calibration",{**c["payload"],"slope":"4"},expected=c["id"],reason="SYNTHETIC correction")
        self.assertTrue(replay(self.db,p["id"])["ok"]);self.assertTrue(status(self.db,p["id"])["requires_reassessment"])
        with self.assertRaises(IntegrityError):self.db.capture("advance:stale","advance",{"packet_version":p["id"],"selected_strain_versions":[s["strains"]["A"]["id"]],"rationale":"SYNTHETIC stale attempt"})

    def test_backup_restore_preserves_scoped_packet_replay(self):
        s,p=self.setup_packet();archive=self.root/"backup.zip";backup(self.db,archive);restore(archive,self.root/"restored")
        with Instrument(self.root/"restored") as db:self.assertTrue(replay(db,p["id"])["ok"])

    def test_report_escapes_retained_user_content(self):
        s,p=self.setup_packet();policy=s["policy"]
        changed=self.db.capture(policy["entity_id"],"packet_policy",{**policy["payload"],"basis":"<script>attack</script>"},expected=policy["id"],reason="SYNTHETIC unsafe text")
        packet=freeze(self.db,"packet:unsafe-text",s["cohort"]["id"],changed["id"],s["snapshot"]["id"])
        text=render(self.db,packet["id"])
        self.assertNotIn("<script",text);self.assertIn("script-src 'none'",text)
        self.assertIn("&lt;script&gt;",text)

    def test_cli_packet_status_report_watch_and_reference_receipt(self):
        s,p=self.setup_packet();command=[sys.executable,"-m","dbtl","--root",str(self.root/"state")]
        for args in [["packet-replay",p["id"]],["packet-status",p["id"]],["packet-report",p["id"],"--output",str(self.root/"packet.html")],
                     ["assessment-summary",s["parts"][0]["measurement"]],["pool-replay",s["snapshot"]["id"]],
                     ["watch-add","watch:cli",p["id"],s["snapshot"]["id"],"--basis","SYNTHETIC CLI review"]]:
            result=subprocess.run(command+args,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIsInstance(json.loads(result.stdout),dict)
        fixture=Path(__file__).resolve().parents[1]/"examples/claim-review-synthetic"
        result=subprocess.run(command+["claim-import","reference:cli",str(fixture/"report.json"),str(fixture/"source.csv"),"--origin","synthetic_fixture","--intended-use","Reference only","--target-domain","demo2:flask","--reason","SYNTHETIC CLI handoff"],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr);reference=json.loads(result.stdout)
        q=freeze(self.db,"packet:reference",s["cohort"]["id"],s["policy"]["id"],s["snapshot"]["id"],reference_versions=[reference["id"]])
        self.assertEqual(q["payload"]["result"]["summaries"],p["payload"]["result"]["summaries"])
        self.assertTrue(all(x["status"]=="open" for x in q["payload"]["result"]["literature_references"][0]["consumer_dimensions"].values()))

    def test_aliases_across_strains_and_duplicate_input_versions_cannot_establish_replication(self):
        from dbtl.units import assign,assignment_id,summarize
        s,p=self.setup_packet();a,b=s["parts"][0],s["parts"][2]
        old=self.db.latest(assignment_id(self.db,b["culture"]["id"]));unit=self.db.latest(assignment_id(self.db,a["culture"]["id"]))["payload"]["unit_version"]
        assign(self.db,b["culture"]["id"],unit,basis="SYNTHETIC conflicting physical mapping",expected=old["id"],reason="SYNTHETIC challenge")
        self.assertTrue(status(self.db,p["id"])["requires_reassessment"])
        with self.assertRaises(IntegrityError):summarize(self.db,[a["measurement"],a["measurement"]])

    def test_synthetic_campaign_moves_to_new_candidate_and_reopens_on_unknown_access(self):
        result=run_demo2(self.root/"demo")
        self.assertEqual(result["initial_top"],"demo2:strain:A");self.assertEqual(result["reassessed_top"],"demo2:strain:C")
        self.assertEqual(len(result["added_candidates"]),2)
        self.assertTrue(result["audit"]["ok"] and result["historical_replay"]["ok"] and result["reassessed_replay"]["ok"])

    def test_malformed_new_contracts_fail_cleanly_without_writes(self):
        count=len(self.db.versions())
        for kind in ["assessment","pool","pool_snapshot","watch","watch_review","availability","quantity","quantity_result","experimental_unit","unit_assignment","genotype_observation","assay_profile","uncertainty_result","trajectory","process_policy","literature_evidence","packet_policy","packet","advance"]:
            for p in [{},{"dimensions":None},{"candidates":None}]:
                with self.subTest(kind=kind,p=p),self.assertRaises(IntegrityError):self.db.capture("malformed:"+kind,kind,p)
        self.assertEqual(len(self.db.versions()),count)


class IndependentOracleTests(unittest.TestCase):
    def test_seeded_rank_one_covariance_matches_independent_exact_oracle(self):
        rng=random.Random(20261020)
        for _ in range(40):
            v=[rng.randrange(-4,5) for _ in range(4)];c=[[str(a*b) for b in v] for a in v]
            result=propagate({"response":"10","intercept":"2","slope":"2","dilution":"3"},c)
            expected=(Fraction(3,2)*v[0]-Fraction(3,2)*v[1]-6*v[2]+4*v[3])**2
            self.assertEqual(Fraction(result["variance"]),expected)

    def test_seeded_pool_selection_matches_independent_set_oracle(self):
        rng=random.Random(209);expected=set();unknown=set()
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with Instrument(root/"state") as db:
                for i in range(20):
                    medium=rng.choice(["target","other",None]);_,m=register(db,root,str(i),medium=medium)
                    if medium=="target":expected.add(m)
                    if medium is None:unknown.add(m)
                pool=make_pool(db,medium="target");rows=compute_snapshot(db,pool["id"])["candidates"]
                self.assertEqual({r["measurement_version"] for r in rows if r["status"]=="included"},expected)
                self.assertEqual({r["measurement_version"] for r in rows if r["status"]=="uncertain"},unknown)
