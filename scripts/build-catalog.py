#!/usr/bin/env python3
"""Regenerate docs/catalog.md — the human browse-index of Otus skills.

Reads the YAML frontmatter (name, description, category, domain) of every
`.claude/skills/*/SKILL.md` and writes docs/catalog.md with two views:

  * "By function" — skills grouped by `category`
  * "By domain"   — skills grouped by `domain`

Output is sorted and deterministic (stable across runs). Stdlib only, no network.
Run from anywhere:

    python3 -I scripts/build-catalog.py
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills"
OUT = ROOT / "docs" / "catalog.md"

# Canonical display order for the two groupings (see docs/authoring.md §4).
CATEGORY_ORDER = [
    "recon",
    "web",
    "access",
    "ad-network",
    "privesc-creds",
    "re-forensics",
    "meta",
]
DOMAIN_ORDER = [
    "web",
    "ad",
    "network",
    "host",
    "crypto",
    "binary",
    "forensics",
    "misc",
]

GENERATED_HEADER = (
    "<!-- GENERATED from .claude/skills/*/SKILL.md frontmatter — do not edit directly.\n"
    "     Regenerate with: python3 -I scripts/build-catalog.py -->\n"
)

_SCALAR_KEYS = ("name", "category", "domain")


def _frontmatter(text: str) -> str:
    """Return the text between the first pair of `---` fences, or '' if absent."""
    if not text.startswith("---"):
        return ""
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return ""
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            return "\n".join(parts[1:i])
    return ""


def _strip_comment(value: str) -> str:
    """Drop a trailing ` # ...` YAML comment from a simple scalar value."""
    return re.split(r"\s+#", value, maxsplit=1)[0].strip().strip("'\"")


def parse_skill(path: pathlib.Path) -> dict:
    """Minimal frontmatter parse for name/category/domain scalars + folded description."""
    fm = _frontmatter(path.read_text(encoding="utf-8"))
    data = {"name": "", "description": "", "category": "", "domain": ""}
    lines = fm.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        for key in _SCALAR_KEYS:
            m = re.match(rf"^{key}:\s*(.*)$", line)
            if m:
                data[key] = _strip_comment(m.group(1))
                break
        m = re.match(r"^description:\s*(.*)$", line)
        if m:
            first = m.group(1).strip()
            if first in (">", "|", ">-", "|-", ">+", "|+"):
                # Folded/literal block: gather indented continuation lines.
                block = []
                i += 1
                while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                    block.append(lines[i].strip())
                    i += 1
                data["description"] = " ".join(w for w in block if w).strip()
                continue
            data["description"] = _strip_comment(first)
        i += 1
    # Collapse any residual internal whitespace runs in the description.
    data["description"] = re.sub(r"\s+", " ", data["description"]).strip()
    return data


def _ordered_groups(skills: list, key: str, order: list) -> list:
    """Yield (group_value, [skills]) in canonical order, with any extras appended sorted."""
    present = {s[key] for s in skills}
    ordered = [g for g in order if g in present]
    ordered += sorted(present - set(order))
    out = []
    for g in ordered:
        members = sorted((s for s in skills if s[key] == g), key=lambda s: s["name"])
        out.append((g, members))
    return out


def _render_view(skills: list, group_key: str, label_key: str, order: list) -> str:
    lines = []
    for group, members in _ordered_groups(skills, group_key, order):
        lines.append(f"### {group}")
        lines.append("")
        for s in members:
            lines.append(f"- **{s['name']}** — {s['description']} _({s[label_key]})_")
        lines.append("")
    return "\n".join(lines).rstrip()


def render(skills: list) -> str:
    skills = sorted(skills, key=lambda s: s["name"])
    by_function = _render_view(skills, "category", "domain", CATEGORY_ORDER)
    by_domain = _render_view(skills, "domain", "category", DOMAIN_ORDER)
    return (
        f"{GENERATED_HEADER}\n"
        "# Otus skill catalog\n\n"
        f"{len(skills)} skills, each a flat runbook at `.claude/skills/<tool>/SKILL.md`. "
        "This index is generated from skill frontmatter — see `docs/authoring.md` to add one.\n\n"
        "## By function\n\n"
        "Grouped by `category`; each row is **name** — description — _(domain)_.\n\n"
        f"{by_function}\n\n"
        "## By domain\n\n"
        "Grouped by `domain`; each row is **name** — description — _(category)_.\n\n"
        f"{by_domain}\n"
    )


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"error: {SKILLS_DIR} not found", file=sys.stderr)
        return 1
    skills = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        data = parse_skill(skill_md)
        missing = [k for k, v in data.items() if not v]
        if missing:
            print(
                f"error: {skill_md.relative_to(ROOT)} missing frontmatter: {', '.join(missing)}",
                file=sys.stderr,
            )
            return 1
        skills.append(data)
    if not skills:
        print(f"error: no skills found under {SKILLS_DIR}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(skills), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(skills)} skills)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
