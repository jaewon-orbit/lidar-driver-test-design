"""Build docs/05_traceability.csv from the requirement table, GAP summary and test cases.

Sources:
  docs/03_test_design.md   requirement table (rows starting with "| REQ-")
  docs/02_gap_analysis.md  GAP summary table (rows starting with "| GAP-")
  docs/04_test_cases.csv   req_or_gap column

Coverage rule:
  Full     at least one direct test case, and at least one of them at L1 or L2
  Partial  test cases exist, but only at L3 or L4, or only through a linked GAP
  None     no test case
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

DOCS = Path("docs")
OUT = DOCS / "05_traceability.csv"

# Requirements affected by each GAP. A test case linked to a GAP also counts
# as indirect coverage for these requirements.
GAP_TO_REQ = {
    "GAP-001": ["REQ-MODEL-01", "REQ-RM-01", "REQ-ROT-01", "REQ-DIAG-01"],
    "GAP-002": ["REQ-ROT-01"],
    "GAP-003": ["REQ-PTP-05"],
    "GAP-004": ["REQ-SCH-01"],
    "GAP-005": ["REQ-NET-02"],
    "GAP-006": ["REQ-CUT-01"],
    "GAP-007": ["REQ-PTP-03"],
    "GAP-008": ["REQ-NET-03"],
    "GAP-009": ["REQ-RNG-01"],
    "GAP-010": ["REQ-DIAG-01", "REQ-ROT-01"],
    "GAP-011": ["REQ-DIAG-01"],
    "GAP-012": ["REQ-RM-01"],
    "GAP-013": ["REQ-FOV-01"],
    "GAP-014": [],
    "GAP-015": [],
}


def table_rows(path, prefix):
    rows = {}
    for line in path.read_text().splitlines():
        if line.startswith(f"| {prefix}"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows[cells[0]] = cells[1]
    return rows


def main():
    reqs = table_rows(DOCS / "03_test_design.md", "REQ-")
    gaps = table_rows(DOCS / "02_gap_analysis.md", "GAP-")
    with open(DOCS / "04_test_cases.csv", newline="") as f:
        tcs = list(csv.DictReader(f))

    level = {tc["tc_id"]: tc["executable_level"] for tc in tcs}
    direct = defaultdict(list)
    for tc in tcs:
        direct[tc["req_or_gap"]].append(tc["tc_id"])

    problems = []
    for key in direct:
        if key not in reqs and key not in gaps:
            problems.append(f"test cases point to unknown item {key}")
    for gap in gaps:
        if gap not in GAP_TO_REQ:
            problems.append(f"{gap} has no entry in GAP_TO_REQ")
    for gap, linked in GAP_TO_REQ.items():
        for req in linked:
            if req not in reqs:
                problems.append(f"{gap} links to unknown requirement {req}")

    rows = []
    for item, desc in list(reqs.items()) + list(gaps.items()):
        if item.startswith("REQ-"):
            kind = "REQ"
            linked = [g for g, rs in GAP_TO_REQ.items() if item in rs]
            via = [t for g in linked for t in direct.get(g, [])]
        else:
            kind = "GAP"
            linked = GAP_TO_REQ.get(item, [])
            via = []
        own = direct.get(item, [])
        levels = sorted({level[t] for t in own + via})
        if own and any(level[t] in ("L1", "L2") for t in own):
            coverage = "Full"
        elif own or via:
            coverage = "Partial"
        else:
            coverage = "None"
        rows.append([
            item, kind, desc, ", ".join(linked), ", ".join(own),
            ", ".join(via), ", ".join(levels), coverage,
        ])

    with open(OUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "item", "type", "description", "linked", "direct_test_cases",
            "via_gap_test_cases", "levels", "coverage",
        ])
        writer.writerows(rows)

    counts = defaultdict(int)
    for r in rows:
        counts[(r[1], r[7])] += 1
    print(f"wrote {OUT} ({len(rows)} rows)")
    for kind in ("REQ", "GAP"):
        summary = ", ".join(f"{c}={counts[(kind, c)]}" for c in ("Full", "Partial", "None"))
        print(f"{kind}: {summary}")
    print("\nNot Full:")
    for r in rows:
        if r[7] != "Full":
            direct_info = r[4] or "no direct test case"
            print(f"  {r[0]} [{r[7]}] {direct_info}; levels: {r[6] or '-'}")
    if problems:
        print("\nProblems:")
        for p in problems:
            print(f"  {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
