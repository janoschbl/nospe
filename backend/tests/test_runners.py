from __future__ import annotations

from unittest.mock import patch

from app.main import app
from run_backend import main


def test_backend_runner_disables_tty_logging_for_headless_sidecar():
    with patch("run_backend.uvicorn.run") as run:
        main()

    assert run.call_args.args[0] is app
    assert run.call_args.kwargs["log_config"] is None
