from __future__ import annotations

import json
from pathlib import Path

import pytest

from chebi_cli.config import ConfigError, load_app_config


def test_load_config_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "base_url": "https://file.example/api",
                "sparql_base_url": "https://file.example/sparql",
                "timeout": 11,
                "auth": {"user": "file-user", "password": "file-pass", "session_id": "file-sid"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CHEBI_BASE_URL", "https://env.example/api")
    monkeypatch.setenv("CHEBI_SPARQL_BASE_URL", "https://env.example/sparql")
    monkeypatch.setenv("CHEBI_TIMEOUT", "22")

    app = load_app_config(
        config_path=str(cfg),
        cli_base_url="https://cli.example/api",
        cli_sparql_base_url="https://cli.example/sparql",
        cli_timeout=33,
        cli_user="cli-user",
        cli_password="cli-pass",
        cli_session_id="cli-sid",
    )

    assert app.base_url == "https://cli.example/api"
    assert app.sparql_base_url == "https://cli.example/sparql"
    assert app.timeout == 33
    assert app.auth.user == "cli-user"
    assert app.auth.password == "cli-pass"
    assert app.auth.session_id == "cli-sid"


def test_invalid_timeout_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text('{"timeout": "nope"}', encoding="utf-8")

    with pytest.raises(ConfigError):
        load_app_config(
            config_path=str(cfg),
            cli_base_url=None,
            cli_sparql_base_url=None,
            cli_timeout=None,
            cli_user=None,
            cli_password=None,
            cli_session_id=None,
        )
