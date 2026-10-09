import ctypes
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tidyup.windows_recycle import ProgressSink, RECYCLE_FLAGS, classify
from tidyup.windows_recycle_test import run


class NativeRecycleContractTests(unittest.TestCase):
    def native(self):
        return {"perform_success": True, "aborted_query_success": True, "aborted": False,
                "events": [{"stage": "pre_delete", "verified": True},
                           {"stage": "post_delete", "native_success": True, "recycle_item_returned": True}]}

    def test_requires_native_recycle_callback_and_both_hashes(self):
        native = self.native()
        self.assertEqual(classify(native, True, "sha", "sha", "sha"), "passed")
        native["events"][1]["recycle_item_returned"] = False
        self.assertEqual(classify(native, True, "sha", "sha", "sha"), "uncertain")
        native = self.native()
        self.assertEqual(classify(native, True, "other", "sha", "sha"), "uncertain")
        self.assertEqual(classify(native, True, "sha", "sha", "changed-reference"), "uncertain")
        self.assertEqual(classify(native, False, "sha", "sha", "sha"), "failed")

    def test_missing_precheck_or_aborted_query_does_not_pass(self):
        native = self.native()
        native["events"] = native["events"][1:]
        self.assertEqual(classify(native, True, "sha", "sha", "sha"), "uncertain")
        native = self.native()
        native["aborted_query_success"] = False
        self.assertEqual(classify(native, True, "sha", "sha", "sha"), "uncertain")
        native["aborted"] = True
        self.assertEqual(classify(native, False, None, "sha", "sha"), "cancelled")

    def test_callback_blocks_failed_verification(self):
        def reject(_path):
            raise ValueError("fixture changed")
        # Só ABI/callbacks sintéticos; isto NÃO comprova COM/Win32.
        with patch.object(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE, create=True), patch("tidyup.windows_recycle.shell_path", return_value="synthetic"):
            sink = ProgressSink(reject, None)
            result = sink.callbacks[11](sink.pointer, 0, None)
            self.assertLess(result, 0)
            self.assertFalse(sink.events[0]["verified"])
            self.assertLess(sink.callbacks[7](sink.pointer, 0, None, None, None), 0)

    def test_flags_require_recycle_and_early_failure(self):
        self.assertTrue(RECYCLE_FLAGS & 0x00080000)
        self.assertTrue(RECYCLE_FLAGS & 0x00100000)
        self.assertTrue(RECYCLE_FLAGS & 0x0400)

    def test_linux_is_not_executed_not_mock_success(self):
        if os.name == "nt":
            self.skipTest("Este teste verifica apenas a recusa explícita de Linux; native runner é opt-in.")
        with tempfile.TemporaryDirectory(prefix="tidyup-native-contract-") as tmp:
            result, path = run(tmp)
            self.assertEqual(result["status"], "not_executed")
            self.assertTrue(path.exists())
            self.assertNotIn("source", result)
