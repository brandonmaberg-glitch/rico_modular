"""Launch the RICO FastAPI web server."""

from __future__ import annotations

import uvicorn


def main() -> None:
    url = "http://127.0.0.1:8000/"
    print(f"Starting RICO web UI at {url}")
    uvicorn.run("server.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
