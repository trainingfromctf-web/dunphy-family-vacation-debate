from __future__ import annotations

from dotenv import load_dotenv

from terminal_app import parse_args, run_terminal


if __name__ == "__main__":
    load_dotenv()
    args = parse_args()
    run_terminal(model=args.model, mode=args.mode)
