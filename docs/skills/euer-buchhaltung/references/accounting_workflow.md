# Buchungen und Kontoauszüge bearbeiten

Dieser Ablauf gilt auch für allgemeine Agenten ohne separate Buchhalter-Rolle.
Wähle den Einstieg nach den tatsächlich vorliegenden Unterlagen. Arbeite mit
dem persönlichen Mandanten-Dossier und den [Fachregeln](domain_rules.md);
Command-Syntax und Fehlerfälle stehen in der [CLI-Referenz](cli_reference.md).

## Vor jeder Buchungsrunde

1. Prüfe mit `euer doctor` Installation, Skill und Datenbankpfad. Lies
   das Dossier im Buchhaltungsordner. Kläre Widersprüche zwischen Dossier,
   Config und Beleg, bevor du betroffene Buchungen vornimmst.
2. Sieh vorhandene Buchungen für den Zeitraum sowie `euer incomplete list` an.
   Ergänze offene Einträge und suche nach möglichen Duplikaten, bevor du
   denselben Zahlungsvorgang neu erfasst.
3. Kläre den bestätigten Steuermodus, die Konten, den Zeitraum und die
   Belegablage. CLI-Defaults sind keine bestätigten Mandantendaten.

## Vom Kontoauszug ausgehen

1. Lies PDF-Text mit einem verfügbaren Werkzeug, etwa `markitdown`. Ist der
   Text unbrauchbar oder der Auszug gescannt, nutze verfügbare Bild-/OCR-Werkzeuge.
   Die euer-CLI extrahiert selbst keinen PDF-Inhalt. Vergleiche kritische Felder
   mit dem Original.
2. Ermittle je Bewegung Wertstellungsdatum, Gegenpartei, tatsächlichen
   EUR-Zahlbetrag und bei Fremdwährung den Originalbetrag samt Währung.
3. Suche bestehende Buchungen und zugehörige Belege. Gleiche EUR-Betrag und
   Gegenpartei exakt ab; Rechnungs- und Wertstellungsdatum dürfen abweichen.
   Bei Teilzahlungen, Gebühren, Sammelposten oder unklarer Zuordnung keine
   ungefähre Zuordnung erzwingen, sondern den Sachverhalt klären.
4. Klassifiziere geklärte Zahlungen als Ausgabe, Einnahme oder Privatvorgang.
   Für viele Einträge ist ein vorbereiteter CSV-/JSONL-Import möglich. Prüfe
   die [Importvoraussetzungen](cli_reference.md#euer-import) und das Ergebnis.

## Von Rechnungen oder Belegen ausgehen

1. Lies den Beleg wie oben und erfasse Rechnungsdatum, leistendes Unternehmen,
   Leistungsgegenstand, Rechnungsbetrag, Währung und belegte Steuerangaben.
   Bestimme die Kategorie anhand der Leistung und des Dossiers, bei Bedarf mit
   `euer list categories --year YYYY`. Leite den RC-Typ aus dem konkreten
   leistenden Unternehmen und Beleg ab, nicht allein aus einem Markennamen.
2. Suche die Zahlung im Kontoauszug und prüfe, ob sie bereits gebucht wurde.
   Eine Rechnung allein belegt keinen Geldfluss. Erfinde kein Wertstellungsdatum;
   kennzeichne ungeklärte Zahlung und benötigte Rückfrage.
3. Nutze den tatsächlichen EUR-Zahlbetrag als `--amount` und das
   Wertstellungsdatum als `--payment-date`. Dokumentiere einen belegten
   Fremdwährungsbetrag zusätzlich mit `--foreign`. Vorsteuer nur aus dem
   Beleg übernehmen; bei Bewirtung nie aus dem Zahlbetrag schätzen.
4. Benenne den Beleg nach der persönlichen Dateinamenregel mit dem
   Rechnungsdatum. Lege ihn im Jahresordner des Zahlungsdatums ab und
   verknüpfe seinen Dateinamen mit der Buchung. Fehlt der Beleg, halte den
   Mangel für die Nacharbeit fest, statt einen Dateinamen zu erfinden.

## Nachkontrolle und Rückmeldung

1. Prüfe `euer incomplete list` und `euer receipt check --year YYYY`; ergänze
   gesicherte Angaben. Ein offener Fall darf sichtbar bleiben, wenn die
   Fakten für eine korrekte Ergänzung fehlen.
2. Vergleiche Buchungen erneut mit den Kontoauszugsbewegungen. Prüfe bei Bedarf
   `summary`, `private-summary` und `vat-report`; dessen Zahlen sind ein
   Arbeitsbericht, keine automatische Steuerabgabe.
3. Gib dem Nutzer nach einer Buchungsrunde eine Liste der erfassten Vorgänge,
   Zuordnungen, fehlenden Belege und fachlichen Rückfragen. Nach einer
   Massenoperation nenne Anzahl und Gesamtsumme.
4. Korrigiert der Nutzer eine wiederkehrende Zuordnung, schlage eine konkrete
   Ergänzung seines Mandanten-Dossiers vor. Ändere dieses nicht stillschweigend.

## Besondere Abgrenzungen

- Privat bezahlte Betriebsausgaben bleiben Ausgaben; Ausgleichsüberweisungen und
  reine Kapitalbewegungen sind getrennt zu klassifizieren. Prüfe die
  [Privatregeln](domain_rules.md#privatvorgänge).
- Bei Kleinunternehmern gibt es keinen Vorsteuerabzug. Reverse Charge kann
  trotzdem eine Umsatzsteuerschuld auslösen. Bei Regelbesteuerung müssen
  Einnahmen und Ausgaben passend zur belegten USt-Behandlung klassifiziert
  werden. Details stehen in den [Steuerregeln](domain_rules.md#steuermodus-config).
- Bei Bewirtungen, Prepaid-Guthaben, Cashback oder anderen Sonderfällen lies
  die jeweilige Regel in `domain_rules.md`, bevor du buchst.
