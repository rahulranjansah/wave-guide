#!/usr/bin/env python3
"""
mega_mermaid.py

Read in a JSON map of filename → .mmd content (e.g. all_mermaid.json),
and write out one big `mega_combined.mmd` that:

  - groups nodes into subgraphs by dependency-count prefix
  - lists every node inside its subgraph
  - lists every edge afterwards
  - gives each module its own unique pastel arrow color
  - injects the init spacing line at the top

Usage:
    python3 mega_mermaid.py all_mermaid.json mega_combined.mmd
"""
import json
import re
import sys
from pathlib import Path

PASTEL_COLORS = [
    "#1f77b4",  # muted blue
    "#ff7f0e",  # safety orange
    "#2ca02c",  # cooked asparagus green
    "#d62728",  # brick red
    "#9467bd",  # muted purple
    "#8c564b",  # chestnut brown
    "#e377c2",  # raspberry yogurt pink
    "#7f7f7f",  # middle gray
    "#bcbd22",  # curry yellow-green
    "#17becf",  # blue-teal
    "#aec7e8",  # light sky blue
    "#ffbb78",  # light salmon
    "#98df8a",  # light green
    "#ff9896",  # light coral
    "#c5b0d5",  # pale lavender
    "#c49c94",  # tan
    "#f7b6d2",  # light pink
    "#c7c7c7",  # light gray
    "#dbdb8d",  # pale olive
    "#9edae5",  # light cyan
]


# match lines like `foo_bar[foo_bar] --> baz[...]
EDGE_RE = re.compile(
    r'^\s*'                  # start + optional space
    r'([A-Za-z0-9_-]+)'      # src ID
    r'\s*\[[^\]]+\]\s*'      # src label
    r'-->\s*'                # arrow
    r'([A-Za-z0-9_-]+)'      # dst ID
    r'\s*\[[^\]]+\]'         # dst label
)

def load_data(json_path):
    return json.loads(Path(json_path).read_text(encoding="utf-8"))

def classify(data):
    """
    Returns:
      classes: dict[prefix] = set(module_names)
      edges:   list of (src, dst, prefix)
    """
    classes = {}
    edges = []
    for fname, content in data.items():
        if not fname.lower().endswith(".mmd") or fname == "mega.mmd":
            continue
        prefix = int(fname.split("_", 1)[0])
        stem = Path(fname).stem.split("_", 1)[1]
        classes.setdefault(prefix, set()).add(stem)
        for line in content.splitlines():
            for m in EDGE_RE.finditer(line):
                src, dst = m.groups()
                edges.append((src, dst, prefix))
    return classes, edges

def pick_colors(classes):
    """
    For each dependency-count prefix, assign a distinct pastel to each module
    in that subgraph, cycling through PASTEL_COLORS.
    """
    color_map = {}
    for prefix in sorted(classes):
        # grab all modules in this subgraph
        mods = sorted(classes[prefix])
        for i, mod in enumerate(mods):
            color_map[mod] = PASTEL_COLORS[i % len(PASTEL_COLORS)]
    return color_map

def write_mega(classes, edges, color_map, out_path):
    lines = []

    # 1) init + graph header
    lines.append('%%{init: {"flowchart": {"nodeSpacing": 80, "rankSpacing": 80}}}%%')
    lines.append('graph LR')
    lines.append('')

    # 2) subgraphs (nodes)
    for prefix in sorted(classes):
        lines.append(f'  subgraph "{prefix} dependencies"')
        for node in sorted(classes[prefix]):
            lines.append(f'    {node}[{node}]')
        lines.append('  end')
        lines.append('')

    # 3) edges
    for src, dst, _ in edges:
        lines.append(f'  {src} --> {dst}')
    lines.append('')

    # 4) linkStyle by source‐module
    grouped = {}
    for idx, (src, dst, _) in enumerate(edges):
        grouped.setdefault(src, []).append(str(idx))

    for src in sorted(grouped):
        hexcol   = color_map[src]
        idx_list = ",".join(grouped[src])
        lines.append(f'  %% arrows from {src} → {hexcol}')
        lines.append(f'  linkStyle {idx_list} stroke:{hexcol},color:{hexcol}')
        lines.append('')

    # 5) write out
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote mega diagram to {out_path}")
    print(f"{len(classes)} classes")
    print(f"{len(edges)} total edges")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 mega_mermaid.py all_mermaid.json mega_combined.mmd")
        sys.exit(1)

    data = load_data(sys.argv[1])
    classes, edges = classify(data)
    color_map = pick_colors(classes)
    write_mega(classes, edges, color_map, sys.argv[2])

if __name__ == "__main__":
    main()
