from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from discussion.phases import PHASES


TOPIC = "Where should the Dunphy family go on vacation?"


def _to_blockquote(text: str) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return ["> _(No content)_"]
    return [f"> {line}" if line.strip() else ">" for line in cleaned.splitlines()]


def build_transcript_markdown(messages: Iterable[dict], model: str, mode: str) -> str:
    generated_at = datetime.now().replace(microsecond=0).isoformat()

    lines = [
        "# Dunphy Family Vacation Discussion Transcript",
        "",
        "> Structured transcript export for archival and review.",
        "",
        "## Session Snapshot",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Topic | {TOPIC} |",
        f"| Model | {model} |",
        f"| Mode | {mode} |",
        f"| Generated At | {generated_at} |",
        "",
        "---",
        "",
    ]

    grouped: dict[int, list[dict]] = {p.phase_number: [] for p in PHASES.values()}
    extras: list[dict] = []

    for message in messages:
        phase_number = message.get("phase_number")
        if isinstance(phase_number, int) and phase_number in grouped:
            grouped[phase_number].append(message)
        else:
            extras.append(message)

    total_messages = sum(len(items) for items in grouped.values()) + len(extras)
    lines.extend(
        [
            "## Discussion Flow",
            "",
            f"- Total captured messages: **{total_messages}**",
            f"- Defined phases: **{len(PHASES)}**",
            "",
            "| Phase | Name | Messages |",
            "| --- | --- | ---: |",
        ]
    )

    for phase_def in sorted(PHASES.values(), key=lambda p: p.phase_number):
        lines.append(
            f"| {phase_def.phase_number} | {phase_def.name} | {len(grouped[phase_def.phase_number])} |"
        )
    if extras:
        lines.append(f"| - | Additional Messages | {len(extras)} |")
    lines.extend(["", "---", ""])

    for phase_def in sorted(PHASES.values(), key=lambda p: p.phase_number):
        phase_messages = grouped[phase_def.phase_number]
        lines.extend(
            [
                f"## Phase {phase_def.phase_number} - {phase_def.name}",
                "",
                f"**Goal:** {phase_def.goal}",
                "",
            ]
        )

        if not phase_messages:
            lines.extend(["_No messages captured for this phase._", "", "---", ""])
            continue

        for idx, entry in enumerate(phase_messages, start=1):
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            timestamp = entry.get("timestamp", "")
            lines.append(f"### {idx}. {speaker}")
            lines.extend(_to_blockquote(text))
            if timestamp:
                lines.append("")
                lines.append(f"_Timestamp: {timestamp}_")
            lines.append("")

        lines.extend(["---", ""])

    if extras:
        lines.extend(["## Additional Messages", ""])
        for entry in extras:
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            timestamp = entry.get("timestamp", "")
            lines.append(f"### {speaker}")
            lines.extend(_to_blockquote(text))
            if timestamp:
                lines.append("")
                lines.append(f"_Timestamp: {timestamp}_")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def save_transcript(path: str | Path, markdown: str) -> None:
    Path(path).write_text(markdown, encoding="utf-8")
