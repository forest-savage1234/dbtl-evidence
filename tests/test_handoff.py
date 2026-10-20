import json
from pathlib import Path
import tempfile
import unittest
from hashlib import sha256

from dbtl.core import Instrument,IntegrityError
from dbtl.handoff import receive

FIXTURE=Path(__file__).resolve().parents[1]/"examples/claim-review-synthetic"


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=Instrument(self.root/"state")

    def tearDown(self):self.db.close();self.temp.cleanup()

    def receive(self,report=None,source=None,origin="synthetic_fixture"):
        return receive(self.db,"literature:claim",report or FIXTURE/"report.json",source or FIXTURE/"source.csv",origin=origin,intended_use="SYNTHETIC reference only",target_domain="No local process")

    def altered(self,change):
        p=json.loads((FIXTURE/"report.json").read_text());change(p);path=self.root/"report.json";path.write_text(json.dumps(p));return path

    def test_real_producer_core_fixture_keeps_open_dimensions_and_biomass_basis(self):
        p=self.receive()["payload"]
        self.assertEqual(p["upstream"]["overallStatus"],"PARTIAL_SUPPORT")
        self.assertEqual(p["upstream"]["spec"]["inputs"][1]["headerText"],"biomass_g")
        self.assertTrue(all(v["status"]=="open" for v in p["consumer_dimensions"].values()))
        self.assertEqual(self.db.versions("measurement"),[])

    def test_fixture_bytes_match_recorded_producer_probe(self):
        p=json.loads((FIXTURE/"provenance.json").read_text())
        for name,key in [("source.csv","source_sha256"),("report.json","report_sha256")]:self.assertEqual(sha256((FIXTURE/name).read_bytes()).hexdigest(),p[key])

    def test_source_mismatch_and_unknown_schema_or_status_rejected(self):
        wrong=self.root/"wrong.csv";wrong.write_text("value\n1\n")
        with self.assertRaises(IntegrityError):self.receive(source=wrong)
        for key,value in [("schema","claim-review/99"),("toolVersion","future"),("overallStatus","VERIFIED")]:
            with self.assertRaises(IntegrityError):self.receive(report=self.altered(lambda p:p.update({key:value})))

    def test_unknown_assessment_and_omitted_open_requirement_rejected(self):
        for change in [lambda p:p["checks"][0].update(status="verified"),lambda p:p.update(checks=[c for c in p["checks"] if c["name"]!="Measurement history"])]:
            with self.assertRaises(IntegrityError):self.receive(report=self.altered(change))

    def test_upstream_conflict_is_preserved_verbatim(self):
        def change(p):
            p.update(numericalStatus="WITHHELD",overallStatus="REVIEW_REQUIRED",error="SYNTHETIC reported-value mismatch")
            p["checks"].append({"name":"Replay requirement","status":"conflict","detail":"SYNTHETIC mismatch"})
        path=self.altered(change);r=self.receive(report=path)
        self.assertEqual(r["payload"]["upstream"],json.loads(path.read_text()))

    def test_local_origin_and_promoted_consumer_status_rejected(self):
        with self.assertRaises(IntegrityError):self.receive(origin="local")
        r=self.receive();p=r["payload"];p["consumer_dimensions"]["measurement"]["status"]="supported"
        with self.assertRaises(IntegrityError):self.db.capture("literature:forged","literature_evidence",p,artifacts=r["artifacts"])
