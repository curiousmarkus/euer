# Technischer Release-Nachweis: 0.15.0 / DATEV 0.4.0

Veröffentlicht am 2026-10-04. Gemeinsamer Umfang: Core Spec 029 und DATEV Spec 001.

- Core-Tag `v0.15.0`: `e38ad3a3ea1e98bae24bdd2ef5368ede726dabbe`.
- DATEV-Tag `v0.4.0`: `27dcb2e33383caf614267637ad468a41fccb2d3e`.
- [Core-CI](https://github.com/curiousmarkus/euer/actions/runs/37198539473):
  erfolgreich, einschließlich Windows, macOS, Linux, XLSX und Coverage.
- [Core-Release](https://github.com/curiousmarkus/euer/actions/runs/37198745941):
  erfolgreich; annotierter Tag, Metadaten, Plattformtests und Prüfung derselben
  Artefakte vor PyPI/GitHub-Veröffentlichung.
- [DATEV-Release](https://github.com/curiousmarkus/euer-datev/actions/runs/37198443050):
  erfolgreich; Plattformtests und isolierte CLI-/Exportprüfung.

Der DATEV-Workflow dokumentiert im Artefakt `release-pair` den Core-Kandidaten
`b9e00dfe978cb139a6488e58201e9b21b71d7dce`. Der finale Core-Commit ergänzt nur
das explizite Schließen dreier SQLite-Testverbindungen für Windows. Sämtliche
ZIP-Einträge des Kandidaten-Wheels und des veröffentlichten Core-Wheels wurden
byteweise verglichen: identischer Inhalt. Die unterschiedlichen Wheel-Prüfsummen
entstehen durch den separaten Build; der Kandidat wird nicht als veröffentlichtes
Archiv ausgegeben.

Nach Veröffentlichung wurden beide Wheels und beide Quellarchive von PyPI
heruntergeladen und gegen PyPI-SHA256 sowie die GitHub-Release-Dateien geprüft:

| Datei | SHA256 (PyPI = GitHub) |
| --- | --- |
| `euer-0.15.0-py3-none-any.whl` | `34492138364ebe0e6aba89df888b15d3051107e69bec5514890ce98ca874d940` |
| `euer-0.15.0.tar.gz` | `0e0765aeeb1198410326e93c1ce78be59c15ce469150c7dfc483d344eb1d8319` |
| `euer_datev-0.4.0-py3-none-any.whl` | `87b01d3ac2d82a7fc1bbb115a741fe6def716743c4e268bdf0fc4e6886bc8641` |
| `euer_datev-0.4.0.tar.gz` | `b0ee3a75a1b5bbd99aa3f2da2ee2691b36f7bede3ba9ec005de3478496eef849` |

`euer-datev/scripts/verify_cli_paths.py` wurde anschließend erneut mit genau den
veröffentlichten Wheels ausgeführt: erfolgreich. Das umfasst getrennte und
gemeinsame Installationen, Core-Delegation, Exit-Codes 0/1/2, Validierung,
befüllte Exporte, Steuerfälle und Belegpakete.

Die [öffentlichen Upgrade-Hinweise](https://euer-buchhaltung.de/datev/versionshinweise)
sind veröffentlicht; Website-Lint und Production-Build waren erfolgreich.
Die [Homebrew-Pipeline](https://github.com/curiousmarkus/homebrew-euer/actions/runs/37199033423)
hat beide Formeln auf macOS und Linux installiert und getestet. Die geprüften
Formeln wurden gemeinsam als Tap-Commit
`5bc827985b06935bf1e520223b2093f9ada45b98` veröffentlicht; Versionen und
Quellarchiv-Prüfsummen stimmen mit den obigen PyPI-Artefakten überein.
Beide Pakete müssen vor der Migration aktualisiert werden. Datenbank sichern,
`euer init --dry-run` prüfen, dann migrieren und den vollständigen Skill 1.3.0
aktualisieren. Keine automatische Zuordnung alter Einnahmen zu neuen Defaults.

Ein Testimport in der konkret verwendeten externen DATEV-Anwendung ist durch
diese technische Abnahme nicht nachgewiesen; die Produktdokumentation beschreibt
ihn als Prüfung vor der produktiven Übergabe.
