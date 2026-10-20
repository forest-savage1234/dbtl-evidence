import json
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction

from dbtl.core import Instrument, IntegrityError
from dbtl.uncertainty import propagate, contrast, freeze_uncertainty, compute
from .test_pools import register


def zeros(n): return [["0" for _ in range(n)] for _ in range(n)]


def assay(db,root,parts,name="a",readout="direct_concentration"):
    source=root/("assay-"+name+".json")
    source.write_text(json.dumps({"schema":"assay-validation-observations/1","calibration_version":parts["calibration"]["id"],
        "matrix":"supernatant","observations":[{"nominal":"500","observed":"501","unit":"mg/L" if readout=="direct_concentration" else "area"}]}))
    key=db.objects.add(source)
    return db.capture("assay:"+name,"assay_profile",{"calibration_version":parts["calibration"]["id"],"matrix":"supernatant",
        "readout":readout,"measurand_id":"demo:product","validation_scope":"SYNTHETIC single observation, not method validation",
        "source_digest":key,"basis":"SYNTHETIC test only"},artifacts=[key])


def uncertainty_source(root,measurement,name="a",covariance=None):
    source=root/("uncertainty-"+name+".json");covariance=zeros(4) if covariance is None else covariance
    source.write_text(json.dumps({"schema":"linear-uncertainty/1","measurement_version":measurement,"covariance":covariance,"basis":"SYNTHETIC assumed covariance; omitted effects unresolved"}))
    return source


class UncertaintyTests(unittest.TestCase):
    def test_analytic_variance_with_fraction_oracle(self):
        c=zeros(4)
        for i,v in enumerate(["4","1","0.04","0.01"]):c[i][i]=v
        r=propagate({"response":"10","intercept":"2","slope":"2","dilution":"3"},c)
        expected=Fraction(9,4)*5+36*Fraction(4,100)+16*Fraction(1,100)
        self.assertEqual(r["value"],"12");self.assertEqual(Fraction(r["variance"]),expected)

    def test_shared_intercept_cancels_in_contrast_but_independent_errors_do_not(self):
        a={"response":"10","intercept":"0","slope":"2","dilution":"1"};b={**a,"response":"6"}
        c=zeros(8);c[1][1]=c[5][5]="4"
        self.assertEqual(contrast(a,b,c)["variance"],"2")
        c[1][5]=c[5][1]="4"
        self.assertEqual(contrast(a,b,c)["variance"],"0");self.assertEqual(contrast(a,b,c)["difference"],"2")

    def test_bad_covariance_and_missing_variables_are_rejected(self):
        v={"response":"10","intercept":"0","slope":"2","dilution":"1"}
        for c in [None,zeros(3),[["1","2","0","0"],["2","1","0","0"],["0","0","0","0"],["0","0","0","0"]]]:
            with self.assertRaises(IntegrityError):propagate(v,c)
        c=zeros(4);c[0][1]="1"
        with self.assertRaises(IntegrityError):propagate(v,c)
        with self.assertRaises(IntegrityError):propagate({"response":"1"},zeros(4))

    def test_assay_source_scope_proxy_and_censoring_remain_distinct(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with Instrument(root/"state") as db:
                parts,m=register(db,root);a=assay(db,root,parts);source=uncertainty_source(root,m)
                r=freeze_uncertainty(db,"uncertainty:a",m,a["id"],source)
                self.assertEqual(r["payload"]["result"]["value"],"0.5")
                proxy=assay(db,root,parts,"proxy","proxy")
                self.assertEqual(compute(db,m,proxy["id"],db.objects.add(source))["status"],"proxy_only")
                raw=db.get(m);p={**raw["payload"],"quantification":"below_loq"}
                censored=db.capture(raw["entity_id"],"measurement",p,expected=m,reason="SYNTHETIC censor review")
                csource=uncertainty_source(root,censored["id"],"censored")
                output=compute(db,censored["id"],a["id"],db.objects.add(csource))
                self.assertEqual(output["status"],"censored_or_unreviewed");self.assertIsNone(output["value"])

    def test_source_corruption_and_forged_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with Instrument(root/"state") as db:
                parts,m=register(db,root);a=assay(db,root,parts);source=uncertainty_source(root,m)
                r=freeze_uncertainty(db,"uncertainty:a",m,a["id"],source);p={**r["payload"],"result":{}}
                with self.assertRaises(IntegrityError):db.capture("uncertainty:forged","uncertainty_result",p,artifacts=r["artifacts"])
                db.objects.path(r["payload"]["source_digest"]).write_text("altered")
                with self.assertRaises(IntegrityError):compute(db,m,a["id"],r["payload"]["source_digest"])

    def test_duplicate_json_keys_cannot_hide_a_covariance(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with Instrument(root/"state") as db:
                parts,m=register(db,root);a=assay(db,root,parts);source=root/"bad.json"
                source.write_text('{"schema":"linear-uncertainty/1","schema":"different"}')
                with self.assertRaises(IntegrityError):compute(db,m,a["id"],db.objects.add(source))
