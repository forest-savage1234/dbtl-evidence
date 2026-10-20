from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument,IntegrityError
from dbtl.units import assign,summarize
from dbtl.assessments import assess
from .test_assessments import dimensions
from .test_pools import register


def unit(db,name,role="culture",parent=None):
    return db.capture("unit:"+name,"experimental_unit",{"physical_id":"physical:"+name,"role":role,"parent_version":parent,"basis":"SYNTHETIC declared material"})


class UnitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=Instrument(self.root/"state")
        self.a,self.ma=register(self.db,self.root,"A");self.b,self.mb=register(self.db,self.root,"B")

    def tearDown(self):self.db.close();self.temp.cleanup()

    def test_aliquots_and_renamed_culture_entities_do_not_inflate_independent_n(self):
        root=unit(self.db,"root");a=unit(self.db,"a","aliquot",root["id"]);b=unit(self.db,"b","aliquot",root["id"])
        assign(self.db,self.a["culture"]["id"],a["id"],basis="alias of physical culture")
        assign(self.db,self.b["culture"]["id"],b["id"],basis="alias of physical culture")
        r=summarize(self.db,[self.ma,self.mb])
        self.assertEqual(r["declared_culture_unit_n"],1);self.assertEqual(r["assessed_culture_unit_n"],0)
        self.assertFalse(r["eligible_for_scoped_descriptive_comparison"])

    def test_distinct_barcodes_are_not_independence_evidence(self):
        for p,name in [(self.a,"a"),(self.b,"b")]:assign(self.db,p["culture"]["id"],unit(self.db,name)["id"],basis="SYNTHETIC barcode")
        self.assertFalse(summarize(self.db,[self.ma,self.mb])["eligible_for_scoped_descriptive_comparison"])

    def test_scoped_independence_assessments_are_required(self):
        for p,name in [(self.a,"a"),(self.b,"b")]:
            r=unit(self.db,name);assign(self.db,p["culture"]["id"],r["id"],basis="SYNTHETIC mapping")
            ds=dimensions();ds["replicate_independence"].update(status="supported",evidence_versions=[p["protocol"]["id"]])
            assess(self.db,"assessment:"+name,r["id"],ds,criteria_id="synthetic:experimental-design:1")
        self.assertTrue(summarize(self.db,[self.ma,self.mb])["eligible_for_scoped_descriptive_comparison"])

    def test_same_acquisition_under_different_labels_is_flagged(self):
        root=unit(self.db,"root");acq=unit(self.db,"acq","acquisition",root["id"])
        assign(self.db,self.ma,acq["id"],basis="SYNTHETIC duplicate")
        assign(self.db,self.mb,acq["id"],basis="SYNTHETIC duplicate")
        self.assertIn("duplicate_physical_acquisition",[i["reason"] for i in summarize(self.db,[self.ma,self.mb])["issues"]])

    def test_conflicting_sample_and_culture_mappings_withhold_comparison(self):
        assign(self.db,self.a["culture"]["id"],unit(self.db,"a")["id"],basis="SYNTHETIC")
        assign(self.db,self.a["sample"]["id"],unit(self.db,"b")["id"],basis="SYNTHETIC conflict")
        self.assertIn("conflicting_unit_mapping",[i["reason"] for i in summarize(self.db,[self.ma])["issues"]])

    def test_duplicate_canonical_physical_unit_is_rejected(self):
        r=unit(self.db,"a")
        with self.assertRaises(IntegrityError):self.db.capture("unit:alias","experimental_unit",r["payload"])

    def test_unsupported_parent_hierarchy_is_rejected(self):
        root=unit(self.db,"root");a=unit(self.db,"a","acquisition",root["id"])
        with self.assertRaises(IntegrityError):unit(self.db,"bad","aliquot",a["id"])
