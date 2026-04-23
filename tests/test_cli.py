from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any

import chebi_cli.cli as cli


@dataclass
class DummyClient:
    payload: dict[str, Any] | None = None

    def __enter__(self) -> DummyClient:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _run(argv: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = cli.main(argv)
    return rc, out.getvalue(), err.getvalue()


def test_bare_invocation_prints_help() -> None:
    rc, out, err = _run([])
    assert rc == 0
    assert "usage:" in out
    assert err == ""


def test_top_level_help() -> None:
    rc, out, _ = _run(["--help"])
    assert rc == 0
    assert "advanced-search" in out
    assert "compound" in out
    assert "calc" in out
    assert "sparql" in out
    assert "workflow" in out


def test_docs_urls_text(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    rc, out, err = _run(["docs", "urls"])
    assert rc == 0
    assert "docs:" in out
    assert err == ""


def test_docs_coverage_json(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    rc, out, _ = _run(["docs", "coverage", "--format", "json"])
    assert rc == 0
    assert "wrapped_endpoints" in out


def test_sparql_queries_lists_presets(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    monkeypatch.setattr(
        cli,
        "list_sparql_queries",
        lambda: {"count": 1, "items": [{"name": "predicates", "description": "List predicates"}]},
    )
    rc, out, err = _run(["sparql", "queries"])
    assert rc == 0
    assert "predicates: List predicates" in out
    assert err == ""


def test_sparql_query_renders_boolean_text(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    monkeypatch.setattr(
        cli,
        "sparql_query",
        lambda *_args, **_kwargs: {"kind": "ask", "boolean": True, "body": "true"},
    )
    rc, out, err = _run(["sparql", "query", "ASK { ?s ?p ?o }"])
    assert rc == 0
    assert out.strip() == "true"
    assert err == ""


def test_parser_invalid_page(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    rc, _, err = _run(["search", "es", "acetone", "--page", "0"])
    assert rc == 2
    assert "--page must be >= 1" in err


def test_compounds_requires_ids(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    rc, _, err = _run(["compounds", "get"])
    assert rc == 2
    assert "Provide IDs" in err


def test_compound_get_success(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    monkeypatch.setattr(
        cli, "get_compound", lambda *_args, **_kwargs: {"chebi_accession": "CHEBI:1"}
    )
    rc, out, err = _run(["compound", "get", "CHEBI:1"])
    assert rc == 0
    assert "CHEBI:1" in out
    assert err == ""


def test_calc_avg_mass_success(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    monkeypatch.setattr(cli, "calc_avg_mass", lambda *_args, **_kwargs: "18.015")
    rc, out, err = _run(["calc", "avg-mass", "--text", "O"])
    assert rc == 0
    assert "18.015" in out
    assert err == ""


def test_workflow_formula_profile_success(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    monkeypatch.setattr(
        cli,
        "workflow_formula_profile",
        lambda *_args, **_kwargs: {"formula": "C8H9NO2", "avg_mass": "151.16"},
    )
    rc, out, err = _run(["workflow", "formula-profile", "C8H9NO2", "--format", "json"])
    assert rc == 0
    assert "151.16" in out
    assert err == ""


def test_workflow_structure_profile_requires_input(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "load_app_config", lambda **_: object())
    monkeypatch.setattr(cli, "ChebiClient", lambda *_: DummyClient())
    rc, _, err = _run(["workflow", "structure-profile"])
    assert rc == 2
    assert "Missing required input text" in err
