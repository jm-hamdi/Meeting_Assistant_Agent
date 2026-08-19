"""CLI entry point and interactive REPL."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import NoReturn

from colorama import Fore, Style

from meet_assistant import __version__
from meet_assistant.agent import build_agent
from meet_assistant.logging import setup_logging
from meet_assistant.settings import settings

logger = logging.getLogger("meet_assistant.cli")

BANNER = f"""
{Fore.CYAN}{'━' * 58}{Style.RESET_ALL}
{Fore.CYAN}
  ███╗   ███╗███████╗███████╗████████╗
  ████╗ ████║██╔════╝██╔════╝╚══██╔══╝
  ██╔████╔██║█████╗  █████╗     ██║
  ██║╚██╔╝██║██╔══╝  ██╔══╝     ██║
  ██║ ╚═╝ ██║███████╗███████╗   ██║
  ╚═╝     ╚═╝╚══════╝╚══════╝   ╚═╝
  Assistant{Style.RESET_ALL}

{Fore.WHITE}  v{__version__} — Local AI meeting transcription & task creation{Style.RESET_ALL}
{Fore.WHITE}  Model   : {settings.lm_studio_model_id}{Style.RESET_ALL}
{Fore.WHITE}  Endpoint: {settings.lm_studio_base_url}{Style.RESET_ALL}
{Fore.WHITE}  Whisper : {settings.whisper_model_size} ({settings.whisper_device} / {settings.whisper_compute_type}){Style.RESET_ALL}
{Fore.CYAN}{'━' * 58}{Style.RESET_ALL}

{Fore.GREEN}  Commands:{Style.RESET_ALL}
  • Type any instruction: {Fore.YELLOW}"Record the standup and create tasks"{Style.RESET_ALL}
  • {Fore.CYAN}list{Style.RESET_ALL}   : Show past meeting sessions
  • {Fore.CYAN}exit{Style.RESET_ALL}   : Quit
"""


def repl(agent) -> NoReturn:
    """Run the interactive REPL."""
    print(BANNER)

    while True:
        try:
            user_input = input(f"\n{Fore.CYAN}Meet ❯ {Style.RESET_ALL}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
            sys.exit(0)

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in ("exit", "quit", "q"):
            print(f"{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
            sys.exit(0)

        if lower == "list":
            try:
                from meet_assistant.tools.storage import list_meetings
                print(list_meetings())
            except Exception as exc:
                print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}")
            continue

        print(f"{Fore.CYAN}⏳ Thinking…{Style.RESET_ALL}")
        try:
            result = agent.run(user_input)
            print(f"\n{Fore.CYAN}Assistant:{Style.RESET_ALL} {result}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⚠ Action interrupted.{Style.RESET_ALL}")
        except Exception as exc:
            logger.error("Execution error: %s", exc, exc_info=True)
            print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="meet",
        description="Meet Assistant — local AI transcription, summarization, and task creation.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Single command to run non-interactively (e.g. meet 'transcribe audio.wav')",
    )
    parser.add_argument(
        "--record",
        type=int,
        metavar="SECONDS",
        help="Record for N seconds then run the full pipeline (bypasses agent).",
    )
    parser.add_argument(
        "--transcribe",
        metavar="FILE",
        help="Transcribe an existing audio file (bypasses agent).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all past meeting sessions.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Override LLM model ID (default: {settings.lm_studio_model_id})",
    )
    parser.add_argument(
        "--whisper",
        default=None,
        metavar="SIZE",
        help=f"Override Whisper model size (default: {settings.whisper_model_size})",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help=f"Max agent steps (default: {settings.max_agent_steps})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG logging.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Meet Assistant v{__version__}",
    )

    args = parser.parse_args()

    if args.verbose:
        settings.verbosity = 2
    if args.whisper:
        settings.whisper_model_size = args.whisper

    setup_logging(settings.verbosity)

    # ── Direct flags (no agent needed) ────────────────────────────────────────
    if args.list:
        from meet_assistant.tools.storage import list_meetings
        print(list_meetings())
        return

    if args.transcribe:
        from meet_assistant.core.transcriber import Transcriber
        transcriber = Transcriber()
        result = transcriber.transcribe(args.transcribe)
        print(result)
        return

    if args.record:
        from meet_assistant.tools.meeting import run_full_pipeline
        print(run_full_pipeline(duration_seconds=args.record))
        return

    # ── Agent mode ────────────────────────────────────────────────────────────
    agent = build_agent(model_id=args.model, max_steps=args.steps)

    if args.prompt:
        try:
            result = agent.run(args.prompt)
            print(f"{Fore.CYAN}Assistant:{Style.RESET_ALL} {result}")
        except Exception as exc:
            logger.error("Error: %s", exc)
            print(f"{Fore.RED}Error: {exc}{Style.RESET_ALL}", file=sys.stderr)
            sys.exit(1)
    else:
        repl(agent)


if __name__ == "__main__":
    main()
