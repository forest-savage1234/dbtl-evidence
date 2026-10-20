from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.ingest import ingest_csv, FIELDS
from dbtl.domain import number
from .support import setup_assay, write_csv


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Instrument(Path(self.temp.name) / "registry")
        self.parts = setup_assay(self.db)
        self.csv = Path(self.temp.name) / "measurements.csv"
        self.base = write_csv(self.csv, self.parts)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_import_is_pinned_atomic_and_idempotent(self):
        first = ingest_csv(self.db, self.csv)
        second = ingest_csv(self.db, self.csv)
        self.assertEqual(first["measurement_versions"], second["measurement_versions"])
        self.assertTrue(second["reused"])
        measurement = self.db.get(first["measurement_versions"][0])
        self.assertEqual(measurement["payload"]["sample_version"], self.parts["sample"]["id"])
        self.assertTrue(self.db.verify()["ok"])

    def test_bad_second_row_rolls_back_first(self):
        before = len(self.db.versions())
        bad = {**self.base, "measurement_id": "measurement:bad", "technical_replicate_id": "tech:2", "response": "NaN"}
        write_csv(self.csv, self.parts, rows=[self.base, bad])
        with self.assertRaises(IntegrityError):
            ingest_csv(self.db, self.csv)
        self.assertEqual(len(self.db.versions()), before)

    def test_duplicate_acquisition_with_new_id_cannot_double_count(self):
        ingest_csv(self.db, self.csv)
        write_csv(self.csv, self.parts, rows=[{**self.base, "measurement_id": "renamed"}])
        with self.assertRaises(IntegrityError):
            ingest_csv(self.db, self.csv)

    def test_wrong_analyte_unit_or_reference_rejected(self):
        for change in [{"analyte_id": "other"}, {"response_unit": "mAU"}, {"sample_version": self.parts["strain"]["id"]}]:
            write_csv(self.csv, self.parts, rows=[{**self.base, **change}])
            with self.assertRaises(IntegrityError):
                ingest_csv(self.db, self.csv)

    def test_unknown_columns_empty_and_truncated_files_rejected(self):
        for content in ["", ",".join(FIELDS) + "\n", ",".join(FIELDS) + "\na,b\n", "extra," + ",".join(FIELDS) + "\n"]:
            self.csv.write_text(content)
            with self.assertRaises(IntegrityError):
                ingest_csv(self.db, self.csv)

    def test_numeric_parser_rejects_nonfinite_float_and_exponent_bombs(self):
        for value in ["Infinity", "NaN", True, 0.1, "1e999999999", " 1", "0,5"]:
            with self.assertRaises(IntegrityError):
                number(value)

    def test_versioned_extensions_do_not_require_schema_migration(self):
        a = self.db.put("design:new", "design", {"extensions": {"lab:new_editor": {"version": 1}}})
        self.assertEqual(a["payload"]["extensions"]["lab:new_editor"]["version"], 1)
        with self.assertRaises(IntegrityError):
            self.db.put("design:bad", "design", {"extensions": {"mystery": 1}})
