from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://www.ebi.ac.uk/chebi/backend/api"
DEFAULT_SPARQL_BASE_URL = "https://sparql.uniprot.org/sparql"
ENV_BASE_URL = "CHEBI_BASE_URL"
ENV_SPARQL_BASE_URL = "CHEBI_SPARQL_BASE_URL"
ENV_TIMEOUT = "CHEBI_TIMEOUT"
ENV_USER = "CHEBI_USER"
ENV_PASSWORD = "CHEBI_PASSWORD"
ENV_SESSION_ID = "CHEBI_SESSION_ID"
ENV_CONFIG_PATH = "CHEBI_CONFIG"


class ConfigError(ValueError):
    """Raised when config data is invalid."""


@dataclass(frozen=True)
class AuthConfig:
    user: str | None = None
    password: str | None = None
    session_id: str | None = None


@dataclass(frozen=True)
class AppConfig:
    base_url: str = DEFAULT_BASE_URL
    sparql_base_url: str = DEFAULT_SPARQL_BASE_URL
    timeout: float = 30.0
    auth: AuthConfig = AuthConfig()


def _xdg_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "chebi-cli" / "config.json"
    return Path.home() / ".config" / "chebi-cli" / "config.json"


def resolve_config_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path)
    return _xdg_config_path()


def load_file_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON config in {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ConfigError(f"Config root in {path} must be a JSON object")
    return parsed


def _as_float(value: Any, source: str) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid timeout from {source}: {value!r}") from exc
    if timeout <= 0:
        raise ConfigError(f"Timeout must be > 0 from {source}: {timeout!r}")
    return timeout


def merge_config(
    *,
    file_config: dict[str, Any],
    cli_base_url: str | None,
    cli_sparql_base_url: str | None,
    cli_timeout: float | None,
    cli_user: str | None,
    cli_password: str | None,
    cli_session_id: str | None,
) -> AppConfig:
    file_auth_raw = file_config.get("auth")
    file_auth: dict[str, Any] = file_auth_raw if isinstance(file_auth_raw, dict) else {}
    env_timeout = os.environ.get(ENV_TIMEOUT)

    base_url = (
        cli_base_url
        or os.environ.get(ENV_BASE_URL)
        or file_config.get("base_url")
        or DEFAULT_BASE_URL
    )
    if not isinstance(base_url, str) or not base_url.strip():
        raise ConfigError("Base URL must be a non-empty string")

    sparql_base_url = (
        cli_sparql_base_url
        or os.environ.get(ENV_SPARQL_BASE_URL)
        or file_config.get("sparql_base_url")
        or DEFAULT_SPARQL_BASE_URL
    )
    if not isinstance(sparql_base_url, str) or not sparql_base_url.strip():
        raise ConfigError("SPARQL base URL must be a non-empty string")

    if cli_timeout is not None:
        timeout = _as_float(cli_timeout, "--timeout")
    elif env_timeout is not None:
        timeout = _as_float(env_timeout, ENV_TIMEOUT)
    elif "timeout" in file_config:
        timeout = _as_float(file_config["timeout"], "config file")
    else:
        timeout = 30.0

    user = cli_user or os.environ.get(ENV_USER) or file_auth.get("user")
    password = cli_password or os.environ.get(ENV_PASSWORD) or file_auth.get("password")
    session_id = cli_session_id or os.environ.get(ENV_SESSION_ID) or file_auth.get("session_id")

    if user is not None and not isinstance(user, str):
        raise ConfigError("Auth user must be a string")
    if password is not None and not isinstance(password, str):
        raise ConfigError("Auth password must be a string")
    if session_id is not None and not isinstance(session_id, str):
        raise ConfigError("Session ID must be a string")

    return AppConfig(
        base_url=base_url.rstrip("/"),
        sparql_base_url=sparql_base_url.rstrip("/"),
        timeout=timeout,
        auth=AuthConfig(user=user, password=password, session_id=session_id),
    )


def load_app_config(
    *,
    config_path: str | None,
    cli_base_url: str | None,
    cli_sparql_base_url: str | None,
    cli_timeout: float | None,
    cli_user: str | None,
    cli_password: str | None,
    cli_session_id: str | None,
) -> AppConfig:
    path = resolve_config_path(config_path)
    file_cfg = load_file_config(path)
    return merge_config(
        file_config=file_cfg,
        cli_base_url=cli_base_url,
        cli_sparql_base_url=cli_sparql_base_url,
        cli_timeout=cli_timeout,
        cli_user=cli_user,
        cli_password=cli_password,
        cli_session_id=cli_session_id,
    )
