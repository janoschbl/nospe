from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import security  # noqa: E402
from app.main import app  # noqa: E402

TEST_SECRET = "test-secret-0123456789abcdef"
TEST_PORT = 8765


@pytest.fixture(autouse=True)
def _api_security():
    security.configure(secret=TEST_SECRET, port=TEST_PORT, dev=False)
    yield


def make_client(**kwargs) -> TestClient:
    """TestClient mit gültigem Host und Secret, wie ihn die echte UI sendet."""
    headers = {security.TOKEN_HEADER_CANONICAL: TEST_SECRET, **kwargs.pop("headers", {})}
    return TestClient(app, base_url=f"http://127.0.0.1:{TEST_PORT}", headers=headers, **kwargs)
