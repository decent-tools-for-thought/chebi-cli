# chebi-cli

Complete production-grade Python CLI wrapper for the public ChEBI 2.0 backend API.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

CLI command entry points:
- `chebi`
- `chebi-cli`

## Upstream API

- API docs: `https://www.ebi.ac.uk/chebi/backend/api/docs/`
- OpenAPI schema: `https://www.ebi.ac.uk/chebi/backend/api/schema/`
- Base URL default: `https://www.ebi.ac.uk/chebi/backend/api`

## Authentication and Config

Most public ChEBI endpoints are usable without auth. The tool still supports optional auth for parity.

Supported sources:
- CLI flags: `--user`, `--password`, `--session-id`, `--base-url`, `--timeout`, `--config`
- Environment variables: `CHEBI_USER`, `CHEBI_PASSWORD`, `CHEBI_SESSION_ID`, `CHEBI_BASE_URL`, `CHEBI_TIMEOUT`, `CHEBI_CONFIG`
- XDG config file: `${XDG_CONFIG_HOME:-~/.config}/chebi-cli/config.json`

Precedence (highest to lowest):
1. CLI flags
2. Environment variables
3. Config file
4. Built-in defaults

Example config file:

```json
{
  "base_url": "https://www.ebi.ac.uk/chebi/backend/api",
  "timeout": 30,
  "auth": {
    "user": "optional-user",
    "password": "optional-password",
    "session_id": "optional-sessionid"
  }
}
```

## Command Surface (full API coverage)

All endpoint paths and methods in the upstream public OpenAPI surface are wrapped.

### Advanced search
- `chebi advanced-search run --json '{...}' [--three-star-only/--no-three-star-only] [--has-structure/--no-has-structure] [--page N --size N --all-pages --max-pages N] [--download/--no-download] [--format json|jsonl|text|raw]`
- `chebi advanced-search sources-list`

### Compound endpoints
- `chebi compound get <CHEBI_ID> [--only-ontology-parents] [--only-ontology-children]`
- `chebi compound structure <ID> [--width N --height N] [--output FILE]`
- `chebi compounds get --id CHEBI:1 [--id CHEBI:2 ...]` (or `--ids-csv`, `--ids-file`)
- `chebi compounds post --id CHEBI:1 ...` (or `--ids-csv`, `--ids-file`)

### Search endpoints
- `chebi search es <TERM> [--page N --size N --all-pages --max-pages N]`
- `chebi search structure-get --smiles '<SMILES>' --search-type connectivity|similarity|substructure [--similarity F] [--three-star-only/--no-three-star-only] [--download/--no-download] [--page/--size/--all-pages]`
- `chebi search structure-post --structure '<SMILES_OR_MOL>' --search-type ... [--similarity F] [--three-star-only/--no-three-star-only] [--download/--no-download] [--page/--size/--all-pages]`

### Ontology endpoints
- `chebi ontology parents <CHEBI_ID>`
- `chebi ontology children <CHEBI_ID>`
- `chebi ontology all-children-get --relation <REL> --entity <CHEBI_ID> [common search/pagination flags]`
- `chebi ontology all-children-post --relation <REL> --entity <CHEBI_ID> [common search/pagination flags]`

### Structure and molfile endpoints
- `chebi structure get <STRUCTURE_ID> [--width N --height N] [--output FILE]`
- `chebi structure molfile <COMPOUND_ID> [--output FILE]`

### Structure-calculation endpoints
- `chebi calc avg-mass --text '<SMILES_OR_MOL>'`
- `chebi calc avg-mass-from-formula --text '<FORMULA>'`
- `chebi calc depict-indigo --text '<SMILES_OR_MOL>' --output out.png [--width N --height N --transbg/--no-transbg]`
- `chebi calc mol-formula --text '<SMILES_OR_MOL>'`
- `chebi calc monoisotopic-mass --text '<SMILES_OR_MOL>'`
- `chebi calc monoisotopic-mass-from-formula --text '<FORMULA>'`
- `chebi calc net-charge --text '<SMILES_OR_MOL>'`

### Docs/spec utilities
- `chebi docs urls`
- `chebi docs coverage`
- `chebi docs schema`

### Higher-order workflows
- `chebi workflow resolve-term <TERM> [--include-parents] [--include-children] [--include-structure-svg]`
  - Runs text search, resolves best match, retrieves compound details, and optionally pulls ontology and SVG in one call.
- `chebi workflow formula-profile <FORMULA>`
  - Computes average and monoisotopic mass from formula and runs advanced formula search.
- `chebi workflow structure-profile --structure '<SMILES_OR_MOL>' [--similarity 0.8] [--three-star-only/--no-three-star-only]`
  - Computes formula/masses/charge and performs both similarity and connectivity structure searches.

### Direct operation escape hatch
- `chebi request --method GET|POST --path /public/... [--param key=value ...] [--json ... | --json-file ... | --text ... | --text-file ...]`

The `request` command is additive convenience and does not replace explicit endpoint wrappers.

## Output Modes

Supported output modes by command:
- `json`: stable machine-readable output
- `jsonl`: one-object-per-line for list/result-heavy commands
- `text`: concise human-readable summaries
- `raw`: minimal transformation (useful for plain text payloads)

Field filtering is available on JSON-like responses via repeatable `--field`.

## Quick Start

```bash
# Help
chebi --help

# Fetch one compound
chebi compound get CHEBI:15377 --format text

# Full-text search
chebi search es paracetamol --size 5 --format json

# Structure similarity search (GET variant)
chebi search structure-get --smiles 'CCO' --search-type similarity --similarity 0.8 --format json

# Advanced search from file
chebi advanced-search run --json-file spec.json --no-three-star-only --format json

# Compute monoisotopic mass from formula
chebi calc monoisotopic-mass-from-formula --text 'C8H9NO2'
```

## Development and Verification

```bash
pip install -e .[dev]
ruff check .
mypy src
pytest
```

## API Caveats

- Some endpoints return plain text or binary content (`depict-indigo`, molfile/SVG retrieval, structure calculations).
- Pagination traversal with `--all-pages` relies on a `next` field in upstream responses. If unavailable, traversal stops after the first page.
- `download` query flags are passed through exactly where upstream advertises them.

## Attribution

This project wraps the ChEBI 2.0 backend API provided by EMBL-EBI.

## Wrapped Scope Statement

This repository wraps all endpoint methods listed in the public OpenAPI document at:
`https://www.ebi.ac.uk/chebi/backend/api/schema/`

Current wrapped surface is also discoverable with:

```bash
chebi docs coverage --format json
```
