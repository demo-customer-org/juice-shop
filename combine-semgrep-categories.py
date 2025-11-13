#!/usr/bin/env python3
"""
Combine Semgrep JSON results with Gemini category output.

Example usage:
    python combine-semgrep-categories.py \
        --semgrep-json semgrep.json \
        --categories-txt gemini-output.txt
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_semgrep_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_gemini_categories(path: Path) -> List[Dict[str, Any]]:
    categories: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    current_section: Optional[str] = None

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            stripped = line.strip()

            if not stripped:
                current_section = None
                continue

            if stripped.startswith("category:"):
                label = stripped.split(":", 1)[1].strip()
                current = {"name": label, "risks": []}
                categories.append(current)
                current_section = None
                continue

            if current is None:
                # Skip anything before the first category block.
                continue

            if stripped.startswith("risks:"):
                current_section = "risks"
                continue

            if stripped.startswith("prefixes:") or stripped.startswith("notes:"):
                current_section = None
                continue

            if stripped.startswith("-"):
                item = stripped[1:].strip()
                if current_section == "risks" and item:
                    current["risks"].append(item)
                continue

    return categories


def build_findings_by_risk(results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    findings: Dict[str, List[str]] = defaultdict(list)
    seen_messages: Dict[str, set[str]] = defaultdict(set)

    for result in results:
        check_id = result.get("check_id")
        if not check_id:
            continue

        path = result.get("path", "<unknown>")
        start_info = result.get("start", {}) or {}
        line = start_info.get("line")
        line_repr = str(line) if line is not None else "?"
        message = (result.get("extra", {}) or {}).get("message", "").strip()

        if message:
            description = f"{path}:{line_repr} - {message}"
        else:
            description = f"{path}:{line_repr}"

        message_key = message or f"{path}:{line_repr}"
        if message_key not in seen_messages[check_id]:
            findings[check_id].append(description)
            seen_messages[check_id].add(message_key)

    return findings


def print_combined_output(categories: List[Dict[str, Any]], findings_by_risk: Dict[str, List[str]]) -> None:
    first = True
    for category in categories:
        if not first:
            print()
        first = False

        name = category.get("name", "<unnamed category>")
        risks = category.get("risks", [])
        unique_risks = []
        seen_risks = set()
        for risk in risks:
            if risk and risk not in seen_risks:
                unique_risks.append(risk)
                seen_risks.add(risk)

        print(f"category: {name}")
        print("risks:")
        if unique_risks:
            for risk in unique_risks:
                print(f"  - {risk}")
        else:
            print("  - <none>")

        print("findings:")
        combined_findings: List[str] = []
        for risk in unique_risks:
            combined_findings.extend(findings_by_risk.get(risk, []))

        if combined_findings:
            for finding in combined_findings:
                print(f"  - {finding}")
        else:
            print("  - <no matching findings>")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Combine Semgrep JSON findings with Gemini category output."
    )
    parser.add_argument(
        "--semgrep-json",
        required=True,
        type=Path,
        help="Path to the semgrep --json output file.",
    )
    parser.add_argument(
        "--categories-txt",
        required=True,
        type=Path,
        help="Path to the Gemini categorization output text.",
    )

    args = parser.parse_args()

    semgrep_data = load_semgrep_json(args.semgrep_json)
    results = semgrep_data.get("results", [])
    if not results:
        raise SystemExit("No Semgrep findings present in the provided JSON.")

    categories = parse_gemini_categories(args.categories_txt)
    if not categories:
        raise SystemExit("No categories were parsed from the Gemini output.")

    findings_by_risk = build_findings_by_risk(results)
    print_combined_output(categories, findings_by_risk)


if __name__ == "__main__":
    main()


