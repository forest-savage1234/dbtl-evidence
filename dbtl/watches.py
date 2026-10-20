"""Read-only reconciliation of watched decisions against evolving registered pools."""
from .core import IntegrityError, digest
from .graph import outdated_sources, verify_closure
from .pools import compute_snapshot, replay_snapshot

REFS = {"availability": {"measurement_version": ("measurement", {"measurement"})},
        "watch": {"target_version": ("target", {"dataset", "decision", "model", "packet", "advance"}),
                  "snapshot_version": ("snapshot", {"pool_snapshot"})},
        "watch_review": {"watch_version": ("watch", {"watch"})}}


def watch_dependencies(kind, payload):
    return [{"role": role, "version_id": payload[field]} for field, (role, _) in REFS[kind].items() if field in payload]


def validate_watch_record(db, kind, payload, deps):
    for field, (_, kinds) in REFS[kind].items():
        if not isinstance(payload.get(field), str) or db.get(payload[field])["kind"] not in kinds:
            raise IntegrityError("Invalid watch reference: "+field)
    if deps != sorted(watch_dependencies(kind, payload), key=lambda d: (d["role"],d["version_id"])):
        raise IntegrityError("Watch dependencies differ from declared references")
    if not isinstance(payload.get("basis"), str) or not payload["basis"].strip():
        raise IntegrityError("A scoped human rationale is required")
    if kind == "availability":
        if set(payload) != {"measurement_version", "state", "category", "basis"} or payload["state"] not in {"available", "withdrawn", "inaccessible"} or payload["category"] not in {"bibliographic", "measurement", "access", "unknown"}:
            raise IntegrityError("Invalid availability notice")
    elif kind == "watch":
        if set(payload) != {"target_version", "snapshot_version", "basis"}: raise IntegrityError("Malformed watch")
        replay_snapshot(db, payload["snapshot_version"])
    else:
        if set(payload) != {"watch_version", "fingerprint", "disposition", "basis"} or payload["disposition"] not in {"retain_historical", "retire"}:
            raise IntegrityError("Review cannot make changed evidence current")
        current=status(db,payload["watch_version"])
        if not current["requires_reassessment"] or payload["fingerprint"] != current["fingerprint"]:
            raise IntegrityError("Pool changed again; review current state")


def watch(db, entity_id, target_version, snapshot_version, *, basis, **kwargs):
    return db.capture(entity_id,"watch",{"target_version":target_version,"snapshot_version":snapshot_version,"basis":basis},**kwargs)


def status(db, watch_version):
    with db.atomic():
        record=db.get(watch_version)
        if record["kind"] != "watch": raise IntegrityError("Expected watch")
        verify_closure(db,watch_version)
        p=record["payload"]; anchor=db.get(p["snapshot_version"])["payload"]
        replay_snapshot(db,p["snapshot_version"])
        current_pool=db.latest(db.get(anchor["pool_version"])["entity_id"])
        current=compute_snapshot(db,current_pool["id"])
        old={r["entity_id"]:r for r in anchor["candidates"]}
        new={r["entity_id"]:r for r in current["candidates"]}
        included=lambda rows: {id:r for id,r in rows.items() if r["status"]=="included"}
        before,after=included(old),included(new)
        delta={"added":sorted(set(after)-set(before)),"removed":sorted(set(before)-set(after)),
               "changed":sorted(id for id in set(before)&set(after) if before[id]!=after[id]),
               "uncertain":sorted(id for id,r in new.items() if r["status"]=="uncertain"),
               "scope_changed":anchor["pool_version"]!=current_pool["id"]}
        stale=outdated_sources(db,p["target_version"])
        target=db.get(p["target_version"])
        superseded_target=db.latest(target["entity_id"])["id"]!=target["id"]
        packet_state=None
        if target["kind"] in {"packet","advance"}:
            from .packets import status as packet_status
            packet_state=packet_status(db,target["id"] if target["kind"]=="packet" else target["payload"]["packet_version"])
        pending=bool(any(delta.values()) or stale or superseded_target or packet_state and packet_state["requires_reassessment"])
        fingerprint_input={"watch":watch_version,"delta":delta,"stale":stale,"target_superseded":superseded_target,
                           "relevant_versions":{id:new[id]["measurement_version"] for id in sorted(after)}}
        if packet_state:fingerprint_input["packet_fingerprint"]=packet_state["fingerprint"]
        fingerprint=digest(fingerprint_input)
        reviews=[r["id"] for r in db.versions("watch_review",heads_only=True) if r["payload"]["watch_version"]==watch_version and r["payload"]["fingerprint"]==fingerprint]
        return {"watch_version":watch_version,"target_version":target["id"],"watermark":current["watermark"],
                "state":"pool_eligibility_unknown" if delta["uncertain"] else "reassessment_pending" if pending else "current_for_registered_pool",
                "requires_reassessment":pending,"delta":delta,"stale_dependencies":stale,"target_superseded":superseded_target,
                "fingerprint":fingerprint,"acknowledged":bool(reviews),"review_versions":reviews,"packet_status":packet_state,
                "coverage":current["coverage"],"meaning":"Review request, not automatic rejection or authorization."}


def acknowledge(db, watch_version, fingerprint, *, disposition, basis, actor):
    with db.atomic():
        return db.capture("watch-review:"+fingerprint,"watch_review",{"watch_version":watch_version,
            "fingerprint":fingerprint,"disposition":disposition,"basis":basis},actor=actor)


def pending(db, include_acknowledged=False):
    values=[status(db,r["id"]) for r in db.versions("watch",heads_only=True)]
    return [r for r in values if r["requires_reassessment"] and (include_acknowledged or not r["acknowledged"])]
