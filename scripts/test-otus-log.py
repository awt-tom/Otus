"""No-network lifecycle tests; all evidence is synthetic and temporary."""

import json
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest


HELPER = pathlib.Path(__file__).with_name("otus-log.py")


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = pathlib.Path(self.temporary.name) / "evidence"
        self.env = {**os.environ, "OTUS_HOME": str(self.home)}
        self.env.pop("OTUS_RUN_DIR", None)

    def call(self, *args, code=0):
        result = subprocess.run([sys.executable, "-I", str(HELPER), *args],
                                env=self.env, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stderr.decode())
        return result

    def authorize(self):
        self.call("scope-init", "--engagement", "test", "--authorized-by", "synthetic-test-user",
                  "--confirmed", "--target", "example.test", "--target", "*.example.test",
                  "--target", "192.0.2.0/24")

    def start(self, target=None):
        args = ["init", "--engagement", "test", "--skill", "nuclei"]
        if target:
            args += ["--target", target]
        return pathlib.Path(self.call(*args).stdout.decode().strip())

    def record(self, directory):
        return json.loads((directory / "run.json").read_text())

    def test_scope_exact_glob_cidr_and_exit_codes(self):
        self.call("scope-check", "--engagement", "test", code=3)
        self.authorize()
        for target in ("example.test", "https://API.example.test:443/path", "192.0.2.42"):
            self.call("scope-check", "--engagement", "test", "--target", target)
        for target in ("outside.test", "192.0.3.42"):
            self.call("scope-check", "--engagement", "test", "--target", target, code=2)
        self.call("scope-init", "--engagement", "test", "--authorized-by", "test", "--confirmed",
                  "--target", "outside.test", code=1)

    def test_failure_writes_raw_log_and_error_handback(self):
        self.authorize()
        directory = self.start("example.test")
        self.call("run", "--run-dir", str(directory), "--", sys.executable, "-c",
                  "import sys; print('raw stdout'); print('raw stderr', file=sys.stderr); sys.exit(7)", code=7)
        data = self.record(directory)
        self.assertEqual(data["status"], "error")
        self.assertGreaterEqual(data["finished"], data["started"])
        self.assertIn(b"raw stderr", (directory / "run.log").read_bytes())
        self.assertIn("## Resolution options", (directory / "findings.md").read_text())
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        self.assertEqual([event["event"] for event in events], ["run_start", "cmd_start", "cmd", "run_end"])
        self.assertEqual(events[-2]["exit"], 7)

    def test_success_and_archive_roundtrip(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--", sys.executable, "-c", "print('no findings')")
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "No hits",
                  "--item", "scope-confirmed=ok:../../scope.json", "--target-state", "unchanged", "--cleanup", "not-needed")
        self.assertEqual((directory / "run.log").read_text(), "no findings\n")
        bundle = pathlib.Path(self.temporary.name) / "saved.tar.gz"
        self.call("archive", "--engagement", "test", "--out", str(bundle))
        with tarfile.open(bundle) as archive:
            member = archive.extractfile("test/nuclei/" + directory.name + "/run.json")
            self.assertEqual(json.load(member), self.record(directory))
        self.call("archive", "--engagement", "test", "--out", str(self.home / "test/self.tar.gz"), code=1)

    def test_denied_scope_records_error_without_authorization(self):
        directory = self.start()
        self.call("scope-check", "--engagement", "test", "--run-dir", str(directory), code=3)
        self.assertEqual(self.record(directory)["status"], "error")
        self.assertFalse((self.home / "test/scope.json").exists())
        self.call("run", "--run-dir", str(directory), "--", sys.executable, "-c", "print('must not run')", code=1)
        self.assertEqual((directory / "run.log").read_text(), "")

    def test_missing_executable_is_recorded(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--", "/nonexistent/otus-test-command", code=127)
        self.assertEqual(self.record(directory)["status"], "error")

    def test_all_batch_targets_are_checked(self):
        self.authorize()
        directory = self.start()
        hosts = pathlib.Path(self.temporary.name) / "hosts.txt"
        hosts.write_text("example.test\noutside.test\n")
        self.call("run", "--run-dir", str(directory), "--targets-file", str(hosts), "--",
                  sys.executable, "-c", "print('must not run')", code=2)
        self.assertEqual((directory / "run.log").read_text(), "")

    def test_metadata_redacts_arguments(self):
        self.authorize()
        directory = self.start()
        secret = "synthetic-secret-not-a-real-credential"
        self.call("run", "--run-dir", str(directory), "--", sys.executable, "-c", "pass", secret)
        self.assertNotIn(secret, (directory / "events.jsonl").read_text())

    def test_unique_pinned_and_escape_paths(self):
        self.assertNotEqual(self.start(), self.start())
        directory = self.start()
        self.call("init", "--engagement", "test", "--skill", "nuclei", "--run-dir", str(directory), code=1)
        self.call("init", "--engagement", "../escape", "--skill", "nuclei", code=1)
        self.call("init", "--engagement", "test", "--skill", "nuclei", "--run-dir", self.temporary.name, code=1)

    def test_guardrail_event_finalizes_without_command(self):
        directory = self.start()
        self.call("event", "--run-dir", str(directory), "--event", "guardrail_stop",
                  "--block", "guardrail:permission-classifier", "--request-id", "test-request")
        self.assertEqual(self.record(directory)["handback"]["request_id"], "test-request")
        self.assertIn("respected the block", (directory / "findings.md").read_text())
        self.assertEqual((directory / "run.log").read_text(), "")

    def test_cleanup_and_finding_validation(self):
        self.authorize()
        directory = self.start()
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "done",
                  "--target-state", "changed", "--cleanup", "verified", code=1)
        proof = directory / "evidence/proof.txt"
        proof.write_text("synthetic proof\n")
        self.call("finish", "--run-dir", str(directory), "--status", "partial", "--summary", "cleanup owed",
                  "--finding", "title=Test;severity=info;evidence=evidence/proof.txt",
                  "--target-state", "changed", "--cleanup", "owed", "--artifact", "synthetic artifact")
        self.assertIn("Test", (directory / "findings.md").read_text())

    def test_timeout_and_signal_finalize_error(self):
        self.authorize()
        for command, exit_code in (("import sys; sys.exit(124)", 124),
                                   ("import os, signal; os.kill(os.getppid(), signal.SIGTERM)", 137)):
            directory = self.start()
            self.call("run", "--run-dir", str(directory), "--", sys.executable, "-c", command, code=exit_code)
            self.assertEqual(self.record(directory)["status"], "error")

    def test_error_can_be_enriched_but_never_reopened(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--", sys.executable, "-c", "raise SystemExit(1)", code=1)
        self.call("finish", "--run-dir", str(directory), "--status", "error", "--summary", "failed after change",
                  "--target-state", "changed", "--cleanup", "owed", "--artifact", "synthetic artifact")
        self.assertEqual(self.record(directory)["handback"]["cleanup"], "owed")
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "cannot reopen", code=1)

    def test_symlinks_and_invalid_scope_are_rejected(self):
        self.authorize()
        scope = self.home / "test/scope.json"
        scope.write_text('{"schema": "bad"}')
        self.call("scope-check", "--engagement", "test", code=3)
        directory = self.start()
        (directory / "evidence/link").symlink_to(pathlib.Path(self.temporary.name))
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "reject symlink", code=1)

    def test_authorization_requires_explicit_confirmation(self):
        self.call("scope-init", "--engagement", "test", "--authorized-by", "test", "--target", "example.test", code=1)
        self.assertFalse((self.home / "test/scope.json").exists())


if __name__ == "__main__":
    unittest.main()