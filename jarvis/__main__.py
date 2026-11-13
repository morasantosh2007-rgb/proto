"""Entry point for JARVIS: Just A Rather Very Intelligent System."""

import argparse
import sys
from jarvis.core.loop import JarvisLoop
from jarvis.integrations.setup_wizard import run_setup_wizard
from jarvis.diagnostics import run_doctor


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="JARVIS: Production-quality voice-controlled personal AI assistant.",
    )
    parser.add_argument(
        "subcommand",
        nargs="?",
        choices=["setup", "doctor", "run"],
        default="run",
        help="Subcommands: 'setup' (run integrations wizard), 'doctor' (run system diagnostics), or 'run' (start assistant).",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Run in interactive text mode instead of voice/microphone.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions without invoking side-effects on the OS or accounts.",
    )

    args = parser.parse_args()

    if args.subcommand == "setup":
        run_setup_wizard()
        return

    if args.subcommand == "doctor":
        success = run_doctor()
        sys.exit(0 if success else 1)

    # Start main assistant loop
    loop = JarvisLoop(text_mode=args.text, dry_run=args.dry_run)
    try:
        loop.start()
    except KeyboardInterrupt:
        print("\nJARVIS shutting down gracefully.")
        loop.stop()


if __name__ == "__main__":
    main()
