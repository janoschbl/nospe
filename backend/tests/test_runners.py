from __future__ import annotations

from unittest.mock import MagicMock, patch

import run_backend
from app import security
from app.main import app


def _run_main(monkeypatch, tmp_path, **env):
    for key in ("NOSPE_HANDSHAKE_FILE", "NOSPE_API_SECRET", "NOSPE_API_PORT", "NOSPE_DEV"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    server = MagicMock()
    with (
        patch("run_backend.uvicorn.Server", return_value=server) as server_cls,
        patch("run_backend.uvicorn.Config") as config_cls,
    ):
        run_backend.main()
    return server, server_cls, config_cls


def test_backend_runner_disables_tty_logging_for_headless_sidecar(monkeypatch, tmp_path):
    server, _server_cls, config_cls = _run_main(monkeypatch, tmp_path, NOSPE_API_PORT="0")

    assert config_cls.call_args.args[0] is app
    assert config_cls.call_args.kwargs["log_config"] is None
    sockets = server.run.call_args.kwargs["sockets"]
    sockets[0].close()


def test_handshake_publishes_random_port_and_secret(monkeypatch, tmp_path):
    handshake = tmp_path / "handshake.txt"
    server, _cls, _config = _run_main(monkeypatch, tmp_path, NOSPE_HANDSHAKE_FILE=str(handshake))

    sock = server.run.call_args.kwargs["sockets"][0]
    try:
        port_line, secret_line = handshake.read_text().splitlines()
        assert int(port_line) == sock.getsockname()[1] != 8765
        assert sock.getsockname()[0] == "127.0.0.1"
        assert len(secret_line) >= 32
        config = security.get_config()
        assert (config.port, config.secret) == (int(port_line), secret_line)
    finally:
        sock.close()


def test_secret_from_environment_is_used(monkeypatch, tmp_path):
    server, _cls, _config = _run_main(
        monkeypatch, tmp_path, NOSPE_API_PORT="0", NOSPE_API_SECRET="x" * 24
    )
    server.run.call_args.kwargs["sockets"][0].close()
    assert security.get_config().secret == "x" * 24
