#!/usr/bin/env python3

"""
Generate Mermaid diagrams for Python and JavaScript files and map dependencies.
*_images.mmd type output

Usage:
    python3 generate_mermaid.py --source path/to/source \
                                --output path/to/mermaid [--local-only]
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List
import os


# TODO: get_local_pip_packages compare and then build mermaid
#from importlib.metadata import distributions
# import json

# def get_pip_packages() -> set[str]:
#     """
#     Return a set of lowercased, top-level package names installed in this interpreter.
#     """
#     names = set()
#     for dist in distributions():
#         name = dist.metadata.get("Name")
#         if name:
#             names.add(name.lower())
#     return names


def parse_args():
    parser = argparse.ArgumentParser(
        description="Map dependencies of Python and JS files and emit Mermaid .mmd files"
    )
    parser.add_argument(
        "--source",
        "-s",
        required=True,
        help="Directory containing source files",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Directory to emit .mmd files",
    )
    # parser.add_argument(
    #     "--local-only",
    #     action="store_true",
    #     help="Generate diagrams *only* for imports within the source tree (ignore pip/stdlib)."
    # )

    return parser.parse_args()

def find_source_files(src_dir: Path) -> List[Path]:
    EXCLUDE_DIRS = {
        "node_modules",
        "venv", ".venv",
        "__pycache__",
        ".pyenv", ".pytest_cache", ".git", ".github",
        "acousticbrainz-highlevel-sample-json-20220623", "tests",
        "mermaid"
    }
    src = str(src_dir)
    files: List[Path] = []

    for root, dirs, filenames in os.walk(src):
        # prune directories so we never descend into them
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for fname in filenames:
            # skip any __init__ file
            if fname == "__init__.py" or fname.startswith(("test_", "tests_")) or fname.endswith(("_test.py", "_test.js")):
                continue

            # only .py or .js
            if not fname.endswith((".py", ".js")):
                continue

            files.append(Path(root) / fname)

    return files

def build_module_map(files: List[Path], src_dir: Path) -> Dict[str, Path]:
    module_map: Dict[str, Path] = {}
    for f in files:
        if not f.is_file():
            continue
        module_name = "/".join(f.relative_to(src_dir).with_suffix("").parts)
        module_map[module_name] = f
    return module_map


PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.,\s]+))")
JS_IMPORT_RE = re.compile(r"^\s*import(?:.*?from)?\s+['\"]([^'\"]+)['\"]")
JS_REQUIRE_RE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")


def _sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def parse_python_dependencies(path: Path, module_map: Dict[str, Path]):
    """
    Returns a dict with three buckets:
      - internal: modules in your source tree
      - pip:      modules installed via pip
      - stdlib:   everything else (assumed stdlib)
    """
    deps = set()
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            m = PY_IMPORT_RE.match(line)
            if not m:
                continue
            mod = m.group(1) or m.group(2)
            if not mod:
                continue
            for item in mod.split(','):
                item = item.strip().split(' ')[0]
                if not item:
                    continue
                deps.add(item.replace('.', '/'))
    internal = sorted(d for d in deps if d in module_map)
    external = sorted(d for d in deps if d not in module_map)


    return {
        "internal": internal,
        "external": external,
    }


def _resolve_js_relative(path: Path, dep: str, src_dir: Path) -> str:
    target = path.parent / dep
    if target.is_dir():
        target = target / "index.js"
    if not target.suffix:
        target = target.with_suffix(".js")
    try:
        rel = target.resolve().relative_to(src_dir.resolve())
        return "/".join(rel.with_suffix("").parts)
    except Exception:
        return dep


def parse_js_dependencies(path: Path, src_dir: Path, module_map: Dict[str, Path]):
    deps = set()
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            m = JS_IMPORT_RE.search(line)
            if m:
                deps.add(m.group(1))
            for m2 in JS_REQUIRE_RE.finditer(line):
                deps.add(m2.group(1))
    resolved = []
    for d in deps:
        if d.startswith('.'):
            mod = _resolve_js_relative(path, d, src_dir)
        else:
            mod = d.replace('.', '/')
        resolved.append(mod)
    internal = sorted(m for m in resolved if m in module_map)
    external = sorted(m for m in resolved if m not in module_map)
    return {"internal": internal, "external": external}


def extract_dependencies(files: List[Path], src_dir: Path, module_map: Dict[str, Path]):
    deps = {}

    for f in files:
        if not f.is_file():
            continue
        if f.suffix == ".py":
            deps[f] = parse_python_dependencies(f, module_map)
        elif f.suffix == ".js":
            deps[f] = parse_js_dependencies(f, src_dir, module_map)
    return deps


def write_mermaid(out_dir: Path, deps: Dict[Path, Dict[str, List[str]]], src_dir: Path):
    expected = set()
    # sort by (total_deps, then filename) ascending
    sorted_files = sorted(
        deps.keys(),
        key=lambda f: (
            len(deps[f]["internal"]) + len(deps[f]["external"]),
            str(f)
        )
    )

    for f in sorted_files:
        mod_name = "/".join(f.relative_to(src_dir).with_suffix("").parts)
        node     = _sanitize(mod_name)

        # 1) compute the dependency count
        total_deps = len(deps[f]["internal"]) + len(deps[f]["external"])
        depends_str = ", ".join(deps[f]["internal"] + deps[f]["external"]) or "(none)"

        # 2) use that count as your prefix (it will repeat for equal counts)
        filename = f"{total_deps}_{node}.mmd"
        expected.add(filename)

        lines = [
            f"%% Module: {mod_name}",
            f"%% Depends on: {depends_str}",
            "graph TD",
        ]
        for d in deps[f]["internal"] + deps[f]["external"]:
            lines.append(f"{node}[{mod_name}] --> {_sanitize(d)}[{d}]")

        (out_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 3) clean up any old diagrams you no longer generate
    for old in out_dir.glob("*.mmd"):
        if old.name not in expected:
            old.unlink()

def main():
    args = parse_args()
    src_dir = Path(args.source).resolve()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = find_source_files(src_dir)
    module_map = build_module_map(files, src_dir)
    deps = extract_dependencies(files, src_dir, module_map)
    write_mermaid(out_dir, deps, src_dir)
    print(f"Generated {len(deps)} diagrams in {out_dir}")


if __name__ == "__main__":
    main()

