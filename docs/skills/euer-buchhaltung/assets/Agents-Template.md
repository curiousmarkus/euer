# Mandanten-Dossier: {{NAME}}

Dieses Dokument enthält die bestätigten Angaben für die Buchhaltung von
{{NAME}}. Ungeklärte Angaben bleiben als offene Punkte mit nächstem Schritt
sichtbar. Allgemeine Buchungsregeln und CLI-Befehle stehen im
`euer-buchhaltung`-Skill.

Die euer zugrunde liegende Datenbank wird niemals direkt gelesen, geschrieben, geöffnet oder durchsucht. Keine direkten Zugriffe mit SQLite, Python, Dateivorschauen, Datenbank-Editoren oder anderen Werkzeugen. Der Zugriff erfolgt ausschließlich über die CLI, die die Datenbank in einem konsistenten Zustand hält und auch für Abfragen und Export die nötigen Befehle bereitstellt. 
Status und effektiven Pfad der Datenbank bei Bedarf ausschließlich mit `euer doctor` prüfen.

## Mandant und Arbeitsbereich

- **Name und Geschäftsform:** {{NAME_UND_GESCHAEFTSFORM}}
- **EÜR-Nutzung:** {{GEKLAERTER_STATUS_ODER_OFFEN}}
- **Buchhaltungsordner:** {{ARBEITSORDNER}}
- **Beginn und bereits erfasste Zeiträume:** {{ZEITRAEUME}}

## Steuerlicher Kontext

- **Bestätigter Umsatzsteuerstatus:** {{SMALL_BUSINESS_STANDARD_ODER_OFFEN}}
- **Besteuerungsart und UStVA-Zeitraum, soweit relevant:** {{BESTEUERUNGSART_UND_ZEITRAUM}}
- **Prüfung und Übermittlung:** {{ZUSTAENDIGKEIT}}
- **Weitere geklärte Besonderheiten:** {{STEUERLICHE_BESONDERHEITEN}}

### Geklärte Auslands- und Reverse-Charge-Fälle

| Leistendes Unternehmen und Sitz | Leistung | Bestätigte Behandlung | Grundlage und Geltung |
|---|---|---|---|
| {{UNTERNEHMEN_UND_SITZ}} | {{LEISTUNG}} | {{BEHANDLUNG_ODER_OFFEN}} | {{BELEG_ODER_AUSKUNFT_UND_ZEITRAUM}} |

## Dateiablage und Werkzeuge

- **Beleg-Root und Jahresordner:** {{BELEG_ROOT_UND_JAHRESORDNER}}
- **Unterordner für Ausgaben und Einnahmen:** {{TYP_UNTERORDNER}}
- **Vereinbarte Dateinamen:** {{DATEINAMEN_REGEL}}
- **Kontoauszüge:** {{PFAD_KONTOAUSZUEGE}}
- **Exporte:** {{EXPORTORDNER}}
- **PDF-/OCR-Werkzeug:** {{BELEGLESE_WERKZEUG}}

## Konten und private Vorgänge

| Kennung | Geschäftlich oder privat | Konto/Zahlungsart | Besonderheiten |
|---|---|---|---|
| {{KENNUNG}} | {{TYP}} | {{KONTO_ODER_ZAHLUNGSART}} | {{BESONDERHEIT}} |

- **Privat bezahlte Betriebsausgaben und Ausgleichsüberweisungen:** {{PRIVATE_AUSLAGEN}}
- **Gemischte Nutzung mit bestätigter Grundlage:** {{GEMISCHTE_NUTZUNG_ODER_OFFEN}}

## Wiederkehrende Zuordnungen

| Lieferant | Sitz/Land | Fachliche Kategorie | Geklärte Besonderheit |
|---|---|---|---|
| {{LIEFERANT}} | {{SITZ_ODER_LAND}} | {{KATEGORIE_ODER_OFFEN}} | {{BESONDERHEIT_ODER_OFFEN}} |

{{OPTIONALE_BUCHUNGSKONTEN_UND_WEITERE_ZUORDNUNGEN}}

## Zusammenarbeit und offene Punkte

- **Rhythmus für Kontoauszüge und Abgleich:** {{ABGLEICH_RHYTHMUS}}
- **Sicherungsziel:** {{SICHERUNGSZIEL}}
- **Weitere mandantenspezifische Regeln:** {{INDIVIDUELLE_REGELN}}

| Offener Punkt | Nächster Schritt | Zuständig |
|---|---|---|
| {{OFFENER_PUNKT}} | {{NAECHSTER_SCHRITT}} | {{ZUSTAENDIG}} |
