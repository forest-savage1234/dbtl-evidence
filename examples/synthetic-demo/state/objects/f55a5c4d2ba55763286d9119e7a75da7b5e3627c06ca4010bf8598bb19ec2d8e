"""Version graph queries. Metabolic networks themselves may have cycles;
evidence derivations in this instrument must point to existing earlier versions.
"""
from collections import deque

from .core import IntegrityError


def closure(db, version_id, *, downstream=False):
    db.get(version_id)
    follow, join = ("dependent_id", "source_id") if downstream else ("source_id", "dependent_id")
    sql = f"""WITH RECURSIVE links AS MATERIALIZED (SELECT * FROM edges),
        reach(id) AS (SELECT ? UNION
          SELECT links.{follow} FROM links JOIN reach ON links.{join}=reach.id)
        SELECT id FROM reach WHERE id<>? ORDER BY id"""
    return [db.get(row[0]) for row in db.conn.execute(sql, (version_id, version_id))]


def impact(db, source_version, *, max_path_steps=256):
    """Return one shortest explanation per reachable version; no duplicate alerts."""
    if type(max_path_steps) is not int or max_path_steps < 1:
        raise IntegrityError("Explanation path limit must be a positive integer")
    records = closure(db, source_version, downstream=True)
    wanted = {r["id"] for r in records}
    adjacency = {}
    for row in db.conn.execute("SELECT source_id, dependent_id, role FROM edges ORDER BY dependent_id,role"):
        if row["dependent_id"] in wanted:
            adjacency.setdefault(row["source_id"], []).append((row["dependent_id"], row["role"]))
    previous, depths = {source_version: None}, {source_version: 0}
    queue = deque([source_version])
    while queue:
        source = queue.popleft()
        for target, role in adjacency.get(source, []):
            if target not in previous:
                previous[target] = (source, role)
                depths[target] = depths[source] + 1
                queue.append(target)
    if set(previous) - {source_version} != wanted:
        raise IntegrityError("SQL reachability and path reconstruction disagree")
    result = []
    for record in records:
        target, path = record["id"], []
        while previous[target] is not None and len(path) < max_path_steps:
            source, role = previous[target]
            path.append({"source": source, "dependent": target, "role": role})
            target = source
        result.append({"record": record, "path": list(reversed(path)),
                       "path_complete": depths[record["id"]] <= max_path_steps,
                       "total_steps": depths[record["id"]]})
    return result


def verify_closure(db, version_id):
    records = [db.get(version_id), *closure(db, version_id)]
    checked = set()
    for record in records:
        for key in record["artifacts"]:
            if key not in checked:
                db.objects.verify(key)
                checked.add(key)
    return {"versions": len(records), "artifacts": len(checked)}


def outdated_sources(db, version_id):
    """Report superseded dependencies; old historical records remain reproducible."""
    return [{"old": r["id"], "current": db.latest(r["entity_id"])["id"], "entity_id": r["entity_id"]}
            for r in [db.get(version_id), *closure(db, version_id)]
            if db.latest(r["entity_id"])["id"] != r["id"]]
