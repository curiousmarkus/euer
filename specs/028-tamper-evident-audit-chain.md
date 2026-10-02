# Spec 028: Integritätsschutz für SQLite: Session-Trigger & Tamper-Evident Hash-Chain

## Status

Offen

## Ziel

Das Datenmodell von `euer` basiert auf einer lokalen SQLite-Datenbank. Dies birgt zwei spezifische Risiken:
1. **Unbefugter direkter SQL-Zugriff:** Ein autonomer KI-Agent (oder ein externes Skript) könnte versuchen, Buchungen direkt via `sqlite3 euer.db "INSERT INTO expenses..."` einzufügen, anstatt die offizielle `euer`-CLI zu nutzen. Dadurch würden Validierungsregeln, Nummernkreise und Vorsteuerlogik umgangen.
2. **Nachträgliche unbemerkte Datenmanipulation:** Einzelne Tabellenzeilen könnten nachträglich editiert oder gelöscht werden, ohne dass die Historie dies belegt.

Spec 028 definiert eine zweistufige Schutzarchitektur (*Defense-in-Depth*):
- **Stufe 1 (Prävention):** SQLite-Trigger blockieren jeden direkten Schreibzugriff harter Hand, es sei denn, die Verbindung wurde von der `euer`-Engine mit einem temporären Session-Token initialisiert.
- **Stufe 2 (Detektion & Integrität):** Das `audit_log` wird zu einer kryptografischen SHA-256-Hash-Kette (*Tamper-Evident Chain*) ausgebaut. Sollte Stufe 1 umgangen werden, bricht die Kette und der **DATEV-Export verweigert den Dienst**.

---

## Schutz- & Produktgrenze (Kein GoBD-Anspruch)

* **Zweck:** Schutz vor eigenmächtigen Agenten-Befehlen und mathematischer Nachweis der Unverfälschtheit (*Tamper-Evidence*) innerhalb der lokalen SQLite-Datenbank.
* **Kein GoBD-Ersatz:** Die Maßnahmen beanspruchen **keine formelle GoBD-Revisionssicherheit**. Eine lokale Datei kann auf Betriebssystemebene samt Backups physisch gelöscht werden. Die Schutzarchitektur garantiert jedoch: *Weder ein KI-Agent noch ein Nutzer kann im laufenden Betrieb unbemerkt an der Validierung vorbei buchen oder Buchungen rückwirkend manipulieren, ohne dass die Integritätsprüfung fehlschlägt.*

---

## Stufe 1: Prävention via Session-Token-Trigger

### Konzept: Die temporäre Autorisierungs-Tabelle (`temp._euer_session`)
In SQLite ist die Hilfsdatenbank `temp` isoliert pro Verbindung. Fremde Prozesse (wie ein Ad-hoc-Aufruf von `sqlite3 euer.db`) haben keinen Zugriff auf den Speicher einer anderen Verbindung.

Wir nutzen dieses Verhalten als Berechtigungs-Schranke:

### 1. Initialisierung im Service-Layer (`euercli.db`)
Sobald die offizielle `euer`-CLI eine Verbindung zur SQLite-Datenbank aufbaut, wird unmittelbar folgendes SQL ausgeführt:

```python
def get_db_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    # Session-Autorisierung für euer-Engine aktivieren:
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS _euer_session (authorized INTEGER NOT NULL);")
    conn.execute("DELETE FROM temp._euer_session;")
    conn.execute("INSERT INTO temp._euer_session (authorized) VALUES (1);")
    return conn
```

### 2. Schutz-Trigger im Schema (`schema.py`)
Für alle schreibbaren Tabellen (`expenses`, `income`, `private_transfers`, `categories`, `audit_log`) werden Trigger für `INSERT`, `UPDATE` und `DELETE` angelegt:

```sql
CREATE TRIGGER IF NOT EXISTS trg_prevent_direct_insert_expenses
BEFORE INSERT ON expenses
WHEN (SELECT count(*) FROM temp._euer_session WHERE authorized = 1) = 0
BEGIN
    SELECT RAISE(ABORT, 'DIREKTER SQL-ZUGRIFF VERBOTEN: Buchungen dürfen ausschließlich über die euer-CLI erfolgen!');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_direct_update_expenses
BEFORE UPDATE ON expenses
WHEN (SELECT count(*) FROM temp._euer_session WHERE authorized = 1) = 0
BEGIN
    SELECT RAISE(ABORT, 'DIREKTER SQL-ZUGRIFF VERBOTEN: Änderungen dürfen ausschließlich über die euer-CLI erfolgen!');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_direct_delete_expenses
BEFORE DELETE ON expenses
WHEN (SELECT count(*) FROM temp._euer_session WHERE authorized = 1) = 0
BEGIN
    SELECT RAISE(ABORT, 'DIREKTER SQL-ZUGRIFF VERBOTEN: Löschungen dürfen ausschließlich über die euer-CLI erfolgen!');
END;
```

