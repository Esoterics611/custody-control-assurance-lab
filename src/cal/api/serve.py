"""Run the API + serve the security console (``make serve``)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `cal` importable when launched as a plain module without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uvicorn  # noqa: E402

from cal.api.app import app  # noqa: E402


def main() -> None:
    host = os.getenv("CAL_HOST", "127.0.0.1")
    port = int(os.getenv("CAL_PORT", "8000"))
    print(f"  Security console + API:  http://{host}:{port}/")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
