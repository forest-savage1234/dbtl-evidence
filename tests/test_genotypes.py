import json
from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.genotypes import evaluate
from dbtl.assessments import assess
from .test_assessments import dimensions
from .test_pools import register


def observation(db, root, parts, name="a", **changes):
    source = root/("calls-"+name+".json")
    source.write_text(json.dumps({"schema":"scoped-genotype-calls/1","calls":[
        {"region_id":"region:1","expected":"intended-state","observed":"intended-state","status":"called"}]}))
    key = db.objects.add(source)
    p = {"strain_version":parts["strain"]["id"],"material_version":parts["sample"]["id"],
         "observed_at":"2026-10-20T00:00:00Z","generation":10,"scope":"clone",
         "method":"SYNTHETIC precomputed calls; not sequencing validation","source_digest":key,
         "limitations":"One declared region only; source calls are not authenticated."}
    p.update(changes)
    r = db.capture("genotype:"+name,"genotype_observation",p,artifacts=[p["source_digest"]])
    return r


class GenotypeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.db=Instrument(self.root/"state")
        self.parts,self.m=register(self.db,self.root)

    def tearDown(self): self.db.close();self.temp.cleanup()

    def run_scope(self, versions, **changes):
        args={"required_regions":["region:1"],"as_of":"2026-10-20T12:00:00Z","max_age_h":"24","minimum_generation":10}
        args.update(changes);return evaluate(self.db,self.m,versions,**args)

    def support(self,r):
        ds=dimensions()
        for d in ("measurement","sample_identity"):ds[d].update(status="supported",evidence_versions=[self.parts["protocol"]["id"]])
        assess(self.db,"review:"+r["entity_id"],r["id"],ds,criteria_id="SYNTHETIC:genotype:1")

    def test_absent_observation_and_unassessed_calls_stay_open(self):
        self.assertEqual(self.run_scope([])["status"],"open")
        r=observation(self.db,self.root,self.parts)
        self.assertEqual(self.run_scope([r["id"]])["status"],"open")

    def test_scoped_supported_observation_does_not_imply_full_genome(self):
        r=observation(self.db,self.root,self.parts);self.support(r)
        result=self.run_scope([r["id"]]);self.assertEqual(result["status"],"supported_for_declared_regions")
        self.assertEqual(self.run_scope([r["id"]],required_regions=["region:1","region:2"])["missing_regions"],["region:2"])

    def test_old_time_generation_and_population_scope_withhold(self):
        for name,changes in [("old",{"observed_at":"2026-10-01T00:00:00Z"}),("early",{"generation":1}),("pop",{"scope":"population"})]:
            r=observation(self.db,self.root,self.parts,name,**changes);self.support(r)
            self.assertEqual(self.run_scope([r["id"]])["status"],"open")

    def test_wrong_strain_material_rejected_and_other_sample_not_reused(self):
        other,_=register(self.db,self.root,"B")
        with self.assertRaises(IntegrityError):observation(self.db,self.root,self.parts,"bad",material_version=other["sample"]["id"])
        r=observation(self.db,self.root,other,"other");self.support(r)
        self.assertEqual(self.run_scope([r["id"]])["status"],"open")

    def test_discordant_call_is_conflict_even_with_supporting_assessment(self):
        path=self.root/"discordant.json";path.write_text(json.dumps({"schema":"scoped-genotype-calls/1","calls":[
            {"region_id":"region:1","expected":"intended","observed":"different","status":"called"}]}))
        r=observation(self.db,self.root,self.parts,source_digest=self.db.objects.add(path));self.support(r)
        self.assertEqual(self.run_scope([r["id"]])["status"],"conflict")

    def test_arbitrary_note_is_not_structured_genotype_evidence(self):
        path=self.root/"note.txt";path.write_text("Operator says genotype verified")
        with self.assertRaises(IntegrityError):observation(self.db,self.root,self.parts,source_digest=self.db.objects.add(path))

    def test_raw_corruption_blocks_reassessment(self):
        r=observation(self.db,self.root,self.parts)
        self.db.objects.path(r["payload"]["source_digest"]).write_text("corrupt")
        with self.assertRaises(IntegrityError):self.run_scope([r["id"]])
