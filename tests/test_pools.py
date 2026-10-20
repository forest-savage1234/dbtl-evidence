from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.ingest import ingest_csv
from dbtl.pools import compute_snapshot, snapshot, replay_snapshot
from .support import setup_assay, write_csv


def register(db, root, name="A", **context):
    parts = setup_assay(db, name, **context)
    path = Path(root)/f"{name}.csv"
    write_csv(path, parts)
    return parts, ingest_csv(db, path)["measurement_versions"][0]


def make_pool(db, **filters):
    return db.capture("pool:test", "pool", {"entity_prefix":"measurement:",
        "filters":{"analyte_id":"demo:product", **filters}, "boundary":"registered_local_measurements_only"})


class PoolTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.db=Instrument(self.root/"state")

    def tearDown(self):
        self.db.close(); self.temp.cleanup()

    def test_new_independent_measurements_are_discovered_without_old_graph_edges(self):
        register(self.db,self.root)
        pool=make_pool(self.db); first=snapshot(self.db,"snapshot:1",pool["id"])
        _, new=register(self.db,self.root,"B")
        second=snapshot(self.db,"snapshot:2",pool["id"])
        self.assertEqual(len(first["payload"]["candidates"]),1)
        self.assertIn(new,[r["measurement_version"] for r in second["payload"]["candidates"]])
        self.assertTrue(replay_snapshot(self.db,first["id"])["ok"])

    def test_unknown_context_is_retained_as_uncertain(self):
        register(self.db,self.root,vessel=None)
        pool=make_pool(self.db,vessel="flask:250mL")
        row=compute_snapshot(self.db,pool["id"])["candidates"][0]
        self.assertEqual(row["status"],"uncertain"); self.assertIn("missing:vessel",row["reasons"])

    def test_known_mismatch_is_preserved_as_exclusion(self):
        register(self.db,self.root,batch="different")
        pool=make_pool(self.db,batch="batch:1")
        self.assertEqual(compute_snapshot(self.db,pool["id"])["candidates"][0]["status"],"excluded")

    def test_forged_membership_is_rejected(self):
        register(self.db,self.root); pool=make_pool(self.db)
        payload=compute_snapshot(self.db,pool["id"]); payload["candidates"]=[]
        with self.assertRaises(IntegrityError): self.db.capture("snapshot:forged","pool_snapshot",payload)

    def test_executable_or_unbounded_predicate_is_rejected(self):
        for changes in [{"filters":{"sql":"SELECT 1"}}, {"boundary":"all-world-literature"}]:
            payload={"entity_prefix":"measurement:","filters":{"analyte_id":"demo:product"},"boundary":"registered_local_measurements_only",**changes}
            with self.assertRaises(IntegrityError): self.db.capture("pool:bad","pool",payload)

    def test_correction_does_not_silently_use_new_context(self):
        parts,_=register(self.db,self.root); pool=make_pool(self.db)
        old=parts["culture"]
        self.db.capture(old["entity_id"],"culture",{**old["payload"],"medium":"corrected"},expected=old["id"])
        self.assertEqual(compute_snapshot(self.db,pool["id"])["candidates"][0]["status"],"uncertain")

    def test_snapshot_journal_digest_detects_rewritten_history(self):
        register(self.db,self.root); pool=make_pool(self.db)
        payload=compute_snapshot(self.db,pool["id"]); payload["journal_sha256"]="0"*64
        with self.assertRaises(IntegrityError): self.db.capture("snapshot:bad","pool_snapshot",payload)
