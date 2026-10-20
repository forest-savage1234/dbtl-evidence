from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path
import random
import sqlite3
import tempfile
from threading import Barrier
import unittest

from dbtl.core import Instrument, IntegrityError, ConflictError
from dbtl.graph import impact
from dbtl.ingest import ingest_csv
from dbtl.calc import titer
from dbtl.review import recalibrate
from .support import setup_assay, write_csv


class AdversarialTests(unittest.TestCase):
    def test_deep_explanations_are_explicitly_bounded_without_losing_descendants(self):
        with tempfile.TemporaryDirectory() as root, Instrument(root) as db:
            source = previous = db.put("n:0", "design", {})
            with db.atomic():
                for i in range(1, 321):
                    previous = db.put(f"n:{i}", "design", {}, dependencies=[{"role": "input", "version_id": previous["id"]}])
            impacts = impact(db, source["id"], max_path_steps=16)
            self.assertEqual(len(impacts), 320)
            last = next(r for r in impacts if r["record"]["id"] == previous["id"])
            self.assertEqual(last["total_steps"], 320)
            self.assertFalse(last["path_complete"])
            self.assertEqual(len(last["path"]), 16)

    def test_random_graphs_agree_with_independent_reachability_oracle(self):
        rng = random.Random(73491)
        with tempfile.TemporaryDirectory() as root, Instrument(root) as db:
            children, records = {}, []
            with db.atomic():
                for i in range(160):
                    parents = rng.sample(records, min(len(records), rng.randrange(0, 5)))
                    record = db.put("node:" + str(i), "design", {}, dependencies=[{"role": "input", "version_id": p["id"]} for p in parents])
                    records.append(record)
                    for p in parents:
                        children.setdefault(p["id"], set()).add(record["id"])
            for source in rng.sample(records, 20):
                expected, stack = set(), list(children.get(source["id"], []))
                while stack:
                    node = stack.pop()
                    if node not in expected:
                        expected.add(node); stack.extend(children.get(node, []))
                actual = {r["record"]["id"] for r in impact(db, source["id"])}
                self.assertEqual(actual, expected)

    def test_concurrent_revision_has_one_winner_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as root:
            with Instrument(root) as db:
                old = db.put("shared", "design", {})
            barrier = Barrier(2)
            def worker(name):
                with Instrument(root) as db:
                    barrier.wait(timeout=10)
                    try:
                        db.put("shared", "design", {"editor": name}, expected=old["id"], reason="concurrent test")
                        return "success"
                    except ConflictError:
                        return "conflict"
            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(worker, ["one", "two"]))
            self.assertEqual(sorted(outcomes), ["conflict", "success"])
            with Instrument(root) as db:
                self.assertEqual(len(db.versions()), 2)
                self.assertTrue(db.verify()["ok"])

    def test_multirow_reimport_after_recalibration_returns_original_order_once(self):
        with tempfile.TemporaryDirectory() as root, Instrument(Path(root) / "state") as db:
            p = setup_assay(db)
            path = Path(root) / "raw.csv"
            base = write_csv(path, p)
            write_csv(path, p, rows=[base, {**base, "measurement_id": "m:2", "technical_replicate_id": "tech:2"}])
            imported = ingest_csv(db, path)
            cal = db.capture(p["calibration"]["entity_id"], "calibration", {**p["calibration"]["payload"], "slope": "4"}, expected=p["calibration"]["id"], reason="correction")
            recalibrate(db, imported["measurement_versions"][0], cal["id"], actor="test", reason="correction")
            reimport = ingest_csv(db, path)
            self.assertEqual(reimport["measurement_versions"], imported["measurement_versions"])
            self.assertEqual(reimport["rows"], 2)

    def test_raw_signal_cannot_be_changed_without_new_raw_evidence(self):
        with tempfile.TemporaryDirectory() as root, Instrument(Path(root) / "state") as db:
            p = setup_assay(db); path = Path(root) / "raw.csv"; write_csv(path, p)
            m = db.get(ingest_csv(db, path)["measurement_versions"][0])
            for change in [{"response": "999"}, {"source_row": 1000}, {"run_id": "other"}]:
                with self.assertRaises(IntegrityError):
                    db.capture(m["entity_id"], "measurement", {**m["payload"], **change}, expected=m["id"], reason="attempted unsupported correction")

    def test_corrupted_registry_structure_and_revision_chain_are_detected(self):
        with tempfile.TemporaryDirectory() as root, Instrument(root) as db:
            a = db.put("a", "design", {})
            db.conn.execute("DROP TRIGGER versions_no_update")
            self.assertFalse(db.verify()["ok"])
            db.conn.execute("UPDATE versions SET revision=7 WHERE id=?", (a["id"],))
            self.assertFalse(db.verify()["ok"])

    def test_unsupported_existing_schema_is_not_mutated_on_open(self):
        with tempfile.TemporaryDirectory() as root:
            with Instrument(root) as db:
                db.conn.execute("UPDATE metadata SET value='999' WHERE key='schema_version'")
                db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            path = Path(root) / "registry.sqlite"
            before = path.read_bytes()
            with self.assertRaises(IntegrityError):
                Instrument(root)
            self.assertEqual(path.read_bytes(), before)

    def test_calibration_arithmetic_agrees_with_fraction_oracle(self):
        rng = random.Random(901)
        with tempfile.TemporaryDirectory() as root, Instrument(Path(root) / "state") as db:
            p = setup_assay(db); path = Path(root) / "raw.csv"
            for i in range(15):
                response, slope, intercept, dilution = rng.randint(100, 999), rng.randint(1, 10), rng.randint(0, 30), rng.randint(1, 10)
                cal = db.capture(f"cal:{i}", "calibration", {**p["calibration"]["payload"], "slope": str(slope), "intercept": str(intercept)})
                parts = {**p, "calibration": cal}
                base = write_csv(path, parts)
                write_csv(path, parts, rows=[{**base, "measurement_id": f"m:{i}", "run_id": f"run:{i}", "response": str(response), "dilution": str(dilution)}])
                m = db.get(ingest_csv(db, path)["measurement_versions"][0])
                expected = Fraction((response-intercept)*dilution, slope*1000)
                from decimal import Decimal, localcontext
                with localcontext() as ctx:
                    ctx.prec = 50
                    actual = titer(db, m)
                    self.assertLess(abs(actual - Decimal(expected.numerator)/Decimal(expected.denominator)), Decimal("1e-45"))
