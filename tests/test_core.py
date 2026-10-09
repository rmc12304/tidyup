import hashlib
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from tidyup.core import Engine
from tidyup.filesystem import Blocked, anchored_open, full_hash, safe_stat, signature, validate_roots
from tidyup.storage import Store


class FakeTrash:
    """Simulação SÓ para fixtures. Não representa uma Lixeira nativa."""
    supported = True
    reason = "Adaptador sintético de teste"

    def __init__(self, outcome="success", callback=None):
        self.calls = 0
        self.outcome = outcome
        self.callback = callback

    def recycle_guarded(self, source, preserved):
        self.calls += 1
        if self.callback:
            return self.callback(source, preserved)
        if self.outcome == "success":
            # Apenas uma simulação reversível dentro do TemporaryDirectory.
            Path(source["path"]).rename(source["path"] + ".synthetic-trash")
            return {"status": "success", "native_evidence": "fixture-only", "original_absent": True}
        return {"status": self.outcome, "reason": "Resultado sintético"}


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tidyup-test-")
        self.base = Path(self.tmp.name)
        self.src = self.base / "source"
        self.ref = self.base / "reference"
        self.src.mkdir()
        self.ref.mkdir()
        self.store = Store(self.base / "data")
        self.engine = Engine(self.store)
        self.engine.configure(str(self.src), [str(self.ref)])

    def tearDown(self):
        if self.engine.worker:
            self.engine.worker.join(10)
        self.store.close()
        self.tmp.cleanup()

    def files(self, source=b"identical", reference=b"identical", name="origem.txt", refname="arquivo.txt"):
        a, b = self.src / name, self.ref / refname
        a.write_bytes(source)
        b.write_bytes(reference)
        return a, b

    def scan(self):
        self.engine.start()
        self.engine.worker.join(10)
        self.assertFalse(self.engine.worker.is_alive())
        snapshot = self.engine.snapshot()
        self.assertEqual(snapshot["status"], "completed", snapshot)
        return snapshot

    def make_plan(self, exception=False):
        snapshot = self.scan()
        return self.engine.plan([{"id": item["id"], "exception": exception} for item in snapshot["items"]])

    def test_different_names_identical_content(self):
        self.files()
        job = self.scan()
        self.assertEqual(job["items"][0]["state"], "verified")
        self.assertEqual(job["items"][0]["hash"], hashlib.sha256(b"identical").hexdigest())
        self.assertEqual(len(job["items"][0]["references"]), 1)

    def test_same_name_different_content(self):
        self.files(b"one", b"two", "same", "same")
        self.assertEqual(self.scan()["items"][0]["state"], "similar")

    def test_empty_files(self):
        self.files(b"", b"")
        self.assertEqual(self.scan()["summary"]["verified"], 1)

    def test_no_source_mutations(self):
        a, b = self.files()
        before = [(p.read_bytes(), signature(p.stat())) for p in (a, b)]
        self.scan()
        self.assertEqual(before, [(p.read_bytes(), signature(p.stat())) for p in (a, b)])

    def test_unicode_long_paths_and_recursion(self):
        folder = self.src
        for i in range(8):
            folder /= f"pasta-acentuação-文件-{i}-aaaaaaaa"
            folder.mkdir()
        (folder / "日本語 ç espaço.txt").write_bytes(b"unicode")
        (self.ref / "copia").write_bytes(b"unicode")
        self.assertGreater(len(str(folder / "日本語 ç espaço.txt")), 260)
        self.assertEqual(self.scan()["summary"]["source_files"], 0)
        self.engine.configure(str(self.src), [str(self.ref)], True)
        self.assertEqual(self.scan()["summary"]["verified"], 1)

    def test_streaming_large_fixture(self):
        data = b"x" * (8 * 1024 * 1024 + 13)
        self.files(data, data)
        job = self.scan()
        self.assertEqual(job["bytes_read"], len(data) * 2)
        self.assertEqual(job["summary"]["verified"], 1)

    def test_symlink_escape_and_hardlink(self):
        a, _ = self.files()
        os.symlink(self.ref, self.src / "escape", target_is_directory=True)
        os.link(a, self.src / "hard")
        job = self.scan()
        self.assertEqual(job["summary"]["blocked"], 3)
        self.assertEqual(job["summary"]["verified"], 0)

    def test_overlaps_and_redirected_root(self):
        with self.assertRaises(Blocked):
            validate_roots(str(self.base), [str(self.ref)], self.store.directory)
        with self.assertRaises(Blocked):
            validate_roots(str(self.src), [str(self.src)], self.store.directory)
        os.symlink(self.src, self.base / "alias")
        with self.assertRaises(Blocked):
            validate_roots(str(self.base / "alias"), [str(self.ref)], self.store.directory)

    def test_data_in_repository_rejected(self):
        with self.assertRaises(ValueError):
            Store(Path(__file__).resolve().parent.parent / "operational-data")

    def test_changed_source_or_reference_invalidates_review(self):
        for changed in ("source", "reference"):
            with self.subTest(changed=changed):
                a, b = self.files()
                item = self.scan()["items"][0]
                (a if changed == "source" else b).write_bytes(b"changed")
                with self.assertRaises(Blocked):
                    self.engine.plan([{"id": item["id"], "exception": False}])

    def test_changed_after_plan_blocks_execution(self):
        a, _ = self.files()
        fake = FakeTrash()
        self.engine.adapter = fake
        plan = self.make_plan()
        a.write_bytes(b"changed")
        op = self.engine.execute(plan["id"])
        self.assertEqual(op["results"][0]["status"], "blocked")
        self.assertEqual(fake.calls, 0)

    def test_preserved_removed_after_plan(self):
        _, b = self.files()
        self.engine.adapter = FakeTrash()
        plan = self.make_plan()
        b.rename(self.ref / "other")
        self.assertEqual(self.engine.execute(plan["id"])["results"][0]["status"], "blocked")

    def test_replacement_same_path(self):
        a, _ = self.files()
        self.engine.adapter = FakeTrash()
        plan = self.make_plan()
        a.rename(self.src / "old")
        a.write_bytes(b"identical")
        self.assertEqual(self.engine.execute(plan["id"])["results"][0]["status"], "blocked")

    def test_change_during_hash(self):
        a, _ = self.files(b"x" * 2000000, b"x" * 2000000)
        def mutate(_n):
            a.write_bytes(b"new")
        with self.assertRaises(Blocked):
            full_hash(str(a), str(self.src), progress=mutate)

    def test_same_identity_twice_and_reference_ids(self):
        self.files()
        item = self.scan()["items"][0]
        selection = {"id": item["id"], "exception": False}
        with self.assertRaises(Blocked):
            self.engine.plan([selection, selection])
        with self.assertRaises(Blocked):
            self.engine.plan([{"id": item["references"][0]["id"], "exception": True}])

    def test_exception_is_individual_and_cannot_bypass_block(self):
        self.files(b"different", b"reference")
        item = self.scan()["items"][0]
        with self.assertRaises(Blocked):
            self.engine.plan([{"id": item["id"], "exception": False}])
        plan = self.engine.plan([{"id": item["id"], "exception": True}])
        self.assertTrue(plan["items"][0]["exception"])
        self.assertFalse(plan["executable"])
        with self.assertRaises(Blocked):
            self.engine.execute(plan["id"])

    def test_unavailable_trash_blocks_all_platforms(self):
        self.files()
        plan = self.make_plan()
        self.assertFalse(plan["executable"])
        with self.assertRaises(Blocked):
            self.engine.execute(plan["id"])

    def test_durable_idempotency_and_reference_preservation(self):
        a, b = self.files()
        fake = FakeTrash()
        self.engine.adapter = fake
        plan = self.make_plan()
        first = self.engine.execute(plan["id"])
        second = self.engine.execute(plan["id"])
        restarted = Engine(self.store, fake).execute(plan["id"])
        self.assertEqual(first, second)
        self.assertEqual(first, restarted)
        self.assertEqual(fake.calls, 1)
        self.assertEqual(b.read_bytes(), b"identical")
        # Restauração sintética, NÃO teste da Lixeira do SO.
        Path(str(a) + ".synthetic-trash").rename(a)
        self.assertEqual(hashlib.sha256(a.read_bytes()).hexdigest(), plan["items"][0]["source"]["hash"])

    def test_no_native_evidence_is_uncertain_and_locks_path(self):
        self.files()
        self.engine.adapter = FakeTrash(callback=lambda *_: {"status": "success", "original_absent": True})
        plan = self.make_plan()
        op = self.engine.execute(plan["id"])
        self.assertEqual(op["results"][0]["status"], "uncertain")
        item = self.scan()["items"][0]
        with self.assertRaises(Blocked):
            self.engine.plan([{"id": item["id"], "exception": False}])

    def test_restart_after_intent(self):
        a, _ = self.files()
        self.store.put("operation", "interrupted", {"id": "interrupted", "status": "running", "results": [{"path": str(a), "status": "intent"}]})
        Engine(self.store)
        self.assertEqual(self.store.get("operation", "interrupted")["results"][0]["status"], "uncertain")

    def test_absent_original_overrides_adapter_claim_of_safe_failure(self):
        a, _ = self.files()
        def misleading(source, ref):
            Path(source["path"]).rename(source["path"] + ".synthetic-trash")
            return {"status": "blocked", "native_evidence": {"diagnostic": "fixture"}}
        self.engine.adapter = FakeTrash(callback=misleading)
        plan = self.make_plan()
        op = self.engine.execute(plan["id"])
        self.assertEqual(op["results"][0]["status"], "uncertain")
        self.assertEqual(op["results"][0]["native_evidence"], {"diagnostic": "fixture"})
        self.assertFalse(a.exists())

    def test_partial_failure_cancel_and_no_all_copies_removed(self):
        self.files()
        (self.src / "second").write_bytes(b"identical")
        def cancel(source, ref):
            self.engine.execution_cancel.set()
            return {"status": "failed", "reason": "fixture"}
        self.engine.adapter = FakeTrash(callback=cancel)
        plan = self.make_plan()
        op = self.engine.execute(plan["id"])
        self.assertEqual([r["status"] for r in op["results"]], ["failed", "cancelled"])
        self.assertTrue((self.ref / "arquivo.txt").exists())

    def test_stale_plan_after_rescan(self):
        self.files()
        self.engine.adapter = FakeTrash()
        plan = self.make_plan()
        self.scan()
        with self.assertRaises(Blocked):
            self.engine.execute(plan["id"])

    def test_permission_error_and_cloud_blocked(self):
        self.files()
        with patch("tidyup.core.full_hash", side_effect=PermissionError("Leitura negada")):
            job = self.scan()
        self.assertEqual(job["items"][0]["state"], "blocked")
        class CloudStat:
            st_file_attributes = 0x1000
            st_mode = 0o100644
            st_nlink = 1
        with patch("pathlib.Path.lstat", return_value=CloudStat()):
            with self.assertRaisesRegex(Blocked, "offline"):
                safe_stat(str(self.src / "origem.txt"), str(self.src))

    def test_cancel_hash_resume_and_cache_invalidation(self):
        self.files()
        self.scan()
        job = self.scan()
        self.assertEqual(job["bytes_read"], 0)
        (self.src / "origem.txt").write_bytes(b"different")
        self.assertEqual(self.scan()["summary"]["verified"], 0)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(InterruptedError):
            full_hash(str(self.ref / "arquivo.txt"), str(self.ref), cancel=cancel)

    def test_anchored_open_rejects_ancestor_swap(self):
        inside = self.src / "nested"
        inside.mkdir()
        (inside / "item").write_bytes(b"original")
        (self.ref / "item").write_bytes(b"outside")
        inside.rename(self.src / "previous")
        os.symlink(self.ref, inside)
        with self.assertRaises(OSError):
            anchored_open(inside / "item", os.O_RDONLY)

    def test_unknown_reparse_blocks(self):
        a, _ = self.files()
        class ReparseStat:
            st_file_attributes = 0x400
            st_mode = 0o100644
            st_nlink = 1
        with patch("pathlib.Path.lstat", return_value=ReparseStat()):
            with self.assertRaisesRegex(Blocked, "reparse"):
                safe_stat(str(a), str(self.src))

    def test_cancellation_during_scan_and_restart(self):
        self.files()
        def interrupted(*_args, **_kwargs):
            self.engine.cancel.set()
            raise InterruptedError("fixture")
        with patch("tidyup.core.full_hash", side_effect=interrupted):
            self.engine.start()
            self.engine.worker.join()
        self.assertEqual(self.engine.snapshot()["status"], "cancelled")
        self.assertEqual(self.scan()["summary"]["verified"], 1)
        job = self.store.get("job", "current")
        job["status"] = "running"
        self.store.put("job", "current", job)
        Engine(self.store)
        self.assertEqual(self.engine.snapshot()["status"], "cancelled")

    def test_second_data_instance_rejected(self):
        with self.assertRaisesRegex(ValueError, "outra instância"):
            Store(self.store.directory)

    def test_guarded_adapter_blocks_change_during_native_phase(self):
        a, _ = self.files()
        def race(source, preserved):
            a.write_bytes(b"modified concurrently")
            return {"status": "blocked", "reason": "Simulação de validação nativa: conteúdo mudou"}
        self.engine.adapter = FakeTrash(callback=race)
        plan = self.make_plan()
        self.assertEqual(self.engine.execute(plan["id"])["results"][0]["status"], "blocked")
        self.assertTrue(a.exists())


if __name__ == "__main__":
    unittest.main()
