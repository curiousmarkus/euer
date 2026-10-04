# Spec 031: Betriebliche Einnahmen auf Privatkonten und Entnahmekopplung

## Status

Entwurf / Geplant (v0.16.0)

## Motivation und Ziel

In der Praxis von Einzelunternehmern und Freiberuflern kommt es vor, dass Kunden Rechnungen auf ein privates Girokonto überweisen (z. B. aus Versehen oder vor Eröffnung eines separaten Geschäftskontos) oder dass Plattform-Auszahlungen auf ein privates Konto fließen.

### Steuerrechtliche Einordnung (§ 11 EStG)
* **Zuflussprinzip:** Nach § 11 Abs. 1 EStG sind Einnahmen in dem Kalenderjahr bezogen, in dem sie dem Steuerpflichtigen zugeflossen sind. Der Zufluss auf ein privates Konto ist steuerlich sofort voll wirksam: Die Betriebseinnahme und die Umsatzsteuer entstehen im Moment der Gutschrift auf dem Privatkonto, nicht erst bei einer eventuellen späteren Weiterleitung auf das Geschäftskonto.
* **Privatentnahme:** Wirtschaftlich und buchhalterisch stellt der Zufluss auf das Privatkonto gleichzeitig eine **Privatentnahme** des Unternehmers in Höhe des zugeflossenen Betrags dar (Geldmittel verlassen das Betriebsvermögen bzw. gelangen gar nicht erst auf ein Geschäftskonto).
* **Gefahr von Doppelerfassungen:** Wenn der Unternehmer den Betrag später vom Privatkonto auf das Geschäftskonto überweist, erscheint auf dem Geschäftskontoauszug eine Gutschrift. Wird diese Gutschrift fälschlich als Einnahme gebucht, wird derselbe Umsatz doppelt versteuert. In Wahrheit handelt es sich bei der Überweisung auf das Geschäftskonto um eine steuerneutrale **Privateinlage** (oder Rückführung der Privatentnahme).

### Ausgangslage bis Spec 029
In Spec 029 wurde als Sicherheitsmaßnahme festgelegt, dass Einnahmen auf Konten, die in `[accounts] private = [...]` konfiguriert sind, mit dem Fehler `unsupported_private_income_account` abgewiesen werden, weil Privatkonten ursprünglich nur für verauslagte Betriebsausgaben (Privateinlagen) modelliert waren.

Dies führt in der Realität zu Problemen:
1. Nutzer oder Agenten müssen das Privatkonto entweder unzutreffend als Geschäftskonto deklarieren.
2. Oder die Einnahme wird erst gebucht, wenn das Geld auf dem Geschäftskonto ankommt – was das Zuflussdatum nach § 11 EStG verfälscht und bei Jahreswechseln zu falschen Steuerjahren führt.

### Ziel
Spec 031 hebt die starre Sperre auf und definiert:
1. Sichere Erfassung von Betriebseinnahmen auf Privatkonten unter Wahrung des korrekten Zuflussdatums (§ 11 EStG).
2. Automatische buchhalterische Behandlung als **Privatentnahme**.
3. Integration in `euer reconcile private` / `private summary`.
4. Saubere DATEV-Abbildung gegen das Privatentnahmekonto (SKR03: 1800 / SKR04: 2100).
5. Erkennung und Warnung vor doppelter Erfassung bei späteren Ausgleichsüberweisungen.

---

## Fachliches Modell

### 1. Datenmodell und Buchungslogik

Einnahmen auf Privatkonten bleiben reguläre Einträge in der Tabelle `income`, erhalten jedoch im Feld `account` den Bezeichner des konfigurierten Privatkontos (z. B. `p-giro`).

* **EÜR-Auswirkung:** Der Betrag (`amount_eur`) fließt zu 100 % in die Betriebseinnahmen des Buchungsjahres ein. Umsatzsteuer wird gemäß Steuersatz regulär berechnet.
* **Privatkonto-Auswirkung:** Der Vorgang wird als **Privatentnahme** gewertet:
  $$\text{Privatentnahme} = \text{Bruttobetrag der Einnahme}$$

### 2. Privatsalden-Abgleich (`euer reconcile private`)

