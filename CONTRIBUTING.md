# Zu euer beitragen

Vielen Dank für dein Interesse an `euer`! `euer` ist ein freies Open-Source-Projekt (lizenziert unter der GNU AGPLv3 mit Plugin-Ausnahme).

## Das Contribution-Modell („Open Source, Closed Contribution“)

`euer` verfolgt ein Modell ähnlich dem von **SQLite** oder **Tailwind CSS**:
Die Software ist zu 100 % quelloffen, frei einsehbar, auditierbar und kostenlos nutzbar. Der Quellcode wird jedoch **ausschließlich von den Kern-Maintainern (Markus Keller)** geschrieben und direkt gepflegt.

### Warum dieses Modell?
1. **Lückenlose Rechtekette (100 % Clean IP):** Es wird sichergestellt, dass keine zersplitterten Urheberrechtsketten entstehen und das Projekt frei von Patent- oder Drittanbieter-Risiken bleibt.
2. **Rechtssicherheit für das Open-Core-Ökosystem:** `euer` dient als Core-Engine für optionale proprietäre Add-ons (wie `euer-datev` oder `euer-invoice`) und für automatisierte Kanzlei-Dienste. Externe Code-Beiträge ohne aufwendige CLAs würden unlösbare Lizenzkonflikte mit der AGPLv3 auslösen.
3. **Fokus & Architekturkonsistenz:** Der Charakter als leichtgewichtiges, auditierbares Werkzeug ohne externe Laufzeitabhängigkeiten bleibt dauerhaft gewahrt.

Aus diesem Grund werden **keine externen Code-Pull-Requests direkt in die Codebasis übernommen**.

---

## Wie du beitragen kannst

Community-Feedback ist für die Weiterentwicklung von `euer` essenziell und sehr willkommen! Du kannst das Projekt auf vielfältige Weise unterstützen:

1. **Fehler melden (Bug Reports):**
   - Prüfe in den [GitHub Issues](https://github.com/curiousmarkus/euer/issues), ob der Fehler bereits bekannt ist.
   - Beschreibe bei neuen Fehlern die verwendete Version (`euer doctor`), das Betriebssystem, den Reproduktionspfad sowie das erwartete und tatsächliche Verhalten.
2. **Feature-Wünsche & Architektur-Vorschläge:**
   - Diskutiere neue Ideen in den Issues oder schlage Konzepte vor.
   - Für nicht-triviale Funktionen können Spezifikationsentwürfe in [`specs/`](specs/) vorgeschlagen werden.
3. **Dokumentation & EÜR-Praxisfälle:**
   - Hinweise auf unklare Dokumentationen, fehlende Buchungsregeln oder steuerliche Edge-Cases in der EÜR sind besonders wertvoll.
4. **Fehlerbehebungen vorschlagen:**
   - Wenn du ein Problem analysiert hast, kannst du den Lösungsansatz oder ein reproduzierbares Minimalbeispiel gerne in einem Issue beschreiben. Die Umsetzung erfolgt dann durch das Core-Team.

---

## Entwicklungsumgebung & lokales Testen

Wenn du `euer` lokal forken, analysieren oder testen möchtest:

Benötigt wird Python 3.11 oder neuer. Unter macOS und Linux richtet `make install` eine virtuelle Umgebung einschließlich der Entwicklungs- und XLSX-Abhängigkeiten ein:

```bash
make install
make test
```

Unter Windows kann dieselbe Umgebung in PowerShell eingerichtet werden:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,xlsx]"
python -m unittest discover -s tests
```

Ohne Installation kann die CLI unter macOS und Linux über `python3 -m euercli <command>` aufgerufen werden. In einer aktivierten virtuellen Umgebung lautet der plattformübergreifende Aufruf `python -m euercli <command>`.

Architektur, Service-Layer-Regeln und Code-Konventionen sind im [`DEVELOPMENT.md`](DEVELOPMENT.md) dokumentiert.

---

## Wichtige Projektregeln (für Maintainer)

- Schreiboperationen auf `expenses`, `income` und `private_transfers` laufen immer über den Service Layer in `euercli/services/`.
- Nutzerseitige Ausgaben sind deutschsprachig; Bezeichner im Code sind englisch.
- Datenbankabfragen sind parametrisiert und jede Änderung wird im Audit-Log erfasst.
- Bei implementierten Specs wird ihr Status aktualisiert, ebenso die Spec-Tabelle in `DEVELOPMENT.md`.
- Die vollständigen verbindlichen Regeln und die Checkliste stehen in [`DEVELOPMENT.md`](DEVELOPMENT.md).
