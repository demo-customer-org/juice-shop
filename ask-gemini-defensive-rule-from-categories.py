#!/usr/bin/env python3
"""
Generate a defensive rule using categorized Semgrep findings and Gemini.
"""

import os
import re
import argparse
from google import genai
from google.genai import types


def load_categories_text(raw_text: str | None) -> str:
    if raw_text:
        return raw_text.strip()

    raise ValueError(
        "Categorized Semgrep findings not provided. Supply the text via --categories-text."
    )


CANONICAL_MESSAGE = """    message: >
      Whenever you edit, touch, or modify code flagged by this rule you must
      refactor it immediately to remove the insecure pattern. Never leave the
      vulnerability intact in the updated code.
"""


DEFAULT_DESCRIPTION = "Gemini-Generated Guardrail"


def build_header(description: str) -> str:
    desc = description.strip() or DEFAULT_DESCRIPTION
    escaped = desc.replace('"', '\\"')
    return f"""---
description: "{escaped}"
globs: ["**/*"]
alwaysApply: false
---"""


def extract_summary_and_body(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    summary = ""
    body_start = 0
    for idx, line in enumerate(lines):
        if line.lower().startswith("summary:"):
            summary = line[len("summary:"):].strip()
            body_start = idx + 1
            break
    body = "\n".join(lines[body_start:]).lstrip("\n")
    return summary, body


def strip_code_fences(text: str) -> str:
    fenced_match = re.fullmatch(r"```[^\n]*\n(?P<body>.*)\n```", text.strip(), re.DOTALL)
    if fenced_match:
        return fenced_match.group("body").strip()
    return text.strip()


def build_prompt(categories_text: str) -> str:
    return f"""You are a security-focused code assistant. You must generate an LLM guardrail rule file in the existing format shown below:

Given the following categorized Semgrep findings:

{categories_text}

Tasks for the assistant:
1. **You must begin the response with a line formatted exactly as `summary: <single sentence>`** describing what the resulting rule enforces. Do not start the sentence with phrases like "This rule" or "This guardrail"; instead, begin directly with the action or protection being enforced. If you cannot supply the `summary:` line, respond with the literal text `FORMAT_ERROR`.
2. Generate a `rules` array that captures this vulnerability class.
3. Add pattern matchers that detect the unsafe code constructs highlighted by the Semgrep findings. Cover every risky variation observed (e.g., different concatenation or interpolation forms).
4. Include references to relevant documentation and the Semgrep rule URL.
5. Provide remediation guidance that tells the coding assistant exactly how to generate secure code (e.g., which safe APIs or patterns to use).
6. Set the `message` field exactly to the literal text `PLACEHOLDER_MESSAGE` (do not alter it).
7. Infer the appropriate languages list (e.g., [javascript, typescript]) from the Semgrep finding.
8. Set severity based on the risk level implied by the finding (e.g., ERROR for critical issues).
9. Write remediation as plain paragraphs (no Markdown code fences or fenced code blocks).

Respond with the summary followed by the `rules` array using this exact YAML structure (replace the ??? values but preserve the shape and indentation). Do NOT include the YAML front-matter header; it will be added for you:

summary: ???
rules:
  - id: ???
    languages: [???]  # single line list
    message: PLACEHOLDER_MESSAGE
    severity: ???
    patterns:
      - pattern-either:
          - pattern: ???  # add additional - pattern entries as needed
    metadata:
      references:
        - ???
        - ???
      remediation: >
        ???
"""


def choose_description(summary: str, categories_text: str) -> str:
    if summary:
        return summary

    for line in categories_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("category:"):
            candidate = stripped.split(":", 1)[1].strip()
            if candidate:
                return candidate

    return DEFAULT_DESCRIPTION


def ask_gemini(categories_text: str) -> str:
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
    prompt = build_prompt(categories_text)

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    response_fragments: list[str] = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
    ):
        response_fragments.append(chunk.text or "")

    combined_response = "".join(response_fragments).strip()
    stripped_response = strip_code_fences(combined_response)
    summary, body = extract_summary_and_body(stripped_response)
    description = choose_description(summary, categories_text)
    header = build_header(description)
    final_body = body.replace(
        "    message: PLACEHOLDER_MESSAGE", CANONICAL_MESSAGE.rstrip()
    ).lstrip()
    final_output = f"{header}\n\n{final_body}"
    return final_output


def split_category_blocks(categories_text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []

    for line in categories_text.splitlines():
        if line.startswith("category:"):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
        if line.strip() == "" and not current:
            # Skip leading blank lines
            continue
        current.append(line)

    if current:
        blocks.append("\n".join(current).strip())

    return blocks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate defensive rules from categorized Semgrep findings using Gemini."
    )
    parser.add_argument(
        "--categories-text",
        type=str,
        help="Categorized Semgrep findings text.",
    )
    parser.add_argument(
        "--first-only",
        action="store_true",
        help="Only generate a rule for the first category block.",
    )
    args = parser.parse_args()

    categories = load_categories_text(args.categories_text)
    blocks = split_category_blocks(categories)

    if not blocks:
        raise ValueError("No category blocks found in provided text.")

    if args.first_only:
        blocks = blocks[:1]

    outputs = [ask_gemini(block) for block in blocks]

    print("\n\n".join(outputs))

