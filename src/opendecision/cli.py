from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import uvicorn

from opendecision import __version__


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opendecision",
        description="Run the OpenDecision API server.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="Start the API server.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument(
        "--model",
        help="Hugging Face model name or local model path.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.model:
        os.environ["OPENDECISION_MODEL"] = args.model

    uvicorn.run(
        "opendecision.api.app:app",
        host=args.host,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
