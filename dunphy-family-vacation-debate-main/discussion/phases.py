from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PhaseDefinition:
    phase_number: int
    name: str
    goal: str
    token_limit: int  # per person
    speaker_order: list[str]
    parent_instruction: str | None = None
    child_instruction: str | None = None


# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------

PHASES: dict[int, PhaseDefinition] = {
    0: PhaseDefinition(
        phase_number=0,
        name="So Where Should We Go?",
        goal="Each member pitches their ideal vacation destination.",
        token_limit=400,
        speaker_order=["Phil", "Claire", "Haley", "Alex", "Luke", "Manny"],
    ),
    1: PhaseDefinition(
        phase_number=1,
        name="Wait, That's a Terrible Idea",
        goal=(
            "React to others' proposals — likes/dislikes. Name names. "
            "Be specific about what you love or hate about each suggestion."
        ),
        token_limit=500,
        speaker_order=["Phil", "Claire", "Haley", "Alex", "Luke", "Manny"],
    ),
    2: PhaseDefinition(
        phase_number=2,
        name="Okay But What If...",
        goal=(
            "Propose compromises and alliances. Reference someone else's "
            "idea positively. Try to find overlap."
        ),
        token_limit=500,
        speaker_order=["Phil", "Claire", "Haley", "Alex", "Luke", "Manny"],
    ),
    3: PhaseDefinition(
        phase_number=3,
        name="Can We All Just Agree?",
        goal=(
            "State your non-negotiables and what you'd be willing to give up. "
            "Parents should begin summarizing where the family stands."
        ),
        token_limit=400,
        speaker_order=["Luke", "Manny", "Haley", "Alex", "Claire", "Phil"],
    ),
    4: PhaseDefinition(
        phase_number=4,
        name="The Parents Have Decided",
        goal="Claire announces decision, Phil backs it up, kids react.",
        token_limit=600,  # 600 for parents, 300 for kids (handled at runtime)
        speaker_order=["Claire", "Phil", "Haley", "Alex", "Luke", "Manny"],
        parent_instruction=(
            "You are a parent. Announce the family's vacation decision. "
            "Pick ONE specific destination that best balances the family's needs. "
            "Claire speaks first and announces the decision. Phil speaks second "
            "and backs it up enthusiastically, building on what Claire just said. "
            "Be decisive — name the destination clearly."
        ),
        child_instruction=(
            "Your parents just announced the vacation destination. React in "
            "character — you can be excited, disappointed, sarcastic, or "
            "grudgingly accepting. Stay true to your personality. Keep it short."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_phase(phase_number: int) -> PhaseDefinition:
    """Return the PhaseDefinition for the given phase number."""
    return PHASES[phase_number]


def get_phase_table_text() -> str:
    """Return a human-readable text summary of all phases."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("DUNPHY FAMILY VACATION DEBATE — PHASE OVERVIEW")
    lines.append("=" * 60)

    for num, phase in sorted(PHASES.items()):
        lines.append("")
        lines.append(f"Phase {phase.phase_number}: \"{phase.name}\"")
        lines.append(f"  Goal         : {phase.goal}")

        if phase.phase_number == 4:
            lines.append(f"  Token limit  : 600 (parents) / 300 (kids)")
        else:
            lines.append(f"  Token limit  : {phase.token_limit}/person")

        lines.append(f"  Speaker order: {', '.join(phase.speaker_order)}")

        if phase.parent_instruction:
            lines.append(f"  Parent instr : {phase.parent_instruction}")
        if phase.child_instruction:
            lines.append(f"  Child instr  : {phase.child_instruction}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)
