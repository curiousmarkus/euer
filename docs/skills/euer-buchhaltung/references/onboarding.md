# Onboarding: Buchhaltung einrichten oder gezielt vervollständigen

Diese Referenz ist die gemeinsame Interview-Anleitung für den lokalen Buchhaltungs-
Agenten und einen separaten LLM-Chat. Ziel sind ein persönliches Mandanten-Dossier,
eine dazu passende euer-Konfiguration und ein klarer nächster Arbeitsauftrag.

## 1. Vorhandenen Stand übernehmen

Bei lokalem Zugriff zuerst Arbeitsordner, vorhandenes Dossier, CLI-Verfügbarkeit,
Existenz der vorgesehenen Datenbank und vorhandene Config prüfen. `euer --version`
und `euer config show` helfen dabei. Die Config-Datei selbst enthält zusätzlich
private Konten und optionale Buchungskonten, die `config show` nicht vollständig zeigt.
Unter macOS/Linux liegt sie in `~/.config/euer/config.toml`, unter Windows in
`%APPDATA%\euer\config.toml`.

Eine vorhandene `AGENTS.md` kann Entwicklerregeln oder andere Anweisungen enthalten.
Erhalte diese Inhalte; ergänze ein klar abgegrenztes Mandanten-Dossier oder verlinke
ein separat vereinbartes Dossier. Fehlt nur die Datei, aber alle Angaben sind bereits
bekannt, erstelle sie daraus, statt das ganze Interview zu wiederholen.
Ein Skill- oder Tool-Update ersetzt eine vorhandene persönliche `AGENTS.md`
niemals automatisch. Lokale Skill-Kopien vor Austausch mit Upstream vergleichen.

| Ausgangslage | Vorgehen |
|---|---|
| Noch keine Einrichtung | Interview führen, Dossier und Setup vorbereiten |
| Dossier vorhanden, Config/DB fehlt | Bekannte Angaben übernehmen; fehlende technische Einrichtung erledigen |
| Config/DB vorhanden, Dossier fehlt | Vorhandene Einstellungen übernehmen; nur fehlenden Kontext erfragen |
| Dossier und Config widersprechen sich | Konkrete Abweichung nennen und maßgeblichen Wert klären, bevor betroffene Buchungen erfolgen |
| Alles vorhanden | Ohne Vollinterview zum eigentlichen Auftrag zurückkehren |
| Kein Terminal-/Dateizugriff | Interview führen und Dateien/Befehle ausgeben; keine lokale Prüfung oder Ausführung behaupten |

Ein Default wie `small_business`, das aktuelle Jahr oder eine Konto-Kennung ist
kein Nachweis, dass er für diesen Mandanten stimmt. Eine fehlende DB am Standardpfad
kann auch bedeuten, dass der Agent im falschen Ordner gestartet wurde.

## 2. Interview nach Bedarf

Erkläre kurz, welche Informationen fehlen. Frage einzeln oder in kleinen Gruppen
(höchstens drei zusammengehörige Fragen), warte auf Antworten und frage Bekanntes
nicht erneut. Passe die Tiefe an den Auftrag an: Eine einzelne fehlende Angabe
rechtfertigt kein vollständiges Interview. Unbekannte Antworten bleiben ausdrücklich
offen; optionale Lieferanten-Mappings oder SKR-Nummern blockieren keine erste Buchung.

### Mandant und Beginn

- Name für Dossier/Audit-Log, Geschäftsform und ob die Gewinnermittlung per EÜR
  für diesen Betrieb geklärt ist. Bei unklarer Eignung keine EÜR-Tauglichkeit zusagen.
- Buchhaltungsordner und Datenbankpfad, zu erfassender Zeitraum, bereits erfasste
  Bestände sowie gegebenenfalls Datenübernahme aus einem anderen System.

### Steuerlicher Kontext

- Bestätigter Umsatzsteuerstatus: `small_business` oder `standard`. Bei Unklarheit
  nach vorhandenen steuerlichen Unterlagen fragen; den Status nicht selbst wählen.
- Soweit relevant: Voranmeldungszeitraum, Soll-/Istbesteuerung, bekannte Fristen und
  wer die Prüfung/Übermittlung übernimmt. Diese Angaben stehen im Dossier; dafür
  gibt es keine entsprechenden euer-Setup-Felder oder automatische Terminüberwachung.
- Regelmäßige ausländische Dienstleister und bisher geklärte Behandlung. Einen
  Reverse-Charge-Typ nicht allein aus einem Markennamen ableiten; konkrete Rechnung
  und leistendes Unternehmen bleiben maßgeblich.
