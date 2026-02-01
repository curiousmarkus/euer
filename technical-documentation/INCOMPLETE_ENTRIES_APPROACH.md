# Approach: Incomplete Entries (Bulk-Import)

This note explains how the new bulk-import + incomplete-entry handling was designed and implemented.

## Goals

- Allow AI-agents (or humans) to import bank statements even when data is partial.
- Store partial lines safely without losing context.
- Provide a dedicated command to list incomplete lines so they can be fixed later.
- Keep behavior consistent with existing CLI patterns (audit log, CSV outputs, etc.).

## High-Level Flow

1. `euer import` reads CSV/JSONL rows and normalizes them into a canonical shape.
2. It validates mandatory fields (`type`, `date`, `party`, `category`, `amount_eur`).
3. If a row is incomplete, it is stored in `incomplete_entries` with raw data and a list
   of missing fields.
4. If a row is complete, it is inserted into `expenses` or `income` as usual (with
   duplicate protection via hash).
5. `euer incomplete list` displays the incomplete entries for follow-up.

From a user perspective, there are two sources of “incomplete” work:

- **Bulk-import rows with missing required fields** → stored in `incomplete_entries`.
- **Standard `add` entries with missing optional details** (e.g., receipt or notes) →
  stored in `expenses`/`income` and completed later via `update`.

## Schema Additions

`incomplete_entries` captures partial data and the missing fields:

- `type`: expense/income/unknown (unknown when type is missing and cannot be inferred).
- `date`, `party`, `category_name`, `amount_eur`, `account`, `foreign_amount`,
  `receipt_name`, `notes`, `vat_amount`.
- `raw_data`: JSON snapshot of the original row.
- `missing_fields`: JSON list of required fields that were missing.

This keeps the original context so the entry can be fixed later without
re-reading the bank statement.

## Normalization & Inference

Import rows are normalized using a flexible field mapping:

- `type` accepts synonyms (expense/ausgabe, income/einnahme, etc.).
- `party` is mapped from `party`, `vendor`, `source`, or `counterparty`.
- `amount_eur` is parsed from multiple numeric formats.
- If `type` is missing but `amount_eur` is available:
  - negative amount → expense
  - positive amount → income

This allows AI-agent outputs and bank CSVs to be accepted without strict schemas.

## Validation Rules

Required fields for a “complete” entry:

- `type`
- `date`
- `party`
- `category`
- `amount_eur`

If a category name exists but does not resolve to a known category ID, it is
also considered “missing” so it routes to incomplete.

## Audit Log

Insertions into `incomplete_entries` are recorded in `audit_log` with action `INSERT`,
consistent with the rest of the system.

## CLI Commands

### Import

```
python3 euer.py import --file import.csv --format csv
```

- Inserts complete rows into `expenses` / `income`.
- Stores incomplete rows in `incomplete_entries`.
- Prints summary counts (total, inserted, duplicates, incomplete).

### Incomplete List

```
python3 euer.py incomplete list
python3 euer.py incomplete list --format csv
```

Shows missing fields (pretty-printed) to help operators fix entries quickly.

## User Workflow (Practical)

1. Capture everything you already know (even if partial).
2. Run `euer incomplete list` to see missing required fields.
3. Keep a clear list of open tasks (e.g., “download invoice X”).
4. Once the missing piece is available, **update the row** (or re-import the line)
   so the entry becomes complete.

## Tests

Tests focus on:

- Mixed complete + incomplete import sets.
- Correct counts and row routing.
- `incomplete list` output in CSV format.

## Follow-Ups (Optional)

Potential enhancements that were left out intentionally to keep scope minimal:

- A “repair” command to convert incomplete rows into full entries.
- UI/editor for fixing missing fields in-place.
- Optional auto-category fallback based on vendor/source heuristics.
