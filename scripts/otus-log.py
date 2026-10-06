#!/usr/bin/env python3
"""Local-only evidence writer. See AGENTS.md for the versioned record contracts."""

import argparse
import datetime
import fcntl
import fnmatch
import ipaddress
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from urllib.parse import urlsplit


REPO = pathlib.Path(__file__).resolve().parent.parent
EVENTS = ("run_start", "cmd_start", "cmd", "marker", "guardrail_stop", "run_end")
BLOCKS = ("guardrail:permission-classifier", "guardrail:api-cyber-safeguard")


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
            or not isinstance(data.get("authorized_by"), str) or not data["authorized_by"].strip()
            or not isinstance(data.get("notes"), str)
            or not isinstance(data.get("targets"), list) or not data["targets"]):
        raise ValueError("invalid scope schema")
    datetime.date.fromisoformat(data["date"])
    for target in data["targets"]:
        if not isinstance(target, str) or target != pattern(target):
            raise ValueError("scope targets must be normalized strings")
    return data


def scope_result(engagement, targets):
    try:
        scope = load_scope(engagement)
    except (OSError, ValueError, KeyError, TypeError):
        return 3, "scope.json missing or invalid; ask the user for explicit authorization"
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
                return 2, "target is outside the authorized allowlist; stop and ask the user"
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
    data["evidence"] = sorted(set(inventory(directory) + ["findings.md"]))
    append_event(directory, "run_end", status=status)
    write_json(directory / "run.json", data)
    atomic(directory / "findings.md", render(data))


def scope_init(args):
    directory = engagement_dir(args.engagement)
    if not args.authorized_by.strip() or not args.confirmed:
        raise ValueError("--confirmed and explicit user-provided --authorized-by are required")
    targets = [pattern(value) for value in args.target]
    private_dir(directory)
    with lock(directory):
        path = inside(directory / "scope.json", root())
        if path.exists() and not args.force:
            raise ValueError("scope.json already exists; never replace authorization implicitly")
        write_json(path, {"schema": "otus/scope@1", "engagement": args.engagement,
                         "authorized_by": args.authorized_by, "date": utc()[:10],
                         "targets": targets, "notes": args.note})
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
    atomic(directory / "run.log", "")
    write_json(directory / "run.json", data)
    atomic(directory / "findings.md", render(data))
    append_event(directory, "run_start")
    print(directory)
    return 0


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
        append_event(directory, "cmd_start", command=metadata, label=args.label)
        process = None
        interrupted = False
        previous = {}

        def terminate(signum, frame):
            nonlocal interrupted
            interrupted = signum
            if process:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, terminate)
        try:
            with inside(directory / "run.log", root()).open("ab") as transcript:
                try:
                    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                    if interrupted:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    while True:
                        chunk = process.stdout.read1(65536)
                        if not chunk:
                            break
                        transcript.write(chunk)
                        transcript.flush()
                        os.fsync(transcript.fileno())
                        try:
                            sys.stdout.buffer.write(chunk)
                            sys.stdout.buffer.flush()
                        except BrokenPipeError:
                            pass
                    exit_code = process.wait()
                    exit_code = 128 - exit_code if exit_code < 0 else exit_code
                    if interrupted:
                        exit_code = 128 + interrupted
                except OSError:
                    exit_code = 127
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        append_event(directory, "cmd", command=metadata, label=args.label, exit=exit_code)
        if exit_code or interrupted:
            reason = "Command interrupted" if interrupted else "Command failed with exit " + str(exit_code)
            finalize(directory, data, "error", reason, [reason])
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
    scope.add_argument("--authorized-by", required=True)
    scope.add_argument("--target", action="append", required=True)
    scope.add_argument("--note", default="")
    scope.add_argument("--confirmed", action="store_true")
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
    start.set_defaults(handler=init)
    execute = commands.add_parser("run")
    execute.add_argument("--run-dir", required=True)
    execute.add_argument("--label", default="")
    execute.add_argument("--target", action="append")
    execute.add_argument("--targets-file")
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