from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dbtl.core import Instrument
from dbtl.demo import run_demo
from dbtl.report import render_report
from .test_datasets import dataset_fixture


class WorkflowTests(unittest.TestCase):
    def test_counterfactual_demonstration_reverses_ranking_and_preserves_both(self):
        with tempfile.TemporaryDirectory() as root:
            result = run_demo(Path(root) / "demo")
            self.assertEqual(result["original"][0]["strain_id"], "demo:strain-A")
            self.assertEqual(result["original"][0]["mean_g_l"], "0.6")
            self.assertEqual(result["corrected"][0]["strain_id"], "demo:strain-B")
            self.assertEqual(result["corrected"][0]["mean_g_l"], "0.51")
            self.assertEqual(next(s["mean_g_l"] for s in result["corrected"] if s["strain_id"] == "demo:strain-A"), "0.3")
            self.assertEqual(len(result["initial_review_findings"]), 2)
            self.assertEqual(result["remaining_pending_findings"], [])
            self.assertTrue(result["historical_replay"]["ok"] and result["current_replay"]["ok"] and result["audit"]["ok"])

    def test_report_escapes_user_text_and_has_no_executable_scripts(self):
        with tempfile.TemporaryDirectory() as root, Instrument(Path(root) / "state") as db:
            parts, _, _, _, dataset = dataset_fixture(db, root)
            attack = "<script>alert('bad')</script><img src='https://example.org'>"
            db.capture("decision:attack", "decision", {"dataset_version": dataset["id"], "selected_strain_versions": [parts["strain"]["id"]], "rationale": attack})
            html = render_report(db, title=attack)
            self.assertNotIn("<script>", html)
            self.assertNotIn("<img ", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("script-src 'none'", html)
            HTMLParser().feed(html)

    def test_cli_roundtrip_and_missing_registry_error(self):
        with tempfile.TemporaryDirectory() as root:
            command = [sys.executable, "-m", "dbtl", "--root", str(Path(root) / "state")]
            missing = subprocess.run(command + ["audit"], capture_output=True, text=True)
            self.assertEqual(missing.returncode, 2)
            self.assertIn("No registry", json.loads(missing.stderr)["error"])
            initialized = subprocess.run(command + ["init"], capture_output=True, text=True)
            self.assertEqual(initialized.returncode, 0)
            payload = Path(root) / "design.json"; payload.write_text('{"name":"test"}')
            captured = subprocess.run(command + ["capture", "design:cli", "design", str(payload), "--reason", "test"], capture_output=True, text=True)
            self.assertEqual(captured.returncode, 0, captured.stderr)
            version = json.loads(captured.stdout)["id"]
            shown = subprocess.run(command + ["show", version], capture_output=True, text=True)
            self.assertEqual(json.loads(shown.stdout)["entity_id"], "design:cli")

    def test_demo_refuses_to_overwrite_existing_directory(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "important").write_text("keep")
            from dbtl.core import IntegrityError
            with self.assertRaises(IntegrityError):
                run_demo(root)
            self.assertEqual(Path(root, "important").read_text(), "keep")
