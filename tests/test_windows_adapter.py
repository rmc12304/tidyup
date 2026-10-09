"""Simulações do adaptador/Engine. Não constituem prova de Windows nativo."""
import hashlib
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tidyup.filesystem import Blocked, signature
from tidyup.native import WindowsFixtureTrash, WindowsTrash, default_adapter
from tidyup.windows_flow_test import run


def synthetic_perform(source, verify):
    verify(str(source))
    verify(str(source))  # equivalente ao callback, sem COM
    recycled = source.parent.parent / (source.name + ".synthetic-recycled")
    source.rename(recycled)
    return {"perform_success": True, "aborted_query_success": True, "aborted": False,
            "events": [{"stage": "pre_delete", "verified": True},
                       {"stage": "post_delete", "native_success": True, "recycle_item_returned": True, "recycled_path": str(recycled)}]}


class WindowsAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tidyup-windows-flow-")
        self.root = Path(self.tmp.name).resolve()
        for role in ("source", "reference"):
            (self.root / role).mkdir()
            (self.root / role / "item.txt").write_bytes(b"same")
        self.adapter = WindowsFixtureTrash(self.root)
        def item(role):
            path = self.root / role / "item.txt"
            return {"path": str(path), "root": str(path.parent), "root_identity": signature(path.parent.stat())[:2], "identity": signature(path.stat()), "hash": hashlib.sha256(b"same").hexdigest()}
        self.source, self.reference = item("source"), item("reference")

    def tearDown(self):
        self.tmp.cleanup()

    def test_success_requires_recycled_content_and_intact_reference(self):
        with patch("tidyup.windows_recycle.perform_recycle", side_effect=synthetic_perform):
            result = self.adapter.recycle_guarded(self.source, self.reference)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["native_evidence"]["recycled_sha256"], self.source["hash"])
        self.assertTrue(Path(self.reference["path"]).exists())

    def test_reference_change_at_callback_blocks_without_moving(self):
        def race(source, verify):
            Path(self.reference["path"]).write_bytes(b"changed")
            verify(str(source))
        with patch("tidyup.windows_recycle.perform_recycle", side_effect=race):
            result = self.adapter.recycle_guarded(self.source, self.reference)
        self.assertEqual(result["status"], "uncertain")
        self.assertTrue(Path(self.source["path"]).exists())

    def test_exception_after_move_is_uncertain(self):
        def interrupted(source, verify):
            synthetic_perform(source, verify)
            raise OSError("interruption after move")
        with patch("tidyup.windows_recycle.perform_recycle", side_effect=interrupted):
            self.assertEqual(self.adapter.recycle_guarded(self.source, self.reference)["status"], "uncertain")

    def test_bad_recycled_hash_is_uncertain(self):
        def wrong(source, verify):
            result = synthetic_perform(source, verify)
            Path(result["events"][1]["recycled_path"]).write_bytes(b"wrong")
            return result
        with patch("tidyup.windows_recycle.perform_recycle", side_effect=wrong):
            self.assertEqual(self.adapter.recycle_guarded(self.source, self.reference)["status"], "uncertain")

    def test_missing_native_proof_cannot_succeed(self):
        def missing(source, verify):
            result = synthetic_perform(source, verify)
            result["events"] = []
            return result
        with patch("tidyup.windows_recycle.perform_recycle", side_effect=missing):
            self.assertEqual(self.adapter.recycle_guarded(self.source, self.reference)["status"], "uncertain")

    def test_scope_rejects_reference_as_source_and_external_paths(self):
        for item in (self.reference, {**self.source, "path": str(self.root / "external.txt")}):
            with patch("tidyup.windows_recycle.perform_recycle") as native:
                self.assertEqual(self.adapter.recycle_guarded(item, self.reference)["status"], "blocked")
                native.assert_not_called()

    def test_cancel_before_native_does_not_move(self):
        event = threading.Event(); event.set()
        self.adapter.bind_cancel(event)
        with patch("tidyup.windows_recycle.perform_recycle") as native:
            self.assertEqual(self.adapter.recycle_guarded(self.source, self.reference)["status"], "cancelled")
            native.assert_not_called()

    def test_changed_root_identity_blocks_before_native(self):
        source = {**self.source, "root_identity": [-1, -1]}
        with patch("tidyup.windows_recycle.perform_recycle") as native:
            self.assertEqual(self.adapter.recycle_guarded(source, self.reference)["status"], "blocked")
            native.assert_not_called()

    def test_exceptional_discard_still_verifies_recycled_hash(self):
        with patch("tidyup.windows_recycle.perform_recycle", side_effect=synthetic_perform):
            result = self.adapter.recycle_guarded(self.source, None)
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["native_evidence"]["reference_sha256"])

    def test_default_and_invalid_fixture_remain_blocked(self):
        self.assertFalse(default_adapter().supported)
        self.assertEqual(WindowsTrash().recycle_guarded(self.source, self.reference)["status"], "blocked")
        with self.assertRaises(Blocked):
            WindowsFixtureTrash(self.root / "source")


class WindowsFlowRunnerTests(unittest.TestCase):
    def test_full_runner_synthetic_batch_revalidation_and_restart(self):
        # Alterar só a detecção de plataforma do runner; filesystem continua POSIX.
        with tempfile.TemporaryDirectory(prefix="tidyup-flow-report-") as reports, patch("tidyup.windows_flow_test.os", SimpleNamespace(name="nt", fsync=os.fsync)), patch("tidyup.windows_recycle.perform_recycle", side_effect=synthetic_perform) as native:
            report, path = run(reports)
            self.assertEqual(report["status"], "passed", report)
            self.assertTrue(all(report["assertions"].values()))
            self.assertEqual(native.call_count, 2)
            self.assertTrue(path.exists())
            root = Path(report["fixture_root"])
            # Apenas esta simulação é limpa; o runner nativo preserva fixtures.
            import shutil
            shutil.rmtree(root)

    def test_linux_never_runs_native(self):
        if os.name == "nt":
            self.skipTest("Recusa específica de POSIX")
        with tempfile.TemporaryDirectory(prefix="tidyup-flow-report-") as reports, patch("tidyup.windows_recycle.perform_recycle") as native:
            report, path = run(reports)
            self.assertEqual(report["status"], "not_executed")
            self.assertNotIn("fixture_root", report)
            native.assert_not_called()
