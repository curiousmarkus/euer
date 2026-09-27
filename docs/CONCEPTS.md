# Konzept und Grenzen

`euer` ist ein lokales CLI für die Einnahmenüberschussrechnung (EÜR). Es richtet
sich an Freiberufler und Einzelunternehmer, die ihre laufende Buchhaltung einem
KI-Agenten übertragen möchten. Der Agent liest Unterlagen, gleicht Zahlungen ab
und bedient die CLI. Der Mensch liefert den geschäftlichen Kontext, äußert bei
offenen Entscheidungen eine Präferenz und prüft die Ergebnisse vor der steuerlichen
Abgabe.

## Die Rollen im Zusammenspiel

| Beteiligter | Aufgabe |
|---|---|
| Mensch | Stellt Belege und Kontoauszüge bereit, erklärt betriebliche Sachverhalte, äußert bei nachvollziehbar dargestellten Alternativen eine Präferenz und gibt Erklärungen selbst ab. |
| Agent | Liest Unterlagen, prüft vorhandene Buchungen, recherchiert steuerliche Regeln anhand belastbarer Quellen, begründet Einordnungen, führt CLI-Befehle aus und meldet Unklarheiten. |
| `euer` | Speichert und validiert Buchungen, protokolliert Änderungen über die CLI und erstellt Auswertungen und Exporte aus den erfassten Daten. |

Der Agent soll Routinearbeit selbstständig erledigen. Fehlen betriebliche
Fakten, fragt er den Menschen. Bei steuerlich unklaren Fällen legt er mögliche
Einordnungen mit Begründung und Folgen offen, damit der Mensch eine Präferenz
äußern oder fachlichen Rat einholen kann.
Die CLI kann Eingaben auf Plausibilität prüfen; sie kann aus einer Rechnung
allein weder den tatsächlichen Geldfluss noch jede steuerliche Behandlung
bestimmen. Schutzprüfungen ersetzen deshalb keine fachliche Prüfung.

## Zwei Arten von Agentenanweisungen

Der ausgelieferte [Buchhaltungs-Skill](skills/euer-buchhaltung/SKILL.md) enthält
den allgemeinen Arbeitsablauf und verweist auf die [CLI-Referenz](skills/euer-buchhaltung/references/cli_reference.md)
und die [Fachregeln](skills/euer-buchhaltung/references/domain_rules.md). Er wird
mit der Software aktualisiert und enthält keine persönlichen Mandantendaten.
Seine Regeln leiten die Prüfung an; sie legen die steuerliche Behandlung eines
konkreten, noch ungeklärten Vorgangs nicht verbindlich fest.

Im Buchhaltungsordner liegt die persönliche `AGENTS.md` als **Mandanten-Dossier**
([Vorlage](skills/euer-buchhaltung/assets/Agents-Template.md)). Darin stehen geklärter Steuerstatus,
Konten, Belegpfade, wiederkehrende Zuordnungen und offene Sonderfälle. Der Agent
nutzt dieses Dossier als Kontext und ergänzt persönliche Regeln nur nach
Abstimmung.

## Daten und Nachvollziehbarkeit

Die Buchungen liegen in einer lokalen SQLite-Datei. Konfiguration und
Belegdateien liegen getrennt davon an den gewählten lokalen Pfaden. `euer`
benötigt für die Buchführung keinen Cloud-Dienst und ist als Open Source unter
AGPLv3 lizenziert. Welche Unterlagen eine KI-Anwendung an einen
Modellanbieter überträgt, hängt von der verwendeten Anwendung und ihrer
Konfiguration ab.

Der Agent bucht und korrigiert über die CLI. Sie validiert Eingaben und schreibt
Änderungen in das Audit-Log. Direkte SQL-Schreibzugriffe umgehen diese
Prüfungen; lesende Abfragen sind für zusätzliche Auswertungen möglich. Belege
und Kontoauszüge bleiben die Grundlage zur Kontrolle. Eine Änderungshistorie
ersetzt weder die Originalunterlagen noch eine Sicherung der Datenbank und
Dateien.

## Was `euer` abdeckt

`euer` erfasst Einnahmen, Ausgaben und Privatvorgänge anhand des tatsächlichen
Zahlungsflusses. Ausnahmen vom Zufluss- und Abflussprinzip erfordern eine
gesonderte fachliche Prüfung. Es unterstützt Kategorien, Umsatzsteuerangaben,
Kleinunternehmerfälle und bestimmte Reverse-Charge-Vorgänge. Aus den Buchungen
erstellt es EÜR-Auswertungen, einen UStVA-Arbeitsbericht und CSV- beziehungsweise
optional XLSX-Exporte. EÜR-Zeilennummern werden nur für mitgelieferte
Formularjahre angezeigt.

Die CLI liest Rechnungen und Kontoauszüge nicht selbst. Sie ruft auch keine
Bankdaten ab, entscheidet keine ungeklärten Steuerfragen und übermittelt keine
Erklärungen an ELSTER. Jahreswechsel, fehlende Belege, Anlagegüter und andere
Sonderfälle können zusätzliche fachliche Klärung erfordern. Vor einer Abgabe
prüft der Mensch die Buchungen, Berichte und Zuordnung zum jeweiligen Formularjahr.

Der konkrete Ablauf von Einrichtung bis Jahresabschluss steht in der
[User Journey](USER_JOURNEY.md).
