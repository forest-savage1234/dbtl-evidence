from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.pools import snapshot, replay_snapshot
from dbtl.watches import watch, status, pending, acknowledge
from .test_datasets import dataset_fixture
from .test_pools import register, make_pool


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=Instrument(self.root/"state")
        self.parts,_,_,_,dataset=dataset_fixture(self.db,self.root)
        self.pool=make_pool(self.db);self.snap=snapshot(self.db,"snapshot:1",self.pool["id"])
        self.watch=watch(self.db,"watch:1",dataset["id"],self.snap["id"],basis="SYNTHETIC advancement universe")

    def tearDown(self):self.db.close();self.temp.cleanup()

    def test_new_independent_result_requests_review(self):
        self.assertFalse(status(self.db,self.watch["id"])["requires_reassessment"])
        register(self.db,self.root,"B")
        s=status(self.db,self.watch["id"])
        self.assertEqual(s["delta"]["added"],["measurement:B"]);self.assertEqual(len(pending(self.db)),1)
        self.assertTrue(replay_snapshot(self.db,self.snap["id"])["ok"])

    def test_irrelevant_excluded_new_result_does_not_alert(self):
        old=self.pool
        pool=self.db.capture(old["entity_id"],"pool",{**old["payload"],"filters":{**old["payload"]["filters"],"batch":"batch:1"}},expected=old["id"])
        snap=snapshot(self.db,"snapshot:2",pool["id"])
        w=watch(self.db,"watch:2",self.watch["payload"]["target_version"],snap["id"],basis="SYNTHETIC scope")
        register(self.db,self.root,"B",batch="different")
        self.assertFalse(status(self.db,w["id"])["requires_reassessment"])

    def test_withdrawal_requests_review_and_access_loss_is_unknown(self):
        m=self.snap["payload"]["candidates"][0]["measurement_version"]
        n=self.db.capture("availability:A","availability",{"measurement_version":m,"state":"withdrawn","category":"measurement","basis":"SYNTHETIC withdrawal"})
        self.assertEqual(status(self.db,self.watch["id"])["delta"]["removed"],["measurement:A"])
        self.db.capture(n["entity_id"],"availability",{**n["payload"],"state":"inaccessible","category":"access"},expected=n["id"])
        self.assertEqual(status(self.db,self.watch["id"])["state"],"pool_eligibility_unknown")

    def test_harmless_bibliographic_notice_does_not_reject_numeric_result(self):
        m=self.snap["payload"]["candidates"][0]["measurement_version"]
        self.db.capture("availability:A","availability",{"measurement_version":m,"state":"available","category":"bibliographic","basis":"SYNTHETIC surname spelling only"})
        self.assertFalse(status(self.db,self.watch["id"])["requires_reassessment"])

    def test_acknowledgement_does_not_reset_current_state(self):
        register(self.db,self.root,"B");s=status(self.db,self.watch["id"])
        acknowledge(self.db,self.watch["id"],s["fingerprint"],disposition="retain_historical",basis="SYNTHETIC retain old decision",actor="reviewer")
        self.assertTrue(status(self.db,self.watch["id"])["requires_reassessment"])
        self.assertEqual(pending(self.db),[])
        register(self.db,self.root,"C");self.assertEqual(len(pending(self.db)),1)

    def test_stale_review_token_is_rejected(self):
        before=status(self.db,self.watch["id"]);register(self.db,self.root,"B")
        with self.assertRaises(IntegrityError):acknowledge(self.db,self.watch["id"],before["fingerprint"],disposition="retain_historical",basis="stale",actor="reviewer")

    def test_restart_and_rolled_back_ingestion_cannot_lose_a_change(self):
        with self.assertRaises(RuntimeError):
            with self.db.atomic():
                register(self.db,self.root,"ROLLBACK");raise RuntimeError("SYNTHETIC interrupted write")
        self.assertFalse(status(self.db,self.watch["id"])["requires_reassessment"])
        register(self.db,self.root,"B");first=status(self.db,self.watch["id"])
        self.db.close();self.db=Instrument(self.root/"state")
        self.assertEqual(status(self.db,self.watch["id"])["fingerprint"],first["fingerprint"])
