"""Regressão sintética das representações stat/fstat do CPython Windows."""
import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tidyup.filesystem import Blocked, descriptor_path_signature, full_hash


def metadata(*, ctime, inode=2):
    return SimpleNamespace(st_dev=1, st_ino=inode, st_size=7, st_mtime_ns=300,
                           st_ctime_ns=ctime, st_birthtime_ns=100, st_nlink=1)


class WindowsHashMetadataTests(unittest.TestCase):
    def digest(self, before, after, *, windows=True):
        with tempfile.TemporaryDirectory(prefix="tidyup-stat-fixture-") as tmp:
            source = Path(tmp) / "fixture.txt"
            source.write_bytes(b"fixture")
            normalize = descriptor_path_signature
            with patch("tidyup.filesystem.safe_stat", return_value=metadata(ctime=100)), \
                 patch("tidyup.filesystem.os.fstat", side_effect=[before, after]), \
                 patch("tidyup.filesystem.descriptor_path_signature", side_effect=lambda st: normalize(st, windows=windows)):
                return full_hash(source, Path(tmp))

    def test_recycled_change_time_does_not_mean_replacement(self):
        self.assertEqual(self.digest(metadata(ctime=200), metadata(ctime=200)), hashlib.sha256(b"fixture").hexdigest())

    def test_real_identity_replacement_still_blocked(self):
        with self.assertRaises(Blocked) as result:
            self.digest(metadata(ctime=200, inode=3), metadata(ctime=200, inode=3))
        self.assertEqual(result.exception.details["phase"], "open")

    def test_change_time_during_read_still_blocked(self):
        with self.assertRaises(Blocked) as result:
            self.digest(metadata(ctime=200), metadata(ctime=201))
        self.assertEqual(result.exception.details["phase"], "read")

    def test_posix_does_not_normalize_creation_time(self):
        with self.assertRaises(Blocked):
            self.digest(metadata(ctime=200), metadata(ctime=200), windows=False)
