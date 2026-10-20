from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument,IntegrityError
from dbtl.process import evaluate
from dbtl.assessments import assess
from .test_assessments import dimensions
from .test_pools import register


def process_policy(db):
    return db.capture("process-policy:test","process_policy",{"start_h":"0","end_h":"24","max_gap_h":"12",
        "variables":{"ph":{"unit":"1","minimum":"6.8","maximum":"7.2"}},"basis":"SYNTHETIC observed-point criteria only"})


def trajectory(db,root,parts,name="a",values="0,7\n12,7\n24,7\n",**changes):
    path=root/("trajectory-"+name+".csv");path.write_text("time,value\n"+values);key=db.objects.add(path)
    p={"culture_version":parts["culture"]["id"],"source_digest":key,"variable":"ph","value_unit":"1","time_unit":"h",
        "clock_origin_utc":"2026-10-19T00:00:00Z","alignment":"culture_start","kind_of_observation":"realized","basis":"SYNTHETIC sensor data"}
    p.update(changes);return db.capture("trajectory:"+name,"trajectory",p,artifacts=[key])


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=Instrument(self.root/"state")
        self.parts,self.m=register(self.db,self.root);self.policy=process_policy(self.db)

    def tearDown(self):self.db.close();self.temp.cleanup()

    def check(self,rows):return evaluate(self.db,self.parts["culture"]["id"],[r["id"] for r in rows],self.policy["id"])

    def support(self,r):
        ds=dimensions();ds["comparability"].update(status="supported",evidence_versions=[self.parts["protocol"]["id"]])
        assess(self.db,"assessment:"+r["entity_id"],r["id"],ds,criteria_id="synthetic:clock-sensor:1")

    def test_same_nominal_context_does_not_hide_oscillations(self):
        constant=trajectory(self.db,self.root,self.parts);self.support(constant)
        oscillating=trajectory(self.db,self.root,self.parts,"osc","0,7\n6,6\n12,7\n18,8\n24,7\n");self.support(oscillating)
        self.assertEqual(self.check([constant])["status"],"within_declared_limits")
        self.assertEqual(self.check([oscillating])["status"],"conflict")

    def test_missing_trajectory_and_unassessed_sensor_stay_open(self):
        self.assertEqual(self.check([])["status"],"open")
        self.assertEqual(self.check([trajectory(self.db,self.root,self.parts)])["status"],"open")

    def test_gaps_endpoints_and_unresolved_alignment_withhold(self):
        for name,values,changes in [("gap","0,7\n24,7\n",{}),("short","1,7\n12,7\n24,7\n",{}),("clock","0,7\n12,7\n24,7\n",{"alignment":"unresolved"})]:
            r=trajectory(self.db,self.root,self.parts,name,values,**changes);self.support(r)
            self.assertEqual(self.check([r])["status"],"open")

    def test_time_units_are_explicit_and_nonmonotonic_or_nominal_data_rejected(self):
        r=trajectory(self.db,self.root,self.parts,"minutes","0,7\n720,7\n1440,7\n",time_unit="min");self.support(r)
        self.assertEqual(self.check([r])["status"],"within_declared_limits")
        for name,values,changes in [("order","0,7\n12,7\n12,7\n",{}),("nominal","0,7\n24,7\n",{"kind_of_observation":"nominal"}),("unit","0,7\n24,7\n",{"value_unit":"mg/L"})]:
            with self.assertRaises(IntegrityError):trajectory(self.db,self.root,self.parts,name,values,**changes)

    def test_conflicting_clock_origins_are_not_silently_merged(self):
        a=trajectory(self.db,self.root,self.parts,"a");b=trajectory(self.db,self.root,self.parts,"b",clock_origin_utc="2026-10-18T00:00:00Z")
        for r in (a,b):self.support(r)
        self.assertEqual(self.check([a,b])["status"],"open")

    def test_corrupt_sensor_bytes_block_reassessment(self):
        r=trajectory(self.db,self.root,self.parts);self.db.objects.path(r["payload"]["source_digest"]).write_text("altered")
        with self.assertRaises(IntegrityError):self.check([r])
