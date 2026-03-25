from __future__ import annotations

import asyncio
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part


class LLMClientError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    backend: str
    gemini_model: str = "gemini-2.5-flash"
    timeout_seconds: float = 60.0


class LLMClient:
    def __init__(self, backend: str):
        backend_normalized = backend.strip().lower()
        if backend_normalized not in {"gemini", "mock"}:
            raise LLMClientError(
                f"Unsupported backend: {backend}. This build supports only Gemini (and mock for local testing)."
            )

        self.config = LLMConfig(backend=backend_normalized)
        self._session_service = InMemorySessionService()
        self._app_name = "family_vacation_debate"
        self._user_id = "discussion_runtime"

        if self.config.backend == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                raise LLMClientError("Gemini API key missing. Set GEMINI_API_KEY in .env.")
            # Force ADK/GenAI to use this key; keep GEMINI_API_KEY so future starts in the
            # same process still pass initialization checks.
            os.environ["GOOGLE_API_KEY"] = api_key

    def validate_connection(self) -> None:
        """Raises LLMClientError if backend is unavailable or credentials are invalid."""
        if self.config.backend == "mock":
            return

        try:
            self.chat(
                system_prompt="You are a readiness checker.",
                messages=[{"role": "user", "content": "Reply exactly: Ready."}],
                max_tokens=10,
            )
        except Exception as exc:  # pragma: no cover
            raise LLMClientError(
                "Gemini is not available. Verify GEMINI_API_KEY and network access."
            ) from exc

    def chat(self, system_prompt: str, messages: List[Dict[str, str]], max_tokens: int) -> Dict[str, Any]:
        if self.config.backend == "mock":
            return self._chat_mock(system_prompt, messages, max_tokens)

        async def _run() -> Dict[str, Any]:
            return await self._chat_async(system_prompt, messages, max_tokens)

        try:
            return asyncio.run(asyncio.wait_for(_run(), timeout=self.config.timeout_seconds))
        except RuntimeError as exc:
            if "asyncio.run() cannot be called from a running event loop" not in str(exc):
                raise
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    asyncio.wait_for(_run(), timeout=self.config.timeout_seconds)
                )
            finally:
                loop.close()

    async def _chat_async(
        self, system_prompt: str, messages: List[Dict[str, str]], max_tokens: int
    ) -> Dict[str, Any]:
        agent = LlmAgent(
            name="debate_runtime_agent",
            model=self.config.gemini_model,
            instruction=system_prompt,
        )
        runner = Runner(
            agent=agent,
            app_name=self._app_name,
            session_service=self._session_service,
        )

        session_id = f"session-{uuid.uuid4().hex}"
        await self._session_service.create_session(
            app_name=self._app_name,
            user_id=self._user_id,
            session_id=session_id,
        )

        prompt_lines = ["Conversation history:"]
        for message in messages:
            role = message.get("role", "user")
            prompt_lines.append(f"[{role}] {message.get('content', '')}")
        prompt_lines.append(f"\nRespond in no more than {max_tokens} tokens.")

        new_message = Content(role="user", parts=[Part(text="\n".join(prompt_lines))])

        final_text = ""
        input_tokens = 0
        output_tokens = 0

        async for event in runner.run_async(
            user_id=self._user_id,
            session_id=session_id,
            new_message=new_message,
        ):
            usage = self._extract_usage(event)
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]

            if event.is_final_response() and getattr(event, "content", None):
                parts = getattr(event.content, "parts", None) or []
                text_chunks = []
                for part in parts:
                    text = getattr(part, "text", None)
                    if text:
                        text_chunks.append(text)
                if text_chunks:
                    final_text = "".join(text_chunks).strip()

        return {
            "text": final_text,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
        }

    def _chat_mock(self, system_prompt: str, messages: List[Dict[str, str]], max_tokens: int) -> Dict[str, Any]:
        latest = messages[-1]["content"] if messages else ""
        if "Respond only with: 'Ready.'" in latest or "Reply exactly: Ready." in latest:
            text = "Ready."
        else:
            role = self._infer_role(system_prompt)
            round_match = re.search(r"Phase\s+(\d+)", latest)
            round_txt = round_match.group(1) if round_match else "?"
            text = (
                f"I am {role}. In phase {round_txt}, I have strong opinions about where we should go on vacation. "
                "I respond directly, stay in character, and engage with what the family has said."
            )

        in_tokens = max(1, len((system_prompt + "\n" + latest).split()))
        out_tokens = min(max_tokens, max(1, len(text.split())))

        return {
            "text": text,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
        }

    @staticmethod
    def _infer_role(system_prompt: str) -> str:
        lower = system_prompt.lower()
        if "phil dunphy" in lower:
            return "Phil"
        if "claire dunphy" in lower:
            return "Claire"
        if "haley dunphy" in lower:
            return "Haley"
        if "alex dunphy" in lower:
            return "Alex"
        if "luke dunphy" in lower:
            return "Luke"
        if "manny delgado" in lower:
            return "Manny"
        return "Family Member"

    @staticmethod
    def _extract_usage(event: Any) -> Dict[str, int]:
        candidates = [
            getattr(event, "usage_metadata", None),
            getattr(getattr(event, "model_response", None), "usage_metadata", None),
            getattr(getattr(event, "llm_response", None), "usage_metadata", None),
        ]

        for usage in candidates:
            if usage is None:
                continue
            prompt = getattr(usage, "prompt_token_count", None)
            output = getattr(usage, "candidates_token_count", None)
            if prompt is None and isinstance(usage, dict):
                prompt = usage.get("prompt_token_count", 0)
                output = usage.get("candidates_token_count", 0)
            return {
                "input_tokens": int(prompt or 0),
                "output_tokens": int(output or 0),
            }

        return {"input_tokens": 0, "output_tokens": 0}
