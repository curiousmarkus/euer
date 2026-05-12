# Spec 011: Reverse-Charge-Typ (EU vs. Drittland)

## Status

Implementiert

## Motivation

`euer` muss Reverse-Charge-Ausgaben für spätere UStVA-Auswertungen nach EU und
Drittland trennen können. Ein boolesches `is_rc` plus separate Jurisdiktion
erzeugt unnötige Kombinationszustände, z.B. `is_rc = 0` mit gesetzter
Jurisdiktion.

Da das Projekt noch Beta-Nutzer hat, wird das Datenmodell früh vereinfacht:
Reverse Charge wird als einzelnes persistiertes Picklist-Feld gespeichert.

## Fachliche Entscheidung

Die Tabelle `expenses` speichert den Reverse-Charge-Zustand in genau einer
Spalte:

```sql
rc_type TEXT NOT NULL DEFAULT 'none'
    CHECK(rc_type IN ('none', 'eu', 'third_country', 'unclassified'))
```

Bedeutung:

| Wert | Bedeutung |
|---|---|
| `none` | Keine Reverse-Charge-Ausgabe |
| `eu` | Reverse-Charge-Leistung aus dem übrigen Gemeinschaftsgebiet |
| `third_country` | Reverse-Charge-Leistung aus steuerlich nicht-EU |
| `unclassified` | Migrierte Altbuchung: RC bekannt, Jurisdiktion fehlt |

`unclassified` ist ausschließlich ein Legacy-/Migrationszustand. Neue
Erfassungen per CLI oder Import dürfen ihn nicht erzeugen.

## ELSTER-Bezug

| `rc_type` | Bedeutung | ELSTER |
|---|---|---|
| `eu` | Sonstige Leistung eines im übrigen Gemeinschaftsgebiet ansässigen Unternehmers | KZ 46 / 47 |
| `third_country` | Andere Leistung aus steuerlich nicht-EU | KZ 84 / 85 |

## Geltungsbereich

- Betrifft **nur `expenses`**
- Betrifft `add expense`, `update expense`, `import`, `list`, `export`,
  `summary`, `incomplete`
- Ist Voraussetzung für Spec 012 (`vat-report`)

`income` ist nicht betroffen.

## Anforderungen

### A1: Datenmodell

Neue Datenbanken enthalten `expenses.rc_type` wie oben definiert.

`is_rc` und `rc_jurisdiction` werden nicht mehr im Schema geführt. Ob eine
Buchung Reverse Charge ist, wird abgeleitet:

```text
rc_type != 'none'
```

`euer init` migriert bestehende Datenbanken:

- `is_rc = 0` → `rc_type = 'none'`
- `is_rc = 1` und `rc_jurisdiction = 'eu'` → `rc_type = 'eu'`
- `is_rc = 1` und `rc_jurisdiction = 'third_country'` →
  `rc_type = 'third_country'`
- `is_rc = 1` ohne Jurisdiktion → `rc_type = 'unclassified'`

### A2: Service-Modelle

`Expense` in `euercli/services/models.py` enthält `rc_type: str = "none"`.

Für Leselogik darf `Expense.is_rc` als abgeleitete Property existieren, schreibt
aber nicht in die Datenbank.

### A3: `add expense`

Die CLI bleibt:

```bash
euer add expense --rc eu
euer add expense --rc third-country
```

Regeln:

- `--rc` verlangt immer einen Wert.
- Erlaubte CLI-Werte: `eu`, `third-country`.
- Intern wird `third-country` als `third_country` gespeichert.
- Ohne `--rc` wird `rc_type = 'none'` gespeichert.
- `unclassified` darf nicht per `add expense` erzeugt werden.

### A4: `update expense`

```bash
euer update expense 42 --rc eu
euer update expense 42 --rc third-country
euer update expense 42 --no-rc
```

Regeln:

- `--rc` und `--no-rc` sind gegenseitig exklusiv.
- `--rc` setzt `rc_type` auf `eu` oder `third_country`.
- `--no-rc` setzt `rc_type = 'none'`.
- Ohne RC-Flag bleibt `rc_type` unverändert, auch bei `unclassified`.
- Altbuchungen mit `rc_type = 'unclassified'` können per `--rc ...`
  nachklassifiziert werden.

### A5: Service-Layer-Validierung

`create_expense()` und `update_expense()` verwenden `rc_type`.

Mindestregeln:

- Zulässige persistierte Werte: `none`, `eu`, `third_country`,
  `unclassified`.
- `create_expense()` akzeptiert nur `none`, `eu`, `third_country`.
- `update_expense()` akzeptiert explizit nur `none`, `eu`, `third_country`;
  `unclassified` bleibt nur erhalten, wenn RC nicht geändert wird.
- CLI und Import dürfen keine abweichenden Varianten direkt in die DB schreiben.

Empfohlene Fehlerfälle:

- `invalid_rc_type`
- `unclassified_rc_type_not_allowed`

### A6: Import

Der Import akzeptiert das Picklist-Feld `rc`.

Akzeptierte Import-Feldnamen:

- `rc`
- `rc_type`
- `is_rc`
- `RC`

Akzeptierte Werte:

- leer / `false` / `0` / `nein` → `none`
- `eu`
- `third-country`
- `third_country`

Für Kompatibilität mit älteren Exporten werden zusätzlich gelesen:

- `rc_jurisdiction`
- `rc-jurisdiction`
- `RC-Jurisdiktion`

Wenn ein Import noch `rc=true`/`X` plus Jurisdiktionsspalte nutzt, wird daraus
`rc_type` normalisiert. `rc=true` ohne Jurisdiktion bleibt ein zeilenbezogener
Importfehler.

### A7: List- und Export-Ausgabe

Die Ausgabe ist round-trip-fähig:

- `list expenses --format csv` enthält eine Spalte `RC`
- `export` für Ausgaben enthält eine Spalte `RC`
- CSV- und Export-Ausgaben verwenden nutzerfreundliche Werte:
  - leer für `none`
  - `eu`
  - `third-country`
  - `unclassified`

### A8: `summary` und `incomplete`

`summary` bleibt kein UVA-Report und führt keine KZ-Aufteilung ein.

Neu ist nur eine Warnung:

```text
Hinweis: 3 Reverse-Charge-Buchung(en) ohne EU-/Drittland-Typ.
  → Für die spätere USt-Voranmeldung bitte per `euer update expense <ID> --rc eu|third-country` nachpflegen.
```

`incomplete list` markiert Ausgaben mit `rc_type = 'unclassified'` als
unvollständig (`rc_type`).

## Nicht im Scope

- Automatische Erkennung der Jurisdiktion aus Anbietername, Land oder Domain
- Vollständige USt-Voranmeldungsausgabe
- Länder- oder Steuerrechts-Engine jenseits der Klassifikationen `eu` und
  `third_country`

## Verwandte Specs

- Spec 004: Steuerlogik (KU/Standard)
- Spec 012: `vat-report`