*(Identische Trigger werden für `income`, `private_transfers` und `categories` hinterlegt).*

### 3. Auswirkung auf Agenten
Versucht ein KI-Agent im Terminal den Befehl:
```bash
sqlite3 euer.db "INSERT INTO expenses (vendor, amount_eur) VALUES ('Test', 50);"
```
wird die Ausführung sofort mit `RuntimeError: DIREKTER SQL-ZUGRIFF VERBOTEN...` abgebrochen. Der Agent wird gezwungen, `euer add expense ...` aufzurufen.

---

## Stufe 2: Detektion via Tamper-Evident Hash-Chain

Sollte ein Entwickler die Trigger mit `DROP TRIGGER` entfernen oder Daten auf Byte-Ebene manipulieren, greift die kryptografische Hash-Kette im `audit_log`.

### Schema-Erweiterung (`audit_log`)

```sql
ALTER TABLE audit_log ADD COLUMN prev_hash TEXT;
ALTER TABLE audit_log ADD COLUMN entry_hash TEXT;
```

Im Ziel-Schema (`schema.py`):

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    table_name TEXT NOT NULL,
    record_id INTEGER NOT NULL,
    record_uuid TEXT,
    action TEXT NOT NULL CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'MIGRATE')),
    old_data TEXT,
    new_data TEXT,
    user TEXT NOT NULL DEFAULT 'default',
    prev_hash TEXT,
    entry_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_entry_hash ON audit_log(entry_hash);
```

### Hash-Berechnung & Kanonisierung

Für den allerersten Eintrag der Datenbank (`id = 1`):
`GENESIS_HASH = "0" * 64` (64 Nullen).

Für jeden Eintrag `n > 1` entspricht `prev_hash` exakt dem `entry_hash` des Eintrags `n - 1`.

#### Kanonischer Payload:
```python
canonical_repr = "|".join([
    prev_hash or GENESIS_HASH,
    str(timestamp),
    str(table_name),
    str(record_id),
    str(record_uuid or ""),
    str(action),
    canonical_json(old_data),
    canonical_json(new_data),
    str(user),
])
entry_hash = hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()
```

---

## Stufe 3: Verifizierung & Export-Sperre

### 1. Neuer CLI-Befehl: `euer audit verify`
```bash
euer audit verify
```
* Prüft lückenlos aufsteigend nach `id ASC`:
  1. Zeile 1 hat `prev_hash == GENESIS_HASH`.
  2. Alle Zeilen: Neuberechneter Hash stimmt exakt mit `entry_hash` überein.
  3. Zeile `i > 1`: `prev_hash == entry_hash[i-1]`.
* **Erfolg:** Exit-Code 0.
* **Integritätsverletzung:** Exit-Code 1 mit Nennung der ersten manipulierten Zeilen-ID.

### 2. Zwingende Export-Schranke (`euer export` und `euer-datev`)
Bevor offizielle Exporte (CSV, XLSX, EÜR-HTML-Bericht oder DATEV-Buchungsstapel) erzeugt werden, führt das System automatisch eine interne Integritätsprüfung durch.
* Bei intakter Kette: Export wird erzeugt.
* Bei gebrochener Kette: Export bricht hart ab:  
  `FEHLER: Export verweigert. Die Datenbankintegrität ist verletzt (Audit-Kette inkonsistent). DATEV-Export zum Schutz der Kanzlei gesperrt.`

---

## Migration bestehender Installationen

1. Migration `010_audit_hash_chain.py` legt die Trigger an und ergänzt `prev_hash` und `entry_hash`.
2. Für bestehende Altdaten wird die Hash-Kette deterministisch nachberechnet (Backfill).
3. Ein abschließender Audit-Eintrag vom Typ `MIGRATE` schließt die Kette für künftige Buchungen.