- Bekannte Sonderfälle für spätere Prüfung festhalten. `vat-report` wertet nach
  Zahlungsdatum aus und deckt nicht jede steuerliche Periodenzuordnung ab.

### Dateiablage und Lesen von Belegen

- Aus einem vorhandenen Belegpfad Root, Jahresordner und Typ-Unterordner ableiten,
  statt jeden Wert einzeln abzufragen. Vorschlag: `<root>/<Jahr>/Ausgaben` bzw.
  `Einnahmen`, Dateiname mit Rechnungsdatum und Anbieter.
- Ablage der Kontoauszüge und konkreten Exportordner festlegen.
  `receipts.year_dir` benötigt `{year}`; `exports.directory` unterstützt diesen
  Platzhalter nicht.
- Verfügbare PDF-Textextraktion/OCR prüfen. `markitdown` ist eine Möglichkeit;
  vorhandene geeignete Werkzeuge können weiter genutzt werden. Die euer-CLI liest
  selbst keine Rechnungs-PDFs aus.
- Für Bewirtungen gilt der Buchhaltungs-Skill: Vorsteuer ausschließlich vom Beleg
  übernehmen, Trinkgeld nicht doppelt zum Zahlbetrag addieren und offene Fälle
  sichtbar nachpflegen.

### Konten und private Vorgänge

- Geschäftliche Konten/Karten und Zahlungsdienstleister mit eindeutigen Kennungen
  erfassen, beispielsweise `g-geschaeftskonto`. Bankname und bei Bedarf letzte vier
  Ziffern genügen zur Unterscheidung; keine Zugangsdaten erfragen.
- Privat bezahlte Betriebsausgaben und dafür verwendete Kennungen erfassen,
  beispielsweise `p-giro`. Nur tatsächlich private Kennungen in `accounts.private`
  aufnehmen. Nach Ausgleichsüberweisungen fragen, um doppelte Kosten zu vermeiden.
- Bei gemischter Nutzung vereinbarte betriebliche Anteile und ihre Grundlage
  dokumentieren. Keine pauschalen Prozentsätze als bestätigte Regeln übernehmen.

### Wiederkehrende Fälle und Zusammenarbeit

- Typische Lieferanten und gewünschte Kategoriezuordnungen erfragen. Kategorien
  nach Initialisierung mit `euer list categories` prüfen; bei Bedarf ein Jahr mit
  `--year YYYY` angeben. Im Dossier nur fachliche Kategorie, Sitz/Land,
  Reverse-Charge-Typ und Besonderheit speichern, keine festen EÜR-Zeilennummern.
- Optional Installationsquelle und Updateweg dokumentieren, wenn für das Projekt
  nützlich; einen festen Binärpfad nur bei unzuverlässigem PATH festhalten.
- Optional Buchungskonten (`[[ledger_accounts]]`) mit Schlüssel, Name, Kategorie
  und gegebenenfalls SKR-Nummer vereinbaren.
- Rhythmus für Kontoauszüge und Monatsabgleich, Ablage offener Fragen und
  Sicherungsziel festhalten. Monatliche Erinnerungen oder Bankabrufe werden dadurch
  nicht automatisch eingerichtet.

## 3. Dossier und technische Änderungen vorbereiten

Fasse die ermittelten Werte und konkrete Änderungen zusammen. Nutze bereits
bestätigte Angaben; frage nur bei neuen Annahmen, Widersprüchen oder noch offenen
Entscheidungen nach. Das Dossier muss mindestens den Mandanten, Arbeits-/DB-Pfad,
bestätigten Steuermodus und die für den Auftrag benötigten Ablage-/Kontenregeln
eindeutig beschreiben. Offene Punkte erhalten einen Status und nächsten Schritt.

Mögliche Gliederung der persönlichen `AGENTS.md` (an den Fall anpassen):

```markdown
# Mandanten-Dossier

## Mandant und Arbeitsbereich
Name, Geschäftsform, geklärte EÜR-Nutzung, Arbeitsordner, DB-Pfad,
Beginn und bereits erfasste Zeiträume.

## Steuerlicher Kontext
Bestätigter Steuermodus; soweit relevant Besteuerungsart, Voranmeldungszeitraum,
Zuständigkeit für Abgabe, geklärte RC-Fälle und offene steuerliche Fragen.

## Dateiablage und Werkzeuge
Beleg-Root, Jahresformat, Typ-Unterordner, Dateinamen-Regel,
Kontoauszüge, Exportordner, PDF-/OCR-Werkzeug.

## Konten und private Vorgänge
Geschäftliche und private Kennungen; privat bezahlte Ausgaben,
Ausgleichsüberweisungen, gemischte Nutzung mit vereinbarten Anteilen.

## Wiederkehrende Zuordnungen
Lieferant zu Kategorie; optionale Buchungskonten.

## Zusammenarbeit und offene Punkte
Monatsabgleich, bereitgestellte Zeiträume, Sicherung, Rückfragen mit nächstem Schritt.
```

