from __future__ import annotations

import argparse
import threading
import time
from datetime import datetime

from discussion.orchestrator import FamilyDiscussionOrchestrator


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def run_terminal(model: str, mode: str) -> None:
    orchestrator = FamilyDiscussionOrchestrator()
    done = threading.Event()

    def on_message(speaker: str, text: str) -> None:
        print(f"[{_timestamp()}] {speaker}: {text}\n")

    def on_phase_change(phase_number: int) -> None:
        print(f"[{_timestamp()}] --- Phase {phase_number} ---")

    def on_complete() -> None:
        print(f"[{_timestamp()}] Discussion complete.")
        done.set()

    def on_error(text: str) -> None:
        print(f"[{_timestamp()}] ERROR: {text}")

    def on_failure(_agent: str) -> None:
        print(f"[{_timestamp()}] A turn failed. Use /retry or /skip.")

    orchestrator.on_message = on_message
    orchestrator.on_phase_change = on_phase_change
    orchestrator.on_discussion_complete = on_complete
    orchestrator.on_error = on_error
    orchestrator.on_failure_options = on_failure

    print(f"[{_timestamp()}] Starting discussion with model={model}, mode={mode}")
    orchestrator.start_discussion(model=model, mode=mode)

    if mode == "ai_led":
        while not done.is_set():
            if orchestrator.is_paused:
                try:
                    cmd = input("Paused> /retry or /skip: ").strip().lower()
                except EOFError:
                    orchestrator.skip_failed_agent()
                    time.sleep(0.2)
                    continue
                if cmd == "/retry":
                    orchestrator.retry_failed_agent()
                elif cmd == "/skip":
                    orchestrator.skip_failed_agent()
                else:
                    print("Type /retry or /skip")
            elif not orchestrator.is_active:
                break
            else:
                time.sleep(0.2)
        return

    print("User-Led mode commands: /next, /retry, /skip, /quit")
    while not done.is_set():
        try:
            user_input = input("You> ").strip()
        except EOFError:
            break

        if not user_input:
            continue
        if user_input == "/quit":
            orchestrator.reset_discussion()
            break
        if user_input == "/next":
            orchestrator.advance_phase()
            continue
        if user_input == "/retry":
            orchestrator.retry_failed_agent()
            continue
        if user_input == "/skip":
            orchestrator.skip_failed_agent()
            continue

        orchestrator.submit_user_message(user_input)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dunphy Family Vacation Discussion (Terminal)")
    parser.add_argument(
        "--model",
        default="gemini",
        choices=["gemini", "mock"],
        help="Model backend",
    )
    parser.add_argument(
        "--mode",
        default="ai_led",
        choices=["ai_led", "user_led"],
        help="Discussion mode",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_terminal(model=args.model, mode=args.mode)
