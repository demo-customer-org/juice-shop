#!/usr/bin/env python3

import argparse
import json
import os
from collections import defaultdict
from typing import Any, Dict, List

from google import genai
from google.genai import types


def load_semgrep_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def prefix_for_check(check_id: str, depth: int) -> str:
    parts = check_id.split(".")
    return ".".join(parts[:depth]) if len(parts) > depth else check_id


def bucket_findings(results: List[Dict[str, Any]], depth: int) -> Dict[str, List[Dict[str, Any]]]:
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for finding in results:
        check_id = finding.get("check_id")
        if not check_id:
            continue
        bucket_key = prefix_for_check(check_id, depth)
        buckets[bucket_key].append(finding)
    return buckets


def summarize_buckets(buckets: Dict[str, List[Dict[str, Any]]], sample_size: int = 5) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for prefix, findings in sorted(buckets.items()):
        unique_checks = sorted({item["check_id"] for item in findings})
        sample_locations = []
        for item in findings[:sample_size]:
            path = item.get("path", "<unknown>")
            line = item.get("start", {}).get("line", "?")
            sample_locations.append(f"{path}:{line}")
        summaries.append(
            {
                "prefix": prefix,
                "total_findings": len(findings),
                "unique_check_ids": unique_checks,
                "sample_locations": sample_locations,
            }
        )
    return summaries


PROMPT_TEMPLATE = """You are a security triage assistant. You receive Semgrep findings grouped by deterministic namespaces.

Each bucket includes:
- prefix: the shared namespace of the checks
- total_findings: how many individual matches were observed
- unique_check_ids: the exact Semgrep checks in that namespace
- sample_locations: example file:line pairs

Your tasks:
1. Treat each deterministic prefix as a potential standalone category; only merge prefixes when their risks are effectively identical.
2. When you do merge multiple prefixes, explicitly explain why they belong together and list all member prefixes.
3. Keep categories granular—aim for one prefix per category when distinctions exist.
4. Output the result as plain text blocks in this format (one block per category):

   category: <short descriptive label>
     prefixes:
       - <prefix>
     risks:
       - <check_id>
     notes: <short justification of why these are grouped>

Here are the buckets you must classify:
{bucket_summary}
"""


def build_prompt(bucket_summary: List[Dict[str, Any]]) -> str:
    serialized = json.dumps(bucket_summary, indent=2, ensure_ascii=False)
    return PROMPT_TEMPLATE.format(bucket_summary=serialized)


def call_gemini(prompt: str) -> str:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        )
    ]

    fragments: List[str] = []
    for chunk in client.models.generate_content_stream(model=model, contents=contents):
        fragments.append(chunk.text or "")

    return "".join(fragments).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Group Semgrep findings into human-readable risk categories using Gemini."
    )
    parser.add_argument(
        "--semgrep-json",
        required=True,
        help="Path to a semgrep --json output file.",
    )
    parser.add_argument(
        "--prefix-depth",
        type=int,
        default=3,
        help="Number of namespace segments to use for deterministic bucketing (default: 3).",
    )
    args = parser.parse_args()

    data = load_semgrep_json(args.semgrep_json)
    results = data.get("results", [])
    if not results:
        raise SystemExit("No Semgrep findings present in the provided JSON.")

    buckets = bucket_findings(results, args.prefix_depth)
    bucket_summary = summarize_buckets(buckets)
    prompt = build_prompt(bucket_summary)

    llm_response = call_gemini(prompt)

    print(llm_response)


if __name__ == "__main__":
    main()


