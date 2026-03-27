from __future__ import annotations

from chebi_cli.docs import ENDPOINTS, coverage_summary


def test_coverage_includes_all_documented_entries() -> None:
    summary = coverage_summary()
    wrapped = summary["wrapped_endpoints"]
    assert isinstance(wrapped, list)
    assert len(wrapped) == len(ENDPOINTS)
    assert "POST /public/advanced_search/" in wrapped
    assert "POST /public/structure-calculations/depict-indigo/" in wrapped
