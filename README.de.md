# Sprite & Sprite Sheet Agent

**Erst die Bewegung entwerfen, dann jedes Einzelbild zeichnen. Jede Änderung bleibt auf ihre Referenz zurückführbar.**

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Español](README.es.md)

v0.2.0 · **design by santu**

Ein Arbeitsablauf mit Offline-Werkzeugen für KI-Assistenten mit Bildverständnis. Aus Figurenansichten und Bewegungsanforderungen entstehen geordnete Posenstrukturen, unabhängige Figurenbilder, Prüf-GIFs und schließlich ein Sprite Sheet als PNG mit JSON-Metadaten.

<p align="center"><img src="assets/readme/structure-sequence.png" width="100%" alt="Drei tatsächlich gerenderte anonyme Posen mit Gelenken, Requisite und Kontaktpunkten"></p>

*Tatsächliche Ausgabe von `scripts/build_demo.py`. Das anonyme technische Beispiel ist weder fertige Figurengrafik noch eine freigegebene Animation.*

## Von der Pose zur Ausgabe

<p align="center"><img src="assets/readme/workflow.svg" width="100%" alt="Posen entwerfen, Einzelbilder prüfen, PNG und JSON exportieren"></p>

1. **Struktur entwerfen** — Figur, Aktionen und Requisiten bestätigen. Stützpunkte, Verdeckungen und Kontakte je Richtung festlegen, danach Bereichsgrenzen und Paletten prüfen.
2. **Einzelbilder prüfen** — Nach Strukturfreigabe zuerst Schlüsselposen, dann unabhängige Übergangsbilder erzeugen. Referenzen, RAW, Kandidaten und Nachbarbilder vergleichen.
3. **Assets exportieren** — Nach menschlicher Freigabe der aktuellen Figurengruppe PNG und JSON mit Bildrechtecken, Pivots und Laufzeiten ausgeben. Die Engine-Anbindung erfolgt separat.

| Funktion | Verhalten |
| --- | --- |
| Aktive Versionen | Nur Gruppen aus dem Manifest anzeigen. Geänderte Dateien brauchen neue Hashes; alte Freigaben werden ungültig. |
| Vergleichsansicht | Struktur, KI-RAW und Kandidat in drei Spalten; Nachbarbilder, gemeinsame Anzeigegröße, Hintergründe und Einzelbildsteuerung. |
| Pixelschutz | Methode C stellt unbewegte Bereiche an identischen Koordinaten wieder her und erstellt Vergleichsbilder und Differenzberichte. |
| Auftragsverwaltung | Referenzen, Budget und Rückmeldungen als Offline-Paket speichern. Bei Wiederaufnahme den bestehenden Auftrag abfragen und doppelte Übernahme blockieren. |
| Verlustfreier Atlas | PNG + JSON aus der aktuell freigegebenen Gruppe exportieren und pixelgenaue Rekonstruktion prüfen. |

**Der KI-Host übernimmt Bewegungsentwurf, Bildanalyse und Bilderzeugung. Der Nutzer erteilt die Freigabe.** Bilddienst, automatische künstlerische Freigabe und Engine-Plugin sind nicht enthalten.

## Schnellstart

