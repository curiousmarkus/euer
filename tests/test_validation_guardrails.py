import datetime
import unittest

from tests.cli_test_base import BaseCLITestCase


class ValidationGuardrailsTestCase(BaseCLITestCase):
    def test_vat_math_mismatch_rejected(self):
        # 119,00 € mit 7% USt, aber explizit 19,00 € USt angegeben -> Fehler
        res_exp = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-03-01",
                "--vendor",
                "Falsche USt GmbH",
                "--amount",
                "-119.00",
                "--category",
                "Laufende EDV-Kosten",
                "--vat-rate",
                "7",
                "--vat",
                "19.00",
            ]
        )
        self.assertNotEqual(res_exp.returncode, 0)
        self.assertIn("weicht um mehr als 0,02 € von rechnerischer USt", res_exp.stderr)

        # Gleiches für Einnahmen
        res_inc = self.run_cli(
            [
                "add",
                "income",
                "--date",
                "2026-03-01",
                "--source",
                "Falsche USt Kunde",
                "--amount",
                "119.00",
                "--vat-rate",
                "7",
                "--vat",
                "19.00",
            ]
        )
        self.assertNotEqual(res_inc.returncode, 0)
        self.assertIn("weicht um mehr als 0,02 € von rechnerischer USt", res_inc.stderr)

    def test_vat_math_consistent_accepted(self):
        # 119,00 € mit 19% USt und 19,00 € Steuer -> konsistent
        res_exp = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-03-01",
                "--vendor",
                "Korrekte USt GmbH",
                "--amount",
                "-119.00",
                "--category",
                "Laufende EDV-Kosten",
                "--vat-rate",
                "19",
                "--vat",
                "19.00",
            ],
            check=True,
        )
        self.assertIn("hinzugefügt", res_exp.stdout)

        # 107,00 € mit 7% USt und 7,00 € Steuer -> konsistent
        res_inc = self.run_cli(
            [
                "add",
                "income",
                "--date",
                "2026-03-01",
                "--source",
                "Korrekte USt Kunde",
                "--amount",
                "107.00",
                "--vat-rate",
                "7",
                "--vat",
                "7.00",
            ],
            check=True,
        )
        self.assertIn("hinzugefügt", res_inc.stdout)

    def test_future_payment_date_rejected(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        res = self.run_cli(
            [
                "add",
                "expense",
                "--payment-date",
                str(tomorrow),
                "--vendor",
                "Zukunft AG",
                "--amount",
                "-50.00",
                "--category",
                "Arbeitsmittel",
            ]
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Zukunftsdaten sind bei EÜR unzulässig", res.stderr)

    def test_future_invoice_date_with_open_payment_accepted(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=5)
        res = self.run_cli(
            [
                "add",
                "expense",
                "--invoice-date",
                str(tomorrow),
                "--vendor",
                "Offene Rechnung GmbH",
                "--amount",
                "-50.00",
                "--category",
                "Arbeitsmittel",
            ],
            check=True,
        )
        self.assertIn("hinzugefügt", res.stdout)

    def test_past_date_warning(self):
        # Mehr als 2 Jahre in der Vergangenheit (z. B. 800 Tage)
        old_date = datetime.date.today() - datetime.timedelta(days=800)
        res = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                str(old_date),
                "--vendor",
                "Alte Rechnung",
                "--amount",
                "-25.00",
                "--category",
                "Arbeitsmittel",
            ],
            check=True,
        )
        self.assertIn("liegt mehr als 2 Jahre in der Vergangenheit", res.stderr)

    def test_amount_threshold_requires_force(self):
        # 6000 € ohne --force -> muss abgelehnt werden
        res = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-03-01",
                "--vendor",
                "Große Anschaffung",
                "--amount",
                "-6000.00",
                "--category",
                "Arbeitsmittel",
            ]
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("überschreitet den Schwellenwert von 5000.00 €", res.stderr)
        self.assertIn("--force", res.stderr)

        # Mit --force -> erfolgreich
        res_force = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-03-01",
                "--vendor",
                "Große Anschaffung",
                "--amount",
                "-6000.00",
                "--category",
                "Arbeitsmittel",
                "--force",
            ],
            check=True,
        )
        self.assertIn("hinzugefügt", res_force.stdout)

    def test_fuzzy_duplicate_detection(self):
        # 1. Erste Buchung anlegen: Adobe Systems Software Ireland, 59.50 € am 2026-05-10
        self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-05-10",
                "--vendor",
                "Adobe Systems Software Ireland",
                "--amount",
                "-59.50",
                "--category",
                "Laufende EDV-Kosten",
            ],
            check=True,
        )

        # 2. Zweite Buchung: gleicher Betrag, ähnlicher Name ("Adobe"), 1 Tag später (2026-05-11)
        res_dup = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-05-11",
                "--vendor",
                "Adobe",
                "--amount",
                "-59.50",
                "--category",
                "Laufende EDV-Kosten",
            ]
        )
        self.assertNotEqual(res_dup.returncode, 0)
        self.assertIn("Mögliches Duplikat", res_dup.stderr)
        self.assertIn("Adobe Systems Software Ireland", res_dup.stderr)
        self.assertIn("--allow-duplicate", res_dup.stderr)

        # 3. Mit --allow-duplicate erzwingen
        res_allowed = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-05-11",
                "--vendor",
                "Adobe",
                "--amount",
                "-59.50",
                "--category",
                "Laufende EDV-Kosten",
                "--allow-duplicate",
            ],
            check=True,
        )
        self.assertIn("hinzugefügt", res_allowed.stdout)

        # 4. Völlig anderer Kreditor am selben Tag -> kein Duplikat
        res_diff = self.run_cli(
            [
                "add",
                "expense",
                "--date",
                "2026-05-10",
                "--vendor",
                "Google Cloud EMEA",
                "--amount",
                "-59.50",
                "--category",
                "Laufende EDV-Kosten",
            ],
            check=True,
        )
        self.assertIn("hinzugefügt", res_diff.stdout)


if __name__ == "__main__":
    unittest.main()
