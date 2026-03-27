<div align="center">

# chebi-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/chebi-cli?sort=semver&color=0f766e)](https://github.com/decent-tools-for-thought/chebi-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-0ea5e9)
![License](https://img.shields.io/badge/license-MIT-14b8a6)

Command-line wrapper for the public ChEBI backend API, with compound, search, ontology, structure, and calculation workflows.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#0EA5E9}Install \space \color{#14B8A6}Tool$$

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
chebi --help
```

## Functionality
$$\color{#0EA5E9}Compound \space \color{#14B8A6}Lookup$$
- `chebi compound get|structure`: fetch one compound or a rendered structure image.
- `chebi compounds get|post`: resolve compound batches from IDs supplied on the command line or from files.

$$\color{#0EA5E9}Search \space \color{#14B8A6}Workflows$$
- `chebi advanced-search run|sources-list`: run advanced JSON-backed searches and inspect source vocabularies.
- `chebi search es`: full-text search over ChEBI records.
- `chebi search structure-get|structure-post`: similarity, connectivity, and substructure search over chemical structures.

$$\color{#0EA5E9}Ontology \space \color{#14B8A6}Browse$$
- `chebi ontology parents|children`: inspect direct ontology neighbors.
- `chebi ontology all-children-get|all-children-post`: traverse descendant relationships with paging controls.

$$\color{#0EA5E9}Structure \space \color{#14B8A6}Math$$
- `chebi structure get|molfile`: fetch stored structure resources.
- `chebi calc avg-mass|monoisotopic-mass|mol-formula|net-charge`: compute derived chemistry values.
- `chebi calc depict-indigo`: render structures to an output file.

$$\color{#0EA5E9}Docs \space \color{#14B8A6}Access$$
- `chebi docs urls|coverage|schema`: inspect upstream URLs, wrapped coverage, and the live schema.
- `chebi request --method ... --path ...`: direct request escape hatch for unsupported calls.
- `chebi workflow resolve-term|formula-profile|structure-profile`: higher-order helper commands built from the wrapped endpoints.

## Configuration
$$\color{#0EA5E9}Save \space \color{#14B8A6}Defaults$$

Most public ChEBI endpoints work without authentication, but the CLI supports optional auth for parity.

Configuration precedence:

1. CLI flags: `--user`, `--password`, `--session-id`, `--base-url`, `--timeout`, `--config`
2. Environment: `CHEBI_USER`, `CHEBI_PASSWORD`, `CHEBI_SESSION_ID`, `CHEBI_BASE_URL`, `CHEBI_TIMEOUT`, `CHEBI_CONFIG`
3. Config file: `${XDG_CONFIG_HOME:-~/.config}/chebi-cli/config.json`
4. Built-in defaults

Example:

```json
{
  "base_url": "https://www.ebi.ac.uk/chebi/backend/api",
  "timeout": 30
}
```

Output modes:

- `json`
- `jsonl`
- `text`
- `raw`

## Quick Start
$$\color{#0EA5E9}Try \space \color{#14B8A6}Lookup$$

```bash
chebi compound get CHEBI:15377 --format text
chebi search es paracetamol --size 5 --format json
chebi search structure-get --smiles 'CCO' --search-type similarity --similarity 0.8 --format json
chebi ontology parents CHEBI:15377
chebi calc monoisotopic-mass-from-formula --text 'C8H9NO2'
chebi docs coverage --format json
```

## Credits

This client is built for the ChEBI backend API and is not affiliated with EMBL-EBI or ChEBI.

Credit goes to EMBL-EBI and the ChEBI project for the chemical ontology, backend API, and documentation this tool depends on.