Erforderlich: **Python 3.10+, Pillow sowie macOS oder Linux**. Die Auftragssperre nutzt `fcntl`; native Windows-Ausführung wird nicht unterstützt. Im Paketverzeichnis ausführen:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install Pillow
python3 scripts/build_demo.py ../sprite-agent-demo
```

`../sprite-agent-demo/review/index.html` im Browser öffnen. Die Demo zeigt Strukturen, farbige Testflächen, Bildsteuerung und den Export von Prüfanmerkungen. Die Testflächen sind keine erzeugten Figuren. Das Ausgabeverzeichnis muss leer sein; für weitere Läufe ein neues wählen. Es erfolgen keine API-Aufrufe.

## Mit einem KI-Assistenten verwenden

Den gesamten Ordner als `sprite-sheet-agent` installieren, mit `SKILL.md` direkt darin. Materialien und Ergebnisse in einem separaten Arbeitsverzeichnis speichern.

- **Codex:** konfiguriertes Skill-Verzeichnis, etwa `~/.codex/skills/sprite-sheet-agent/`. Neu laden und `$sprite-sheet-agent` aufrufen.
- **Claude Code:** `~/.claude/skills/sprite-sheet-agent/` oder das Skill-Verzeichnis des Projekts. Neu laden und `/sprite-sheet-agent` aufrufen.
- **Andere:** [AGENT.md](AGENT.md), [SKILL.md](SKILL.md) und die [Produktionsregeln](references/production-method.md) einlesen lassen.

Diese Installationswege sind noch nicht in echten Host-Sitzungen überprüft. Die README allein lädt nicht alle Regeln. Der Host benötigt Dateizugriff und Bildverständnis; die Bilderzeugung erfolgt über das gewählte Werkzeug oder eine API.

Freigegebene Vorder-, Seiten- und Rückansichten, Zielgröße und Aktionsliste vorbereiten. Bei asymmetrischen Figuren die Gegenseite ergänzen; Requisiten brauchen eigene Referenzen.

> Verwende sprite-sheet-agent in meinem Figurenverzeichnis. Prüfe die Ansichten und plane Gehen in vier Richtungen, Hinsetzen und Aufstehen. Lege zuerst Aktionsliste, Requisitenreferenzen und farbige Strukturen vor. Erzeuge unabhängige Figurenbilder erst nach meiner Freigabe. Aktualisiere die Prüfseite pro Gruppe und bewahre Originale, RAW und verworfene Versionen auf.

## A / B / C auswählen

| Methode | Modelleingabe | Verarbeitung |
| --- | --- | --- |
| A | Referenzbild + Bearbeitungsmaske + kurze Anweisung | Modellergebnis speichern und visuell prüfen. |
| B | Eingaben aus A + JSON der aktuellen Aufgabe | Modellergebnis speichern und visuell prüfen. |
| C | Wie B | Originalpixel mit separater Schutzmaske wiederherstellen, anschließend Übergänge und Bewegung prüfen. |

Ohne Maskenunterstützung den eingeschränkten Modus dokumentieren. JSON beschreibt Vorgaben, garantiert jedoch keine Umsetzung. C benötigt unbewegte Bereiche mit gleicher Größe und identischen Koordinaten. Die alte Kopfposition beim Hinsetzen, Drehen oder Laufen nicht starr festhalten.

Für dieselbe Quelle und dasselbe Modellergebnis sind höchstens zwei C-Kompositionen erlaubt. Die zweite muss die wirksame Alpha-Grenze ändern. Das sind keine zwei zusätzlichen Bildgenerierungen. Budget und Aufruflimit separat bestätigen: insgesamt drei Aufrufe je Bild sind nur ein Vorschlag; bestehende Grenzen haben Vorrang. Ohne geeigneten Kandidaten bleibt das Bild zur Überarbeitung offen.

## Dokumentation und Grenzen

[Englische Anleitung](docs/usage.en.md) · [Chinesische Anleitung](docs/usage.zh-CN.md) · [Vorlagen](templates/) · [Prüfprotokoll, chinesisch](VALIDATION.md)

Einige Offline-Prüfungen sind dokumentiert. Host-Laden, externe Bildqualität, vollständige Figurenproduktion und Engine-Anbindung müssen noch geprüft werden. Diese README ist deutsch; Anleitungen sind englisch und chinesisch, Skill-Regeln und Prüfoberfläche überwiegend chinesisch.

Ein automatischer Farbdetektor ist nicht enthalten. Der Host prüft Farben in freigegebenen Bereichen und beurteilt die Bilder. Originale und RAW erhalten; technische Prüfungen, Selbstprüfung, Nutzerfreigabe und Engine-Validierung getrennt führen. Skripte dürfen Strukturhilfen zeichnen, aber keine fertige Figurenbewegung durch Spiegeln, Zusammensetzen von Gliedmaßen oder automatische Zwischenbilder vortäuschen.

---

**design by santu**
