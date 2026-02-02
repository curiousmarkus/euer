# Approach: Incomplete Bookings (No Staging Table)

This note describes the simplified approach for “incomplete” handling without a
dedicated staging table.

## Goals

- Allow imports even when non-critical data is missing.
- Keep a clear list of bookings that still need enrichment.
- Avoid separate `incomplete_entries` storage.

## High-Level Flow

1. `euer import` reads CSV/JSONL rows and normalizes them.
2. It enforces **hard required fields**: `type`, `date`, `party`, `amount_eur`.
   - Missing any of these → import aborts.
3. Valid rows are inserted directly into `expenses` / `income`.
4. `euer incomplete list` scans **existing bookings** and computes missing
   **quality fields** (see below).

## Required vs. Quality Fields

### Hard required (import/add must have)
- `type` (or inferred from amount sign)
- `date`
- `party` (vendor/source)
- `amount_eur`

### Quality required (can be missing, shown by `incomplete list`)
- `category`
- `receipt`
- `vat` (only in `standard` mode)
- `account` (expenses only)

Receipt exception:
- `Gezahlte USt` (EÜR line 58) does **not** require a receipt.

## Incomplete List Logic

`euer incomplete list` is a **live query** over `expenses` / `income`.

- For expenses:
  - missing `category` → `category`
  - missing `receipt_name` → `receipt` (except `Gezahlte USt`)
  - missing `account` → `account`
  - in `standard`:
    - RC → `vat` if `vat_input` or `vat_output` is missing
    - normal → `vat` if `vat_input` is missing
- For income:
  - missing `category` → `category`
  - missing `receipt_name` → `receipt`
  - in `standard`: missing `vat_output` → `vat`

## Schema Notes

- `category_id` is nullable in `expenses` / `income`.
- No `incomplete_entries` table is used.

## User Workflow

1. Import or add bookings with the known basics.
2. Run `euer incomplete list`.
3. Complete missing data using `euer update expense|income <ID>`.

## Tests (Focus)

- Import fails when required fields are missing.
- `incomplete list` detects missing category/receipt/vat/account.
