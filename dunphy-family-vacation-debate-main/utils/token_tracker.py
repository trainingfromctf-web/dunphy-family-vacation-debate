from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict

AGENTS = ["Phil", "Claire", "Haley", "Alex", "Luke", "Manny"]

PRICING_PER_MILLION = {
    "anthropic": {"input": 0.80, "output": 4.00},
    "gemini": {"input": 0.075, "output": 0.30},
    "ollama": {"input": 0.0, "output": 0.0},
    "mock": {"input": 0.0, "output": 0.0},
}


@dataclass
class UsageTotals:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class TokenTracker:
    def __init__(self, backend: str, on_update: Callable[[dict], None] | None = None):
        self.backend = backend.lower()
        self.on_update = on_update
        self._agent_totals: Dict[str, UsageTotals] = {agent: UsageTotals() for agent in AGENTS}
        self._agent_rounds: Dict[str, Dict[int, UsageTotals]] = defaultdict(dict)

    def add_usage(self, agent: str, round_number: int, input_tokens: int, output_tokens: int) -> None:
        if agent not in self._agent_totals:
            self._agent_totals[agent] = UsageTotals()

        totals = self._agent_totals[agent]
        totals.prompt_tokens += max(0, int(input_tokens))
        totals.completion_tokens += max(0, int(output_tokens))

        round_totals = self._agent_rounds[agent].get(round_number)
        if round_totals is None:
            round_totals = UsageTotals()
            self._agent_rounds[agent][round_number] = round_totals

        round_totals.prompt_tokens += max(0, int(input_tokens))
        round_totals.completion_tokens += max(0, int(output_tokens))

        if self.on_update:
            self.on_update(self.get_metrics_state())

    def get_metrics_state(self) -> dict:
        agent_payload = {}
        total_prompt = 0
        total_completion = 0

        for agent in AGENTS:
            totals = self._agent_totals.get(agent, UsageTotals())
            total_prompt += totals.prompt_tokens
            total_completion += totals.completion_tokens

            per_round = {}
            for round_number, round_totals in sorted(self._agent_rounds.get(agent, {}).items()):
                per_round[round_number] = {
                    "prompt_tokens": round_totals.prompt_tokens,
                    "completion_tokens": round_totals.completion_tokens,
                    "total_tokens": round_totals.total_tokens,
                    "cost_usd": self._calculate_cost(round_totals.prompt_tokens, round_totals.completion_tokens),
                    "cost_display": self._format_cost(
                        self._calculate_cost(round_totals.prompt_tokens, round_totals.completion_tokens)
                    ),
                }

            cost = self._calculate_cost(totals.prompt_tokens, totals.completion_tokens)
            agent_payload[agent] = {
                "prompt_tokens": totals.prompt_tokens,
                "completion_tokens": totals.completion_tokens,
                "total_tokens": totals.total_tokens,
                "cost_usd": cost,
                "cost_display": self._format_cost(cost),
                "per_round": per_round,
            }

        grand_cost = self._calculate_cost(total_prompt, total_completion)

        return {
            "backend": self.backend,
            "agents": agent_payload,
            "summary": {
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "total_tokens": total_prompt + total_completion,
                "cost_usd": grand_cost,
                "cost_display": self._format_cost(grand_cost),
            },
        }

    def reset(self) -> None:
        self._agent_totals = {agent: UsageTotals() for agent in AGENTS}
        self._agent_rounds = defaultdict(dict)
        if self.on_update:
            self.on_update(self.get_metrics_state())

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        rates = PRICING_PER_MILLION[self.backend]
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        return input_cost + output_cost

    def _format_cost(self, value: float) -> str:
        if self.backend in {"ollama", "mock"}:
            return "$0.000000 (local)"
        return f"${value:.6f}"
