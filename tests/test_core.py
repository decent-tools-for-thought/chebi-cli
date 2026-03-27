from __future__ import annotations

from typing import Any

import pytest

from chebi_cli.core import (
    format_jsonl,
    parse_id_list,
    parse_json_input,
    parse_text_input,
    render_text,
    select_fields,
    workflow_formula_profile,
)


def test_select_fields_dict() -> None:
    payload: dict[str, Any] = {"a": 1, "b": 2, "c": 3}
    assert select_fields(payload, ["a", "c"]) == {"a": 1, "c": 3}


def test_format_jsonl() -> None:
    out = format_jsonl([{"a": 1}, {"b": 2}])
    assert out.splitlines() == ['{"a": 1}', '{"b": 2}']


def test_parse_json_input_requires_one_source(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        parse_json_input(None, None)

    fp = tmp_path / "p.json"
    fp.write_text('{"x": 1}', encoding="utf-8")
    assert parse_json_input(None, str(fp)) == {"x": 1}


def test_parse_id_list_accepts_mixed_sources(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fp = tmp_path / "ids.txt"
    fp.write_text("CHEBI:1\nCHEBI:2\n", encoding="utf-8")
    out = parse_id_list(["CHEBI:3"], "CHEBI:4,CHEBI:5", str(fp))
    assert out == ["CHEBI:3", "CHEBI:4", "CHEBI:5", "CHEBI:1", "CHEBI:2"]


def test_parse_text_input(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fp = tmp_path / "smi.txt"
    fp.write_text("CCO", encoding="utf-8")
    assert parse_text_input(None, str(fp)) == "CCO"


def test_render_text_results() -> None:
    payload = {"results": [{"chebi_accession": "CHEBI:1", "name": "foo"}]}
    text = render_text(payload)
    assert "results: 1" in text
    assert "CHEBI:1" in text


def test_workflow_formula_profile_aggregates_calls(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "chebi_cli.core.advanced_search",
        lambda *_args, **_kwargs: {"results": [{"chebi_accession": "CHEBI:1"}]},
    )
    monkeypatch.setattr(
        "chebi_cli.core.calc_avg_mass_from_formula", lambda *_args, **_kwargs: "151.16"
    )
    monkeypatch.setattr(
        "chebi_cli.core.calc_monoisotopic_mass_from_formula",
        lambda *_args, **_kwargs: "151.0633",
    )
    payload = workflow_formula_profile(client=None, formula="C8H9NO2")  # type: ignore[arg-type]
    assert payload["formula"] == "C8H9NO2"
    assert payload["avg_mass"] == "151.16"
    assert payload["monoisotopic_mass"] == "151.0633"
