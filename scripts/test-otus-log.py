"""No-network lifecycle tests; all evidence is synthetic and temporary."""

import json
import ast
import os
import pathlib
import re
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
        self.assertEqual((directory / "run.log").read_bytes(), b"")

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
                                   ("import os, signal; os.kill(os.getppid(), signal.SIGTERM)", 143)):
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
        for malformed in ('{"schema": "bad"}', "[]", "null", "false", "42"):
            scope.write_text(malformed)
            self.call("scope-check", "--engagement", "test", code=3)
        directory = self.start()
        (directory / "evidence/link").symlink_to(pathlib.Path(self.temporary.name))
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "reject symlink", code=1)

    def test_authorization_requires_explicit_confirmation(self):
        self.call("scope-init", "--engagement", "test", "--authorized-by", "test", "--target", "example.test", code=1)
        self.assertFalse((self.home / "test/scope.json").exists())

    def test_partial_cleanup_is_visible_in_rendered_findings(self):
        directory = self.start()
        self.call("finish", "--run-dir", str(directory), "--status", "partial", "--summary", "Unfinished",
                  "--target-state", "changed", "--cleanup", "owed", "--artifact", "synthetic artifact")
        self.assertIn("Cleanup: owed", (directory / "findings.md").read_text())
        self.assertIn("synthetic artifact", (directory / "findings.md").read_text())

    def test_pipeline_preserves_upstream_failure(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--", "/bin/bash", "-o", "pipefail", "-c",
                  "printf 'one raw line\\n'; false | cat", code=1)
        self.assertEqual((directory / "run.log").read_text(), "one raw line\n")

    def test_json_escaping_and_evidence_inventory(self):
        directory = self.start()
        summary = 'Quoted "text", slash \\, and newline\n'
        self.call("finish", "--run-dir", str(directory), "--status", "partial", "--summary", summary)
        self.assertEqual(self.record(directory)["summary"], summary)
        for filename in ("run.json", "events.jsonl", "run.log", "findings.md"):
            self.assertIn(filename, self.record(directory)["evidence"])

    def test_parallel_events_have_unique_ordered_sequences(self):
        directory = self.start()
        processes = [subprocess.Popen([sys.executable, "-I", str(HELPER), "event", "--run-dir", str(directory),
                                       "--event", "marker", "--note", "synthetic step"], env=self.env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE) for index in range(6)]
        for process in processes:
            output, errors = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, errors.decode())
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        self.assertEqual([event["seq"] for event in events], list(range(1, 8)))

    def test_default_root_is_repo_out_without_writing_there(self):
        environment = dict(self.env)
        environment.pop("OTUS_HOME")
        result = subprocess.run([sys.executable, "-I", "-c",
                                 "import runpy, sys; print(runpy.run_path(sys.argv[1])['root']())", str(HELPER)],
                                env=environment, capture_output=True, timeout=10, check=True)
        self.assertEqual(pathlib.Path(result.stdout.decode().strip()), HELPER.parent.parent / "out")

    def test_archive_restores_every_evidence_file(self):
        directory = self.start()
        self.call("finish", "--run-dir", str(directory), "--status", "partial", "--summary", "Synthetic")
        destination = pathlib.Path(self.temporary.name) / "export.tar.gz"
        self.call("archive", "--engagement", "test", "--out", str(destination))
        restored = pathlib.Path(self.temporary.name) / "restored"
        with tarfile.open(destination) as bundle:
            bundle.extractall(restored, filter="data")
        for original in (self.home / "test").rglob("*"):
            if original.is_file():
                self.assertEqual(original.read_bytes(), (restored / original.relative_to(self.home)).read_bytes())

    def test_skill_root_is_rejected(self):
        self.env["OTUS_HOME"] = str(HELPER.parent.parent / ".claude/skills")
        self.call("init", "--engagement", "test", "--skill", "nuclei", code=1)


class WiringTests(unittest.TestCase):
    def test_all_skills_use_helper_and_versioned_scope(self):
        skills = list((HELPER.parent.parent / ".claude/skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 26)
        for path in skills:
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                for subcommand in ("init --engagement", "scope-check --engagement", "run --run-dir", "finish --run-dir"):
                    self.assertIn(subcommand, text)
                self.assertIn("evidence: ../../scope.json", text)
                self.assertIn("## Checklist", text)
                self.assertLessEqual(len(text.splitlines()), 75)
                self.assertNotRegex(text, r"(?:echo|printf).*\{.*schema")
                self.assertNotRegex(text, r"tee.*\$RUN/run\.log")
                self.assertNotIn("scope.txt", text)
                self.assertNotIn("review.md", text)

    def test_scope_modes_and_locked_agent_writers(self):
        repo = HELPER.parent.parent
        for skill in ("binwalk", "ghidra", "steghide", "wireshark", "hashcat", "review"):
            text = (repo / ".claude/skills" / skill / "SKILL.md").read_text()
            gates = re.findall(r"scripts/otus-log\.py scope-check[^`]+", text)
            self.assertTrue(gates)
            self.assertTrue(all("--target" not in gate for gate in gates), skill)
        pwn = (repo / ".claude/skills/pwntools/SKILL.md").read_text()
        self.assertIn('scope-check --engagement "$ENGAGEMENT" --target "$HOST"', pwn)
        for name in ("reviewer", "reporter"):
            text = (repo / ".claude/agents" / (name + ".md")).read_text()
            tools = next(line for line in text.splitlines() if line.startswith("tools:"))
            self.assertIn("Write", tools)
            self.assertNotIn("python", tools)
            self.assertNotIn("scope.txt", text)
            self.assertNotIn("review.md", text)
            self.assertIn("review.json", text)
            self.assertIn("scope.json", text)
        reporter = (repo / ".claude/agents/reporter.md").read_text()
        self.assertIn("events.jsonl", reporter)
        self.assertIn("inline it **verbatim**", reporter)
        self.assertIn("Save-as-PDF", reporter)
        self.assertNotIn("clock bug", reporter)

    def test_helper_imports_are_stdlib_only(self):
        tree = ast.parse(HELPER.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module.split(".")[0])
        self.assertTrue(imports.issubset(sys.stdlib_module_names))
        self.assertFalse(imports & {"socket", "http", "requests", "httpx"})

    def test_runtime_adapters_match_canonical_generator(self):
        script = HELPER.with_name("build-runtimes.py")
        sources = [HELPER.parent.parent / "CLAUDE.md", HELPER.parent.parent / ".github/copilot-instructions.md"]
        before = [path.read_bytes() for path in sources]
        import runpy
        module = runpy.run_path(str(script))
        contract = (HELPER.parent.parent / "AGENTS.md").read_text()
        for path, appendix in module["TARGETS"].items():
            self.assertEqual(path.read_text(), module["render"](contract, appendix))
        self.assertEqual(before, [path.read_bytes() for path in sources])


if __name__ == "__main__":
    unittest.main()