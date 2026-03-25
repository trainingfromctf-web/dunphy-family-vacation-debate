from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Callable, Dict, List, Optional

from agents import phil, claire, haley, alex, luke, manny
from discussion.phases import PHASES, PhaseDefinition, get_phase
from utils.llm_client import LLMClient, LLMClientError
from utils.token_tracker import TokenTracker

TOPIC = "Where should the Dunphy family go on vacation?"

AGENT_ORDER = ["Phil", "Claire", "Haley", "Alex", "Luke", "Manny"]
ALL_AGENTS = AGENT_ORDER  # No moderator

SYSTEM_PROMPTS = {
    "Phil": phil.get_system_prompt,
    "Claire": claire.get_system_prompt,
    "Haley": haley.get_system_prompt,
    "Alex": alex.get_system_prompt,
    "Luke": luke.get_system_prompt,
    "Manny": manny.get_system_prompt,
}


class FamilyDiscussionOrchestrator:
    def __init__(self):
        self.current_phase = 0
        self.mode = "ai_led"
        self.model = "Anthropic"

        self.is_active = False
        self.is_paused = False
        self.is_complete = False

        self.history: List[dict] = []
        self.client: LLMClient | None = None
        self.token_tracker: TokenTracker | None = None

        self.on_message: Callable[[str, str], None] | None = None
        self.on_phase_change: Callable[[int], None] | None = None
        self.on_discussion_complete: Callable[[], None] | None = None
        self.on_metrics_update: Callable[[dict], None] | None = None
        self.on_error: Callable[[str], None] | None = None
        self.on_failure_options: Callable[[str], None] | None = None

        self._state_lock = threading.Lock()
        self._turn_lock = threading.Lock()
        self._failure_event = threading.Event()
        self._failure_resolution: str | None = None
        self._pending_failure: Dict[str, str] | None = None
        self._session_id = uuid.uuid4().hex

    def start_discussion(self, model: str, mode: str) -> None:
        with self._state_lock:
            self._reset_state_locked()
            self.model = model
            self.mode = mode
            self.is_active = True
            self._session_id = uuid.uuid4().hex

        backend = self._model_to_backend(model)
        self.token_tracker = TokenTracker(backend=backend, on_update=self._emit_metrics_update)

        worker = threading.Thread(target=self._run_discussion_start, daemon=True)
        worker.start()

    def submit_user_message(self, text: str) -> None:
        if not text.strip() or not self.is_active or self.is_complete:
            return

        self._append_message("User", text.strip(), phase_number=self.current_phase)

        if self._is_next_phase_command(text):
            self.advance_phase()
            return

        if self.mode != "user_led":
            return

        current_session_id = self._session_id
        worker = threading.Thread(
            target=self._run_user_led_turn, args=(text.strip(), current_session_id), daemon=True
        )
        worker.start()

    def advance_phase(self) -> None:
        with self._state_lock:
            if not self.is_active or self.is_complete:
                return
            max_phase = max(PHASES.keys())
            if self.current_phase < max_phase:
                self.current_phase += 1
                self._emit_phase_change(self.current_phase)
            else:
                self._complete_discussion_locked()

    def retry_failed_agent(self) -> None:
        with self._state_lock:
            if not self._pending_failure:
                return
            self._failure_resolution = "retry"
            self._failure_event.set()

    def skip_failed_agent(self) -> None:
        with self._state_lock:
            if not self._pending_failure:
                return
            self._failure_resolution = "skip"
            self._failure_event.set()

    def reset_discussion(self) -> None:
        with self._state_lock:
            self._reset_state_locked()

        if self.token_tracker:
            self.token_tracker.reset()

    def get_history(self) -> List[dict]:
        return list(self.history)

    # ------------------------------------------------------------------
    # Internal: discussion lifecycle
    # ------------------------------------------------------------------

    def _run_discussion_start(self) -> None:
        try:
            try:
                self.client = LLMClient(self._model_to_backend(self.model))
                self.client.validate_connection()
            except LLMClientError as exc:
                self._emit_error(str(exc))
                with self._state_lock:
                    self._reset_state_locked()
                return

            ready = self._run_preflight_checks()
            if not ready:
                with self._state_lock:
                    self._reset_state_locked()
                return

            self.current_phase = 0
            self._emit_phase_change(0)

            if self.mode == "ai_led":
                worker = threading.Thread(target=self._run_ai_led_discussion, daemon=True)
                worker.start()
            else:
                self._append_message(
                    "System",
                    "User-Led mode is active. Enter your prompt to begin Phase 0.",
                    phase_number=self.current_phase,
                )
        except Exception as exc:  # pragma: no cover - safety net for thread failures
            self._emit_error(f"Discussion start failed unexpectedly: {exc}")
            with self._state_lock:
                self._reset_state_locked()

    def _run_preflight_checks(self) -> bool:
        if not self.client:
            return False

        for agent in ALL_AGENTS:
            system_prompt = SYSTEM_PROMPTS[agent]()
            ready_prompt = (
                f"You are {agent}. You understand your role in this family discussion. "
                "Respond only with: 'Ready.'"
            )
            try:
                response = self.client.chat(
                    system_prompt=system_prompt,
                    messages=[{"role": "user", "content": ready_prompt}],
                    max_tokens=20,
                )
            except Exception as exc:  # pragma: no cover - runtime API behavior
                self._emit_error(f"Pre-flight check failed for {agent}: {exc}")
                return False

            if "ready" not in response.get("text", "").strip().lower():
                self._emit_error(f"Pre-flight check failed for {agent}: unexpected readiness response.")
                return False

        return True

    def _run_ai_led_discussion(self) -> None:
        session_id = self._session_id
        try:
            # Opening scene
            self._append_message(
                "System",
                "The Dunphy family sits around the kitchen table to decide their vacation destination...",
                phase_number=0,
            )

            for phase_num in sorted(PHASES.keys()):
                phase_def = PHASES[phase_num]
                if not self._is_session_current(session_id) or not self.is_active or self.is_complete:
                    return

                self.current_phase = phase_def.phase_number
                self._emit_phase_change(phase_def.phase_number)

                # Phase intro system message
                self._append_message(
                    "System",
                    f"Phase {phase_def.phase_number}: \"{phase_def.name}\" \u2014 {phase_def.goal}",
                    phase_number=phase_def.phase_number,
                )

                for agent in phase_def.speaker_order:
                    success = self._run_agent_turn(agent, phase_def, session_id=session_id)
                    if not success:
                        return

            # Closing
            self._append_message(
                "System",
                "The Dunphys have made their decision!",
                phase_number=4,
            )

            with self._state_lock:
                if self._is_session_current(session_id):
                    self._complete_discussion_locked()
        except Exception as exc:  # pragma: no cover - safety net for thread failures
            self._emit_error(f"Discussion failed unexpectedly: {exc}")
            with self._state_lock:
                self._reset_state_locked()

    def _run_user_led_turn(self, user_text: str, session_id: str) -> None:
        if not self._is_session_current(session_id):
            return

        with self._turn_lock:
            if not self._is_session_current(session_id):
                return
            phase_def = get_phase(self.current_phase)
            for agent in phase_def.speaker_order:
                success = self._run_agent_turn(
                    agent, phase_def, user_trigger=user_text, session_id=session_id
                )
                if not success:
                    return

    # ------------------------------------------------------------------
    # Internal: agent turn execution
    # ------------------------------------------------------------------

    def _run_agent_turn(
        self,
        agent_name: str,
        phase_def: PhaseDefinition,
        user_trigger: str | None = None,
        session_id: str | None = None,
    ) -> bool:
        if not self.client:
            return False

        if user_trigger:
            instruction = (
                f"Current phase: {phase_def.phase_number} - {phase_def.name}. "
                f"Phase goal: {phase_def.goal} "
                f"Respond directly to the latest message: {user_trigger}\n"
                "Output only your own speech for this turn. "
                "Do NOT include transcript tags like [user]/[assistant] and do NOT write other speakers' lines.\n"
                f"Stay in character. Respond in no more than {phase_def.token_limit} tokens."
            )
        else:
            if phase_def.phase_number == 4:
                if agent_name in ("Claire", "Phil"):
                    instruction = (
                        f"Phase {phase_def.phase_number}: {phase_def.name}. "
                        f"{phase_def.parent_instruction} "
                        "Output only your own speech. Do NOT write other speakers' lines. "
                        f"Respond in no more than 600 tokens."
                    )
                else:
                    instruction = (
                        f"Phase {phase_def.phase_number}: {phase_def.name}. "
                        f"{phase_def.child_instruction} "
                        "Output only your own speech. Do NOT write other speakers' lines. "
                        f"Respond in no more than 300 tokens."
                    )
            else:
                instruction = (
                    f"Phase {phase_def.phase_number}: {phase_def.name}. "
                    f"Goal: {phase_def.goal} "
                    "Output only your own speech for this turn. "
                    "Do NOT include transcript tags like [user]/[assistant] and do NOT write other speakers' lines. "
                    f"Respond in no more than {phase_def.token_limit} tokens."
                )

        max_tokens = phase_def.token_limit
        if phase_def.phase_number == 4:
            max_tokens = 600 if agent_name in ("Claire", "Phil") else 300

        result = self._invoke_with_recovery(
            agent_name=agent_name,
            phase_def=phase_def,
            instruction=instruction,
            max_tokens=max_tokens,
            track_metrics=True,
            session_id=session_id or self._session_id,
        )
        if result is None:
            return False
        if result.get("skipped"):
            return True

        bounded_text = self._hard_cap_text_tokens(result.get("text", ""), max_tokens)
        bounded_text = self._sanitize_agent_output(agent_name, bounded_text)
        self._append_message(agent_name, bounded_text, phase_number=phase_def.phase_number)
        return True

    # ------------------------------------------------------------------
    # Internal: recovery / retry logic
    # ------------------------------------------------------------------

    def _invoke_with_recovery(
        self,
        agent_name: str,
        phase_def: PhaseDefinition,
        instruction: str,
        max_tokens: int,
        track_metrics: bool,
        session_id: str,
    ) -> Optional[dict]:
        first_error: Exception | None = None

        for attempt in (1, 2):
            if not self._is_session_current(session_id):
                return None
            try:
                result = self._invoke_agent(
                    agent_name=agent_name,
                    phase_number=phase_def.phase_number,
                    instruction=instruction,
                    max_tokens=max_tokens,
                    track_metrics=track_metrics,
                    session_id=session_id,
                )
                return result
            except Exception as exc:  # pragma: no cover - runtime API behavior
                if str(exc) == "Stale discussion session":
                    return None
                if attempt == 1:
                    first_error = exc
                    self._emit_error(f"{agent_name} attempt 1 failed: {exc}")
                    self._append_message(
                        "System",
                        f"\u26a0 {agent_name} failed to respond. Retrying...",
                        phase_number=phase_def.phase_number,
                    )
                else:
                    self._emit_error(f"{agent_name} attempt 2 failed: {exc}")
                    self._append_message(
                        "System",
                        f"\u26a0 {agent_name} failed again. Choose Retry Failed or Skip Failed to continue.",
                        phase_number=phase_def.phase_number,
                    )

        return self._wait_for_manual_recovery(
            agent_name=agent_name,
            phase_def=phase_def,
            instruction=instruction,
            max_tokens=max_tokens,
            track_metrics=track_metrics,
            prior_error=first_error,
            session_id=session_id,
        )

    def _wait_for_manual_recovery(
        self,
        agent_name: str,
        phase_def: PhaseDefinition,
        instruction: str,
        max_tokens: int,
        track_metrics: bool,
        prior_error: Exception | None,
        session_id: str,
    ) -> Optional[dict]:
        if not self._is_session_current(session_id):
            return None

        with self._state_lock:
            self.is_paused = True
            self._pending_failure = {"agent": agent_name}
            self._failure_resolution = None
            self._failure_event.clear()

        if self.on_failure_options:
            self.on_failure_options(agent_name)

        # Keep the worker responsive even when user never clicks a recovery action.
        while self._is_session_current(session_id):
            if self._failure_event.wait(timeout=0.5):
                break
        if not self._is_session_current(session_id):
            return None

        with self._state_lock:
            decision = self._failure_resolution
            self._pending_failure = None
            self._failure_resolution = None
            self.is_paused = False

        if decision == "retry":
            try:
                return self._invoke_agent(
                    agent_name=agent_name,
                    phase_number=phase_def.phase_number,
                    instruction=instruction,
                    max_tokens=max_tokens,
                    track_metrics=track_metrics,
                    session_id=session_id,
                )
            except Exception as exc:  # pragma: no cover
                self._append_message(
                    "System",
                    f"\u26a0 {agent_name} retry failed. Skipping this turn.",
                    phase_number=phase_def.phase_number,
                )
                self._emit_error(f"{agent_name} failed after manual retry: {exc}")
                return None

        self._append_message(
            "System",
            f"Skipped {agent_name}'s turn for Phase {phase_def.phase_number}.",
            phase_number=phase_def.phase_number,
        )
        if prior_error:
            self._emit_error(f"{agent_name} error: {prior_error}")
        return {"text": "", "skipped": True}

    # ------------------------------------------------------------------
    # Internal: LLM invocation
    # ------------------------------------------------------------------

    def _invoke_agent(
        self,
        agent_name: str,
        phase_number: int,
        instruction: str,
        max_tokens: int,
        track_metrics: bool,
        session_id: str,
    ) -> dict:
        if not self.client:
            raise RuntimeError("LLM client is not initialized")
        if not self._is_session_current(session_id):
            raise RuntimeError("Stale discussion session")

        system_prompt = SYSTEM_PROMPTS[agent_name]()
        messages = self._build_messages_for_agent(agent_name, instruction)
        result = self.client.chat(system_prompt=system_prompt, messages=messages, max_tokens=max_tokens)
        if not self._is_session_current(session_id):
            raise RuntimeError("Stale discussion session")

        if track_metrics and self.token_tracker:
            self.token_tracker.add_usage(
                agent=agent_name,
                round_number=phase_number,
                input_tokens=int(result.get("input_tokens", 0)),
                output_tokens=int(result.get("output_tokens", 0)),
            )

        return result

    def _build_messages_for_agent(self, target_agent: str, latest_instruction: str) -> List[dict]:
        messages: List[dict] = []
        for entry in self.history:
            speaker = entry.get("speaker", "")
            text = entry.get("text", "")
            role = "assistant" if speaker == target_agent else "user"
            messages.append({"role": role, "content": f"{speaker}: {text}"})

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Discussion topic: {TOPIC}\n"
                    f"Current phase: {self.current_phase}\n"
                    f"Instruction: {latest_instruction}"
                ),
            }
        )
        return messages

    # ------------------------------------------------------------------
    # Internal: message & state helpers
    # ------------------------------------------------------------------

    def _append_message(self, speaker: str, text: str, phase_number: int) -> None:
        message = {
            "speaker": speaker,
            "text": text,
            "phase_number": phase_number,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self.history.append(message)
        if self.on_message:
            self.on_message(speaker, text)

    def _complete_discussion_locked(self) -> None:
        self.is_active = False
        self.is_complete = True
        self.is_paused = False
        if self.on_discussion_complete:
            self.on_discussion_complete()

    def _reset_state_locked(self) -> None:
        self._session_id = uuid.uuid4().hex
        self.current_phase = 0
        self.history = []
        self.is_active = False
        self.is_paused = False
        self.is_complete = False
        self._pending_failure = None
        self._failure_resolution = None
        self._failure_event.set()

    def _emit_phase_change(self, phase_number: int) -> None:
        if self.on_phase_change:
            self.on_phase_change(phase_number)

    def _emit_metrics_update(self, metrics: dict) -> None:
        if self.on_metrics_update:
            self.on_metrics_update(metrics)

    def _emit_error(self, text: str) -> None:
        if self.on_error:
            self.on_error(text)

    @staticmethod
    def _is_next_phase_command(text: str) -> bool:
        normalized = text.strip().lower()
        return normalized in {"/next", "next phase", "/next phase", "advance phase"}

    @staticmethod
    def _model_to_backend(model: str) -> str:
        normalized = model.strip().lower()
        mapping = {
            "gemini": "gemini",
            "mock": "mock",
        }
        if normalized not in mapping:
            raise ValueError(f"Unknown model: {model}. Use 'gemini' or 'mock'.")
        return mapping[normalized]

    def _is_session_current(self, session_id: str) -> bool:
        return self._session_id == session_id

    @staticmethod
    def _hard_cap_text_tokens(text: str, max_tokens: int) -> str:
        """
        Hard cap for displayed/stored response length.
        Uses whitespace-token approximation to enforce an upper bound regardless of model behavior.
        """
        words = text.split()
        if len(words) <= max_tokens:
            return text
        return " ".join(words[:max_tokens]).strip()

    @staticmethod
    def _sanitize_agent_output(agent_name: str, text: str) -> str:
        """
        Remove leaked transcript continuation markers from model output.
        """
        cleaned = text.strip()
        if not cleaned:
            return cleaned

        # Remove self-prefix if model emits "Name: ..." instead of direct speech.
        self_prefix = f"{agent_name}:"
        if cleaned.startswith(self_prefix):
            cleaned = cleaned[len(self_prefix):].strip()

        # Cut off when output starts replaying transcript turns.
        cutoff_markers = [
            "\n[user]",
            "\n[assistant]",
            " [user]",
            " [assistant]",
            "\nPhil:",
            "\nClaire:",
            "\nHaley:",
            "\nAlex:",
            "\nLuke:",
            "\nManny:",
            "\nSystem:",
        ]
        lowest = len(cleaned)
        for marker in cutoff_markers:
            idx = cleaned.find(marker)
            if idx != -1:
                lowest = min(lowest, idx)

        cleaned = cleaned[:lowest].strip()
        return cleaned
