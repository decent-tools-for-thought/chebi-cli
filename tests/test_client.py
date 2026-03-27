from __future__ import annotations

import httpx
import pytest

from chebi_cli.client import ApiError, ChebiClient, ResponseParseError
from chebi_cli.config import AppConfig, AuthConfig


def _config() -> AppConfig:
    return AppConfig(base_url="https://example.org", timeout=5.0, auth=AuthConfig())


def test_get_json_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ChebiClient(_config())

    def fake_request(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(client._http, "request", fake_request)
    payload = client.get_json("/public/foo")
    assert payload == {"ok": True}
    client.close()


def test_get_json_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ChebiClient(_config())

    def fake_request(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return httpx.Response(404, text="missing")

    monkeypatch.setattr(client._http, "request", fake_request)
    with pytest.raises(ApiError):
        client.get_json("/public/foo")
    client.close()


def test_get_json_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = ChebiClient(_config())

    def fake_request(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return httpx.Response(200, text="not-json")

    monkeypatch.setattr(client._http, "request", fake_request)
    with pytest.raises(ResponseParseError):
        client.get_json("/public/foo")
    client.close()
