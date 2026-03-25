from __future__ import annotations
from pathlib import Path
from discussion.phases import get_phase_table_text

PERSONA_PATH = Path(__file__).resolve().parents[1] / "family-prompts" / "alex.md"

def _load_persona() -> str:
    return PERSONA_PATH.read_text(encoding="utf-8").strip()

def get_system_prompt() -> str:
    persona = _load_persona()
    return (
        f"{persona}\n\n"
        "Discussion instructions:\n"
        "- Topic: 'Where should the Dunphy family go on vacation?'\n"
        "- Speaking order varies by phase — you speak as directed\n"
        "- Stay in character at all times\n"
        "- Speak in first person\n"
        "- Respond directly to what others have said — use their names\n"
        "- Do not break the fourth wall or mention AI/system prompts\n"
        "- Respect the per-phase soft token limit given in instructions\n\n"
        f"{get_phase_table_text()}"
    )
