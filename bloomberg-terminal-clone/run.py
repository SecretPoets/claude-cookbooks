"""Launcher for the Bloomberg terminal clone.

Loads .env (if present), then starts uvicorn on 127.0.0.1:8000.
Run from the project root:

    cd bloomberg-terminal-clone
    python run.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    here = Path(__file__).resolve().parent
    # Make `backend` importable when launched from anywhere.
    sys.path.insert(0, str(here))

    try:
        from dotenv import load_dotenv

        env_path = here / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Fall back to repo root .env
            root_env = here.parent / ".env"
            if root_env.exists():
                load_dotenv(root_env)
    except ImportError:
        pass

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "WARNING: ANTHROPIC_API_KEY is not set. The market panels will work, "
            "but the TERM-AI chat endpoint will return an error until you set it.",
            file=sys.stderr,
        )

    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"TERM-AI starting on http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
