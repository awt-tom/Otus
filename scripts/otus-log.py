#!/usr/bin/env python3
"""Local-only evidence writer. See AGENTS.md for the versioned record contracts."""

import argparse
import datetime
import fcntl
import fnmatch
import ipaddress
import json
import math
import os
import pathlib
import re
import selectors
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import contextmanager
from urllib.parse import urlsplit


REPO = pathlib.Path(__file__).resolve().parent.parent
EVENTS = ("run_start", "cmd_start", "cmd", "marker", "guardrail_stop", "run_end")
BLOCKS = ("guardrail:permission-classifier", "guardrail:api-cyber-safeguard")
STOP_REASONS = ("unknown", "completed", "native-budget", "health", "inconclusive",
                "helper-timeout", "interrupted", "error")


def positive_seconds(value):
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("duration must be positive and finite")
    return seconds


def grace_seconds(value):
    seconds = positive_seconds(value)
    if seconds > 30:
        raise argparse.ArgumentTypeError("grace must not exceed 30 seconds")
    return seconds


def observed_units(value):
    count = int(value)
    if count < 0:
        raise argparse.ArgumentTypeError("observed units must be nonnegative")
    return count


def coverage(profile="unspecified", declared=""):
    return {"profile": profile, "declared": declared, "observed": None,
            "omitted": [], "stop_reason": "unknown"}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def slug(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise ValueError("engagement and skill must be short path-free slugs")
    return value


def root():
    directory = pathlib.Path(os.environ.get("OTUS_HOME") or REPO / "out").expanduser().resolve()
    if any(directory.is_relative_to(REPO / name) for name in (".claude/skills", ".git")):
        raise ValueError("evidence root cannot be a skill directory or Git metadata")
    return directory


def inside(path, parent):
    path = pathlib.Path(path).expanduser().absolute()
    if path.is_symlink() or not path.resolve().is_relative_to(parent.resolve()):
        raise ValueError("path escapes evidence root or is a symlink")
    for component in (path, *path.parents):
        if component == parent:
            break
        if component.is_symlink():
            raise ValueError("symlinks are not allowed in evidence paths")
    return path


def engagement_dir(engagement):
    return inside(root() / slug(engagement), root())


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


@contextmanager
def lock(directory, name=".record.lock"):
    path = inside(directory / name, root())
    with path.open("a", encoding="utf-8") as handle:
        path.chmod(0o600)
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def atomic(path, text):
    inside(path, root())
    descriptor, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        pathlib.Path(temporary).unlink(missing_ok=True)


def write_json(path, data):
    atomic(path, json.dumps(data, indent=2, ensure_ascii=True) + "\n")


def host(value):
    value = value.strip()
    if not value or any(character.isspace() for character in value):
        raise ValueError("target must be a host, IP, or URL without whitespace")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    parsed = urlsplit(value if "://" in value else "//" + value)
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError("invalid target or credentials embedded in URL")
    if "://" in value and parsed.scheme not in ("http", "https", "ssh", "tcp"):
        raise ValueError("unsupported target URL scheme")
    parsed.port
    return parsed.hostname.rstrip(".").lower().encode("idna").decode("ascii")


def pattern(value):
    try:
        return str(ipaddress.ip_network(value, strict=True))
    except ValueError:
        if "/" in value and "://" not in value:
            raise ValueError("invalid CIDR or scope target")
    if "*" in value or "?" in value or "[" in value:
        if not value.startswith("*.") or not re.fullmatch(r"\*\.[A-Za-z0-9.-]+", value):
            raise ValueError("scope glob must have the form *.example.test")
        return value.lower().rstrip(".")
    return host(value)


def load_scope(engagement):
    path = inside(engagement_dir(engagement) / "scope.json", root())
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("scope must be a JSON object")
    if (data.get("schema") != "otus/scope@1" or data.get("engagement") != engagement
            or any(field in data and not isinstance(data[field], str) for field in ("authorized_by", "notes"))
            or not isinstance(data.get("targets"), list)
            or data.get("mode", "network") not in ("network", "offline")):
        raise ValueError("invalid scope schema")
    if (data.get("mode", "network") == "network" and not data["targets"]
            or data.get("mode") == "offline" and data["targets"]):
        raise ValueError("network scope needs targets; offline scope must have no network targets")
    datetime.date.fromisoformat(data["date"])
    for target in data["targets"]:
        if not isinstance(target, str) or target != pattern(target):
            raise ValueError("scope targets must be normalized strings")
    return data


def scope_result(engagement, targets):
    try:
        scope = load_scope(engagement)
    except (OSError, ValueError, KeyError, TypeError):
        return 3, "scope.json missing or invalid; coordinator must bind the supplied task scope"
    if scope.get("mode") == "offline" and targets:
        return 2, "offline scope cannot be used for network targets; stop and clarify scope"
    for target in targets:
        try:
            candidate = host(target)
            matched = False
            for allowed in scope["targets"]:
                if "/" in allowed:
                    try:
                        matched = ipaddress.ip_address(candidate) in ipaddress.ip_network(allowed)
                    except ValueError:
                        matched = False
                else:
                    matched = fnmatch.fnmatchcase(candidate, allowed)
                if matched:
                    break
            if not matched:
                return 2, "target is outside the bound task scope; stop and clarify scope"
        except ValueError:
            return 2, "invalid target; stop and ask the user"
    return 0, "scope confirmed"


def target_list(args):
    targets = list(getattr(args, "target", None) or [])
    filename = getattr(args, "targets_file", None)
    if filename:
        lines = pathlib.Path(filename).read_text(encoding="utf-8").splitlines()
        entries = [line.strip() for line in lines if line.strip()]
        if not entries:
            raise ValueError("target list is empty")
        targets.extend(entries)
    return targets


def read_run(directory):
    directory = inside(pathlib.Path(directory), root())
    data = json.loads(inside(directory / "run.json", root()).read_text(encoding="utf-8"))
    if data.get("schema") != "otus/run@1":
        raise ValueError("invalid run schema")
    expected = engagement_dir(data["engagement"]) / slug(data["skill"])
    if directory.parent != expected or pathlib.Path(data["run_dir"]) != directory:
        raise ValueError("run directory does not match its engagement and skill")
    return directory, data


def append_event(directory, event, **fields):
    path = inside(directory / "events.jsonl", root())
    with lock(directory, ".events.lock"):
        sequence = 1
        if path.exists():
            with path.open(encoding="utf-8") as previous:
                for line in previous:
                    sequence = json.loads(line)["seq"] + 1
        data = {"schema": "otus/event@1", "ts": utc(), "seq": sequence,
                "run_dir": str(directory), "event": event, **fields}
        with path.open("a", encoding="utf-8") as handle:
            path.chmod(0o600)
            handle.write(json.dumps(data, ensure_ascii=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def inventory(directory):
    files = []
    for path in sorted(directory.rglob("*")):
        inside(path, root())
        if path.is_file() and not path.name.startswith("."):
            files.append(path.relative_to(directory).as_posix())
    return files


def render(data):
    lines = ["STATUS: " + data["status"] + " - " + data["summary"], ""]
    handback = data["handback"]
    if data["status"] == "error":
        lines += ["## Completed before stop", *handback["completed"], "",
                  "## Target state", handback["target_state"],
                  "Cleanup: " + handback["cleanup"], *handback["artifacts"], "",
                  "## Resolution options", *handback["resolution"], ""]
        if handback["block"]:
            lines += ["The run respected the block and attempted no retry/reword/split/background/bypass.", ""]
    else:
        lines += ["## Target state", handback["target_state"],
                  "Cleanup: " + handback["cleanup"], *handback["artifacts"], ""]
    extent = data.get("coverage")
    lines += ["## Coverage"]
    if extent:
        lines += ["Profile: " + extent["profile"], "Declared set: " + extent["declared"],
                  "Observed units: " + (str(extent["observed"]) if extent["observed"] is not None else "unknown"),
                  "Stop reason: " + extent["stop_reason"], *["Omitted: " + item for item in extent["omitted"]], ""]
    else:
        lines += ["Unknown; no coverage declaration recorded.", ""]
    lines += ["## Findings"]
    for finding in data["findings"]:
        lines += ["", "### " + finding["title"], "Severity: " + finding["severity"],
                  "Target: " + finding.get("target", ""), finding.get("description", ""),
                  "Evidence: " + finding["evidence"]]
    if not data["findings"]:
        lines += ["No confirmed findings recorded."]
    if data["errors"]:
        lines += ["", "## Errors", *data["errors"]]
    return "\n".join(lines) + "\n"


def finalize(directory, data, status, summary, errors=(), **changes):
    if data["finished"] is not None and not (data["status"] == status == "error"):
        raise ValueError("run is already finalized; create a new run instead")
    data.update(changes)
    data.update(status=status, summary=summary, finished=max(utc(), data["started"]))
    data["errors"].extend(errors)
    if status == "error" and not data["errors"]:
        raise ValueError("error runs require --error")
    if status == "complete" and data["handback"]["cleanup"] == "owed":
        raise ValueError("owed cleanup cannot be declared complete")
    if status == "complete" and data.get("coverage", {}).get("stop_reason", "unknown") not in ("unknown", "completed"):
        raise ValueError("incomplete coverage must remain partial or error")
    data["evidence"] = sorted(set(inventory(directory) + ["findings.md"]))
    append_event(directory, "run_end", status=status)
    write_json(directory / "run.json", data)
    atomic(directory / "findings.md", render(data))


def scope_init(args):
    directory = engagement_dir(args.engagement)
    targets = sorted({pattern(value) for value in args.target})
    if (args.offline and targets) or (not args.offline and not targets):
        raise ValueError("provide --target for network scope or --offline without targets")
    mode = "offline" if args.offline else "network"
    private_dir(directory)
    with lock(directory):
        path = inside(directory / "scope.json", root())
        if path.exists() and not args.force:
            previous = load_scope(args.engagement)
            if sorted(set(previous["targets"])) == targets and previous.get("mode", "network") == mode:
                return 0
            raise ValueError("scope.json already binds different targets; never replace task scope implicitly")
        data = {"schema": "otus/scope@1", "engagement": args.engagement,
                "date": utc()[:10], "targets": targets, "notes": args.note}
        if args.authorized_by is not None:
            data["authorized_by"] = args.authorized_by
        if args.offline:
            data["mode"] = mode
        write_json(path, data)
    return 0


def scope_check(args):
    try:
        result, reason = scope_result(args.engagement, target_list(args))
    except (OSError, ValueError):
        result, reason = 2, "target list missing, invalid, or empty; stop and ask the user"
    if result:
        print(reason, file=sys.stderr)
        if args.run_dir:
            directory, data = read_run(args.run_dir)
            if data["engagement"] != args.engagement:
                raise ValueError("scope check engagement differs from run")
            with lock(directory):
                finalize(directory, data, "error", reason, [reason])
    return result


def init(args):
    parent = engagement_dir(args.engagement) / slug(args.skill)
    private_dir(parent)
    pinned = args.run_dir or os.environ.get("OTUS_RUN_DIR")
    name = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = inside(pathlib.Path(pinned) if pinned else parent / name, root())
    if directory.parent != parent or directory.exists():
        raise ValueError("run must be new and immediately below its engagement/skill directory")
    directory.mkdir(mode=0o700)
    for name in ("notes", "evidence", "loot"):
        private_dir(directory / name)
    data = {"schema": "otus/run@1", "skill": args.skill, "engagement": args.engagement,
            "run_dir": str(directory), "target": args.target or "", "started": utc(),
            "finished": None, "status": "partial", "summary": "Run initialized; not finalized",
            "evidence": ["events.jsonl", "run.log", "findings.md"], "items": {}, "findings": [],
            "errors": [], "handback": {"completed": [], "target_state": "unknown",
            "cleanup": "unknown", "artifacts": [], "resolution": ["Resolve the failure before starting a new run."],
            "block": "", "request_id": ""}}
    if args.profile or args.coverage_set:
        data["coverage"] = coverage(slug(args.profile) if args.profile else "unspecified", args.coverage_set or "")
    atomic(directory / "run.log", "")
    write_json(directory / "run.json", data)
    atomic(directory / "findings.md", render(data))
    append_event(directory, "run_start")
    print(directory)
    return 0


def hashcat_outcome(command, child_exit, transcript_path, offset, timeout):
    if pathlib.Path(command[0]).name not in ("hashcat", "hashcat.bin") or "--status-json" not in command:
        return None
    excluded = {"--quiet", "--machine-readable", "--force", "--restore", "--benchmark", "--show", "--left",
                "--keyspace", "--stdout", "--speed-only", "--progress-only", "--identify", "--self-test-disable",
                "--brain-client", "--brain-server", "-I", "-b", "-q", "-h", "-V"}
    if any(argument.partition("=")[0] in excluded for argument in command[1:]):
        return None
    runtime_values = []
    modes = []
    for index, argument in enumerate(command[1:], 1):
        if argument == "--runtime" and index + 1 < len(command):
            runtime_values.append(command[index + 1])
        elif argument.startswith("--runtime="):
            runtime_values.append(argument.partition("=")[2])
        elif argument in ("-m", "--hash-type") and index + 1 < len(command):
            modes.append(command[index + 1])
    if len(modes) != 1 or not modes[0].isdigit() or len(runtime_values) != 1:
        return None
    if not runtime_values[0].isdigit() or not 0 < int(runtime_values[0]) < timeout:
        return None
    with transcript_path.open("rb") as raw:
        raw.seek(offset)
        header = raw.read(8192).decode("utf-8", errors="replace")
        raw.seek(max(offset, raw.seek(0, os.SEEK_END) - 65536))
        tail = raw.read().decode("utf-8", errors="replace")
    if not re.search(r"^hashcat \(v6\.2\.6\) starting\s*$", header, re.MULTILINE):
        return None
    snapshot = None
    for line in tail.splitlines():
        if not line.lstrip().startswith("{"):
            continue
        try:
            value = json.loads(line)
        except ValueError:
            snapshot = None
            continue
        if isinstance(value, dict) and "status" in value:
            snapshot = value
    if not snapshot or type(snapshot.get("status")) is not int or not isinstance(snapshot.get("guess"), dict):
        return None
    progress = snapshot.get("progress")
    recovered = snapshot.get("recovered_hashes")
    for counts in (progress, recovered):
        if (not isinstance(counts, list) or len(counts) != 2
                or any(type(count) is not int or count < 0 for count in counts)
                or counts[0] > counts[1]):
            return None
    if not isinstance(snapshot.get("session"), str) or recovered[1] == 0:
        return None
    if child_exit == 1 and snapshot["status"] == 5 and progress[1] > 0 and progress[0] == progress[1]:
        return "exhausted"
    if child_exit == 4 and snapshot["status"] == 11:
        return "native-budget"
    return None


def run(args):
    directory, data = read_run(args.run_dir)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("run requires a command after --")
    with lock(directory):
        directory, data = read_run(directory)
        if data["finished"] is not None:
            raise ValueError("cannot execute commands in a finalized run")
        try:
            targets = target_list(args) or ([data["target"]] if data["target"] else [])
            result, reason = scope_result(data["engagement"], targets)
        except (OSError, ValueError):
            result, reason = 2, "target list missing, invalid, or empty"
        if result:
            finalize(directory, data, "error", reason, [reason])
            print(reason, file=sys.stderr)
            return result
        metadata = {"executable": pathlib.Path(command[0]).name, "arguments": "[redacted]"}
        started = time.monotonic()
        limits = {"timeout": args.timeout, "grace": args.grace, "policy": args.outcome_policy}
        append_event(directory, "cmd_start", command=metadata, label=args.label, execution=limits)
        process = None
        interrupted = 0
        timed_out = False
        child_exit = None
        console_descriptor = None
        console_blocking = None
        previous = {}

        def terminate(signum, frame):
            nonlocal interrupted
            interrupted = signum

        def signal_group(signum):
            try:
                os.killpg(process.pid, signum)
                return True
            except ProcessLookupError:
                return False

        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, terminate)
        try:
            with inside(directory / "run.log", root()).open("ab") as transcript:
                log_offset = transcript.tell()
                try:
                    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                    os.set_blocking(process.stdout.fileno(), False)
                    try:
                        console_descriptor = sys.stdout.fileno()
                        console_blocking = os.get_blocking(console_descriptor)
                        os.set_blocking(console_descriptor, False)
                    except (OSError, ValueError):
                        console_descriptor = None
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ)
                        output_open = True
                        stopping_at = None
                        while True:
                            now = time.monotonic()
                            child_exit = process.poll()
                            if stopping_at is None and (interrupted or now >= started + args.timeout):
                                timed_out = not interrupted
                                stopping_at = now + args.grace
                                signal_group(signal.SIGTERM)
                            if child_exit is not None and not output_open:
                                if stopping_at is None or not signal_group(0):
                                    break
                            if stopping_at is not None and now >= stopping_at:
                                signal_group(signal.SIGKILL)
                                break
                            boundary = stopping_at if stopping_at is not None else started + args.timeout
                            for ready, mask in selector.select(min(0.1, max(0, boundary - now))):
                                try:
                                    chunk = os.read(ready.fd, 65536)
                                except BlockingIOError:
                                    continue
                                if not chunk:
                                    selector.unregister(process.stdout)
                                    output_open = False
                                    continue
                                transcript.write(chunk)
                                transcript.flush()
                                os.fsync(transcript.fileno())
                                if console_descriptor is not None:
                                    try:
                                        os.write(console_descriptor, chunk)
                                    except OSError:
                                        pass
                        try:
                            child_exit = process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            signal_group(signal.SIGKILL)
                            child_exit = process.poll()
                        drain_until = time.monotonic() + 1
                        while output_open and time.monotonic() < drain_until:
                            try:
                                chunk = os.read(process.stdout.fileno(), 65536)
                            except BlockingIOError:
                                break
                            if not chunk:
                                break
                            transcript.write(chunk)
                        transcript.flush()
                        os.fsync(transcript.fileno())
                    tool_exit = 128 - child_exit if child_exit is not None and child_exit < 0 else child_exit
                    exit_code = 124 if timed_out else (128 + interrupted if interrupted else tool_exit)
                    if exit_code is None:
                        exit_code = 1
                except OSError as error:
                    transcript.write(("Command launch or capture failed: " + str(error) + "\n").encode())
                    transcript.flush()
                    os.fsync(transcript.fileno())
                    if process:
                        try:
                            signal_group(signal.SIGKILL)
                            child_exit = process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            child_exit = process.poll()
                        except ProcessLookupError:
                            pass
                    tool_exit = 127
                    exit_code = 124 if timed_out else (128 + interrupted if interrupted else 127)
        finally:
            if process and process.stdout:
                process.stdout.close()
            if console_descriptor is not None and console_blocking is not None:
                os.set_blocking(console_descriptor, console_blocking)
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        outcome = "success" if exit_code == 0 else "error"
        if not timed_out and not interrupted and exit_code in (1, 4) and args.outcome_policy == "hashcat-v6.2.6":
            classified = hashcat_outcome(command, child_exit, directory / "run.log", log_offset, args.timeout)
            if classified:
                outcome = classified
                exit_code = 0
                if classified == "native-budget":
                    data.setdefault("coverage", coverage())["stop_reason"] = "native-budget"
        execution = {**limits, "duration": round(time.monotonic() - started, 6),
                     "child_exit": child_exit, "helper_exit": exit_code,
                     "outcome": outcome,
                     "stop": "timeout" if timed_out else ("interrupted" if interrupted else "finished")}
        append_event(directory, "cmd", command=metadata, label=args.label,
                     exit=tool_exit if tool_exit is not None else exit_code, execution=execution)
        if exit_code or interrupted:
            reason = ("Command interrupted" if interrupted else
                      "Command exceeded helper deadline" if timed_out else
                      "Command failed with exit " + str(exit_code))
            if "coverage" in data:
                data["coverage"]["stop_reason"] = "interrupted" if interrupted else ("helper-timeout" if timed_out else "error")
            finalize(directory, data, "error", reason, [reason])
        elif outcome == "native-budget":
            write_json(directory / "run.json", data)
            atomic(directory / "findings.md", render(data))
        return exit_code


def event(args):
    directory, data = read_run(args.run_dir)
    with lock(directory):
        directory, data = read_run(directory)
        if data["finished"] is not None:
            raise ValueError("cannot append to finalized run")
        if args.event == "guardrail_stop" and args.block not in BLOCKS:
            raise ValueError("guardrail_stop requires a recognized --block")
        fields = {"note": args.note, "block": args.block, "request_id": args.request_id}
        if args.cmd:
            fields["command"] = {"arguments": "[redacted]"}
        if args.exit is not None:
            fields["exit"] = args.exit
        append_event(directory, args.event, **fields)
        if args.event == "guardrail_stop":
            data["handback"].update(block=args.block, request_id=args.request_id)
            finalize(directory, data, "error", "Platform guardrail stopped the run", [args.block])
    return 0


def finish(args):
    directory, data = read_run(args.run_dir)
    with lock(directory):
        directory, data = read_run(directory)
        if args.profile or args.coverage_set is not None or args.observed is not None or args.omitted or args.stop_reason:
            extent = data.setdefault("coverage", coverage())
            if args.profile:
                extent["profile"] = slug(args.profile)
            if args.coverage_set is not None:
                extent["declared"] = args.coverage_set
            if args.observed is not None:
                extent["observed"] = args.observed
            extent["omitted"].extend(args.omitted)
            if args.stop_reason:
                if (extent["stop_reason"] in ("native-budget", "helper-timeout", "interrupted", "error")
                        and args.stop_reason not in (extent["stop_reason"], "error")):
                    raise ValueError("recorded execution stop cannot be relabeled")
                extent["stop_reason"] = args.stop_reason
        for item in args.item:
            name, value = item.split("=", 1)
            outcome, evidence = value.split(":", 1)
            if outcome not in ("ok", "fail"):
                raise ValueError("item must be id=ok|fail:evidence")
            if evidence != "../../scope.json":
                inside(directory / evidence, directory)
            data["items"][slug(name)] = {"ok": outcome == "ok", "evidence": evidence}
        for text in args.finding:
            finding = dict(field.split("=", 1) for field in text.split(";"))
            if not all(finding.get(key) for key in ("title", "severity", "evidence")):
                raise ValueError("finding requires title, severity, and evidence")
            inside(directory / finding["evidence"], directory)
            if not (directory / finding["evidence"]).is_file():
                raise ValueError("finding evidence must exist in this run")
            if finding["severity"] not in ("info", "low", "medium", "high", "critical"):
                raise ValueError("invalid finding severity")
            data["findings"].append(finding)
        handback = data["handback"]
        handback.update(target_state=args.target_state, cleanup=args.cleanup,
                        completed=args.completed, artifacts=args.artifact, resolution=args.resolution or handback["resolution"])
        if args.cleanup == "verified":
            proof = inside(directory / "loot/cleanup_verify.txt", directory)
            if not proof.is_file() or not proof.stat().st_size:
                raise ValueError("verified cleanup requires nonempty loot/cleanup_verify.txt")
        if args.target_state == "changed" and args.cleanup not in ("owed", "verified"):
            raise ValueError("changed target requires owed or verified cleanup")
        finalize(directory, data, args.status, args.summary, args.error)
    return 0


def archive(args):
    directory = engagement_dir(args.engagement)
    if not directory.is_dir():
        raise ValueError("engagement does not exist")
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = pathlib.Path(args.out or (args.engagement + "-" + timestamp + ".tar.gz")).expanduser().absolute()
    if destination.exists() or destination.is_symlink() or destination.resolve().is_relative_to(directory.resolve()):
        raise ValueError("archive must be new and outside the engagement directory")
    inventory(directory)
    try:
        with destination.open("xb") as handle:
            destination.chmod(0o600)
            with tarfile.open(fileobj=handle, mode="w:gz") as bundle:
                bundle.add(directory, arcname=args.engagement, recursive=True)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    print(destination)
    return 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="subcommand", required=True)
    scope = commands.add_parser("scope-init")
    scope.add_argument("--engagement", required=True)
    scope.add_argument("--authorized-by", help="optional legacy provenance; not an execution prerequisite")
    scope.add_argument("--target", action="append", default=[])
    scope.add_argument("--offline", action="store_true", help="bind a local-only task with no network targets")
    scope.add_argument("--note", default="")
    scope.add_argument("--confirmed", action="store_true", help="accepted for legacy CLI compatibility")
    scope.add_argument("--force", action="store_true")
    scope.set_defaults(handler=scope_init)
    check = commands.add_parser("scope-check")
    check.add_argument("--engagement", required=True)
    check.add_argument("--target", action="append")
    check.add_argument("--targets-file")
    check.add_argument("--run-dir")
    check.set_defaults(handler=scope_check)
    start = commands.add_parser("init")
    start.add_argument("--engagement", required=True)
    start.add_argument("--skill", required=True)
    start.add_argument("--target")
    start.add_argument("--run-dir")
    start.add_argument("--profile")
    start.add_argument("--coverage-set")
    start.set_defaults(handler=init)
    execute = commands.add_parser("run")
    execute.add_argument("--run-dir", required=True)
    execute.add_argument("--label", default="")
    execute.add_argument("--target", action="append")
    execute.add_argument("--targets-file")
    execute.add_argument("--timeout", type=positive_seconds, default=300.0)
    execute.add_argument("--grace", type=grace_seconds, default=5.0)
    execute.add_argument("--outcome-policy", choices=("strict", "hashcat-v6.2.6"), default="strict")
    execute.add_argument("command", nargs=argparse.REMAINDER)
    execute.set_defaults(handler=run)
    mark = commands.add_parser("event")
    mark.add_argument("--run-dir", required=True)
    mark.add_argument("--event", choices=EVENTS, required=True)
    mark.add_argument("--cmd")
    mark.add_argument("--exit", type=int)
    mark.add_argument("--block", choices=BLOCKS, default="")
    mark.add_argument("--request-id", default="")
    mark.add_argument("--note", default="")
    mark.set_defaults(handler=event)
    end = commands.add_parser("finish")
    end.add_argument("--run-dir", required=True)
    end.add_argument("--status", choices=("complete", "partial", "error"), required=True)
    end.add_argument("--summary", required=True)
    for field in ("item", "finding", "error", "completed", "artifact", "resolution"):
        end.add_argument("--" + field, action="append", default=[])
    end.add_argument("--target-state", choices=("unknown", "unchanged", "changed"), default="unknown")
    end.add_argument("--cleanup", choices=("unknown", "not-needed", "verified", "owed"), default="unknown")
    end.add_argument("--profile")
    end.add_argument("--coverage-set")
    end.add_argument("--observed", type=observed_units)
    end.add_argument("--omitted", action="append", default=[])
    end.add_argument("--stop-reason", choices=STOP_REASONS)
    end.set_defaults(handler=finish)
    export = commands.add_parser("archive")
    export.add_argument("--engagement", required=True)
    export.add_argument("--out")
    export.set_defaults(handler=archive)
    return result


def main():
    args = parser().parse_args()
    try:
        return args.handler(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("otus-log: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())