Bisher erfasste der Privatsaldo nur Betriebsausgaben, die privat bezahlt wurden (Privateinlagen):
$$\text{Privatsaldo}_{\text{bisher}} = \sum \text{Ausgaben (privat bezahlt)}$$

Unter Spec 031 wird der Privatsaldo zu einer echten Gegenüberstellung:
$$\text{Netto-Privatsaldo} = \sum \text{Privateinlagen (Ausgaben)} - \sum \text{Privatentnahmen (Einnahmen)}$$

* Ist der Saldo **positiv**, hat das Unternehmen Schulden beim Unternehmer (Rückerstattungsanspruch aus verauslagten Kosten).
* Ist der Saldo **negativ**, hat der Unternehmer dem Unternehmen Geld entnommen (z. B. durch direkte Kundeneingänge auf das Privatkonto).

### 3. DATEV-Kontierungsregeln

Bei Exporten nach DATEV (über `euer-datev`) entscheidet das Zahlungskonto über das Gegenkonto der Einnahme:

| Kontotyp | SKR03 Gegenkonto | SKR04 Gegenkonto | Buchungssatz (Beispiel 1.190 € inkl. 19% USt) |
|---|---|---|---|
| **Betriebskonto** (z. B. `giro`) | 1200 (Bank) | 1800 (Bank) | Bank (1200) an Erlöse 19% (8400) |
| **Privatkonto** (z. B. `p-giro`) | **1800** (Privatentnahmen allgemein) | **2100** (Privatentnahmen allgemein) | Privatentnahmen (1800) an Erlöse 19% (8400) |

Zum Vergleich für Ausgaben auf Privatkonten:
* Ausgaben privat bezahlt werden gegen **Privateinlagen** gebucht (SKR03: **1890**, SKR04: **2180**).

---

## CLI- und Schnittstellenverhalten

### 1. Erfassung (`euer add income`)

```bash
euer add income \
  --amount 1190.00 \
  --date 2026-03-15 \
  --tax-rate 19 \
  --account p-giro \
  --description "Webdesign Kunde Müller (Zahlung auf Privatkonto)"
```

* Wenn `p-giro` in `[accounts] private = ["p-giro"]` definiert ist:
  * Keine Fehlermeldung mehr!
  * Ausgabe eines Hinweises:
    `[INFO] Einnahme auf Privatkonto 'p-giro' gebucht. Wirtschaftlich als Privatentnahme gewertet (1.190,00 €).`

### 2. Übersicht `euer private summary` / `euer reconcile private`

Die Auswertung trennt übersichtlich:
```text
=== Privatausgleich 2026 ===
Privateinlagen (Ausgaben privat bezahlt):     + 3.450,00 € (14 Belege)
Privatentnahmen (Einnahmen privat vereinnahmt): - 1.190,00 € ( 1 Beleg)
-----------------------------------------------------------
Netto-Erstattungsanspruch an Unternehmen:    + 2.260,00 €
```

### 3. Schutz vor Doppelerfassung bei Weiterleitung

Wenn der Nutzer später 1.190,00 € von `p-giro` auf sein Geschäftskonto `giro` überweist und diese Zeile im Kontoauszug des Geschäftskontos auftaucht:
* Diese Bankbewegung ist **keine** Betriebseinnahme.
* Sie kann als interner Geldtransit / Privateinlage gebucht werden (siehe Spec 030):
  `euer add transfer --from p-giro --to giro --amount 1190.00`
  bzw.
  `euer reconcile private --settle 1190.00 --date 2026-03-20`
* Bei manuellem Versuch, diese Weiterleitung als Einnahme zu buchen, warnt das System, wenn Datum, Betrag und Referenz auf eine kürzlich erfasste Privatkonto-Einnahme hindeuten.

---

## Migration und Upgrade

1. **Konfiguration:** Keine Schema-Änderung in der Datenbank erforderlich (Tabelle `income` besitzt bereits die Spalte `account` seit Migration 010).
2. **Validierungs-Update:** Entfernen der Fehlerbedingung `unsupported_private_income_account` aus `euercli/services/income.py`.
3. **euer-datev:** Aktualisierung der Kontenauflösung: Einnahmen mit Privatkonto mappen auf `1800` (SKR03) bzw. `2100` (SKR04), analog zur bestehenden Behandlung von Privatausgaben auf `1890`/`2180`.