Ersetze die beschreibenden Zeilen durch tatsächliche Angaben. Ein ausführliches
Duplikat der CLI-Anleitung gehört nicht ins Dossier: Die Buchungsregeln liefert
weiterhin `SKILL.md`. Bewahre bereits vorhandene individuelle Regeln.

## 4. Einrichtung anwenden

Bei einem lokalen Einrichtungsauftrag die vereinbarten Dateien und Einstellungen
anlegen bzw. gezielt ergänzen. Existierende Datenbanken nicht ersetzen und bestehende
Buchungen nicht automatisch reklassifizieren. Vor Änderungen an einem bestehenden
Bestand eine konsistente Sicherung vorsehen. Die Config gilt über Arbeitsordner
hinweg: Bei einem weiteren Mandanten erst die gemeinsame Config-Nutzung klären.

- Falls die CLI fehlt, passend zur Umgebung installieren bzw. den nötigen
  Installationsschritt benennen. Ein reiner Interviewauftrag umfasst keine Installation.
- `euer --db "/vereinbarter/pfad/euer.db" init` initialisiert die ausgewählte DB;
  bei vorhandenen DBs kann es Migrationen anwenden.
- Mit `euer setup --set <section.key> <value>` nur die benötigten Werte setzen:
  `tax.mode`, `receipts.root`, `receipts.year_dir`, `receipts.expenses_dir`,
  `receipts.income_dir`, `exports.directory`, `user.name`, `accounts.private`.
- Kontoauszugs-Pfad, Geschäftskennungen und Lieferanten-Mappings im Dossier
  dokumentieren; dafür keine erfundenen CLI-Flags verwenden.
- `accounts.private` akzeptiert eine nichtleere kommaseparierte Liste. Ohne private
  Konten keine erfundene Kennung eintragen und keinen leeren `setup --set`-Wert
  ausführen. In einer frischen Config kann der Schlüssel entfallen (CLI-Fallback:
  `privat`); diese Kennung dann nicht für Geschäftskonten nutzen. Soll eine vorhandene
  Liste geleert werden, die Änderung gezielt in der TOML vornehmen und den Fallback
  berücksichtigen. Bestehende Klassifikationen nicht stillschweigend ändern.
- Optionale Buchungskonten über interaktives `euer setup` oder gezielt als
  `[[ledger_accounts]]` in der TOML einrichten; andere Einstellungen erhalten.
- Pfade und Namen für die tatsächliche Shell korrekt quoten. Keine wörtlichen
  Platzhalter ausführen; erforderliche Ordner mit den vorhandenen Dateitools anlegen.

Ohne lokalen Zugriff gibst du stattdessen das vollständige Dossier und konkrete,
zur Shell passende Setup-Befehle zum Kopieren aus. Kennzeichne die Einrichtung als
vorbereitet, aber noch nicht lokal geprüft. Alle fehlenden Referenzinhalte müssen
bereitgestellt werden; einen nicht gelesenen Leitfaden nicht aus dem Gedächtnis ersetzen.

## 5. Abschluss und Rückkehr zum Auftrag

Nach der Einrichtung Dossier und tatsächliche Config vergleichen, Existenz der
gewählten DB und Belegordner prüfen und auf dieser DB Kategorien sowie gegebenenfalls
Buchungskonten lesen. `euer incomplete list` zeigt offene Bestandsfälle, ist aber
kein Test für vollständiges Onboarding. Ohne Schreibauftrag keine Testbuchung anlegen.

Berichte knapp: verwendeter DB-/Config-Pfad, angelegte oder ergänzte Dateien,
geprüfte Einstellungen und offene Punkte. Für eine erste Buchung müssen Datenbank,
Steuermodus und die für diesen Vorgang nötigen Regeln geklärt sein; unvollständige
Belegdaten dürfen entsprechend dem Buchhaltungs-Skill offenbleiben.

Setze danach den ursprünglichen Buchungsauftrag fort, sofern er bereits erteilt
wurde und die nötigen Angaben vorliegen. Bei einem reinen Einrichtungsauftrag
schließe mit dem nächsten Schritt ab: erste Rechnung bzw. Kontoauszüge bereitstellen.
