from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.quantities import capture_quantity,derive,replay_result


class QuantityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=Instrument(self.root/"state")
        self.subject=self.db.capture("fixture:source","design",{"data":"SYNTHETIC"})
        self.path=self.root/"q.csv"
        self.path.write_text("pair,product,substrate,biomass,mass_unit,time,time_unit\na,1,1,1,g,60,min\nb,9,3,3,g,60,min\n")

    def tearDown(self):self.db.close();self.temp.cleanup()

    def q(self,id,row,column,basis,**kwargs):
        return capture_quantity(self.db,id,self.path,row=row,value_column=column,unit_column="mass_unit",
            pair_column="pair",subject_version=self.subject["id"],basis=basis,measurand_id="synthetic:"+column,origin="synthetic",**kwargs)

    def groups(self):
        ns=[self.q("q:n"+str(i),i,"product","product_mass")["id"] for i in [2,3]]
        ds=[self.q("q:d"+str(i),i,"substrate","substrate_consumed_mass")["id"] for i in [2,3]]
        return ns,ds

    def test_estimators_have_independent_expected_values(self):
        ns,ds=self.groups()
        for estimator,expected in [("ratio_of_means","2.5"),("mean_of_paired_ratios","2")]:
            r=derive(self.db,"result:"+estimator,ns,ds,metric="mass_yield",estimator=estimator)
            self.assertEqual(r["payload"]["value"],expected)
            self.assertEqual(replay_result(self.db,r["id"])["scientific_validity"],"not_established")

    def test_product_biomass_cannot_be_called_substrate_yield(self):
        ns,_=self.groups();ds=[self.q("q:b"+str(i),i,"biomass","biomass_mass")["id"] for i in [2,3]]
        with self.assertRaises(IntegrityError):derive(self.db,"result:bad",ns,ds,metric="mass_yield",estimator="ratio_of_means")
        self.assertEqual(derive(self.db,"result:ratio",ns,ds,metric="mass_ratio",estimator="ratio_of_means")["payload"]["unit"],"g/g")

    def test_missing_pairs_are_rejected(self):
        ns,ds=self.groups()
        with self.assertRaises(IntegrityError):derive(self.db,"result:bad",ns,ds[:1],metric="mass_yield",estimator="mean_of_paired_ratios")

    def test_changed_declared_pair_or_value_fails_source_binding(self):
        q=self.q("q:n",2,"product","product_mass")
        for field,value in [("pair_id","renamed"),("value","100")]:
            with self.assertRaises(IntegrityError):self.db.capture("q:forged","quantity",{**q["payload"],field:value},artifacts=q["artifacts"])

    def test_corrupted_source_blocks_replay(self):
        ns,ds=self.groups();r=derive(self.db,"result:1",ns,ds,metric="mass_yield",estimator="ratio_of_means")
        self.db.objects.path(self.db.get(ns[0])["payload"]["source_digest"]).write_text("changed")
        with self.assertRaises(IntegrityError):replay_result(self.db,r["id"])

    def test_zero_denominator_and_forged_result_are_rejected(self):
        self.path.write_text("pair,product,substrate,mass_unit\na,1,0,g\n")
        n=self.q("q:n",2,"product","product_mass");d=self.q("q:d",2,"substrate","substrate_consumed_mass")
        with self.assertRaises(IntegrityError):derive(self.db,"result:bad",[n["id"]],[d["id"]],metric="mass_yield",estimator="ratio_of_means")

    def test_unit_conversion_and_endpoint_average_time_are_explicit(self):
        self.path.write_text("pair,product,product_unit,time,time_unit\na,1000,mg/L,60,min\n")
        n=capture_quantity(self.db,"q:n",self.path,row=2,value_column="product",unit_column="product_unit",pair_column="pair",subject_version=self.subject["id"],basis="product_concentration",measurand_id="synthetic:product",origin="synthetic")
        d=capture_quantity(self.db,"q:d",self.path,row=2,value_column="time",unit_column="time_unit",pair_column="pair",subject_version=self.subject["id"],basis="elapsed_time",measurand_id="synthetic:time",origin="synthetic")
        r=derive(self.db,"result:time",[n["id"]],[d["id"]],metric="endpoint_average_productivity",estimator="mean_of_paired_ratios")
        self.assertEqual((r["payload"]["value"],r["payload"]["unit"]),("1","g/L/h"))

    def test_duplicate_pair_ids_do_not_become_paired_replication(self):
        ns,ds=self.groups();again=self.q("q:alias",2,"product","product_mass")
        with self.assertRaises(IntegrityError):derive(self.db,"result:bad",ns+[again["id"]],ds,metric="mass_yield",estimator="mean_of_paired_ratios")
