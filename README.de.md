# FreeBuds Client

[![CI](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml/badge.svg)](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-green)](LICENSE)

[**English**](README.md) | [**Português (Brasil)**](README.pt-BR.md) | [**Español**](README.es.md) | [**Русский**](README.ru.md) | [**简体中文**](README.zh-CN.md) | [**Français**](README.fr.md) | [**Deutsch**](README.de.md) | [**日本語**](README.ja.md)

> ⚠️ **Hinweis:** Diese Übersetzung wurde mit künstlicher Intelligenz (KI) erstellt und kann Fehler oder Ungenauigkeiten enthalten. Die Originaldokumentation ist auf [Englisch](README.md) und [Portugiesisch](README.pt-BR.md) verfügbar.

**Inoffizieller** Windows-Desktop-Client zur Verwaltung von HUAWEI FreeBuds Kopfhörern, inspiriert von der Benutzerfreundlichkeit des Galaxy Buds Client. Ziel ist es, Akkustand, Geräuschsteuerung, Klangprofile, Gesten, Multipoint-Status und Hardwarediagnose ohne Huawei-Konto und ohne HUAWEI AI Life bereitzustellen.

---

## ⚡ Schnellübersicht (TL;DR)

Für alle, die nur die wichtigsten Fakten benötigen:

- **Was es ist:** Eine schlanke Windows-Anwendung (mit moderner HarmonyOS-inspirierter Benutzeroberfläche und CLI) zur Überwachung und Konfiguration von HUAWEI FreeBuds direkt am PC.
- **Was es bietet:**
  - Echtzeit-Akkustand für beide Kopfhörer (L/R) und das Ladeetui.
  - Umschaltung der Geräuschsteuerung (ANC: Geräuschunterdrückung, Aus, Aufmerksamkeit) und Adaptive Aufmerksamkeit (11 Stufen).
  - Klangprofile (HUAWEI SOUND), Raumklang, Trageerkennung und Gestensteuerung (Tippen/Kopfbewegungen).
  - Minimierung in den Windows-Infobereich (System Tray).
  - Umfassende Mehrsprachigkeit (mit Sprachauswahl in den Einstellungen).
- **Was es NICHT tut:** Es ersetzt nicht die offizielle Smartphone-App (keine Firmware-Updates, kein erweiterter benutzerdefinierter Equalizer, kein Auffinden verlegter Kopfhörer).
- **Schnellstart:** Laden Sie die eigenständige `.exe`-Datei direkt von der [Releases](https://github.com/hrbtnog/freebuds-client/releases)-Seite herunter oder starten Sie den Quellcode mit Python 3.10+ (`pip install -e ".[ui]"` und dann `freebuds-ui`).
- **Persönliches Projekt:** Ein nicht-kommerzielles Freizeitprojekt, entwickelt mit KI-Unterstützung. Feedback, Fehlermeldungen und Pull Requests sind herzlich willkommen!

---

## Über mich und die Motivation hinter dem Projekt

Ich bin **kein Programmierer** und habe nie in der Softwareentwicklung gearbeitet. Dies ist ein persönliches Lernprojekt: Ich wollte den Akkustand und die Geräuschunterdrückung meiner FreeBuds Pro 5 bequem am PC steuern, ohne auf das Smartphone oder HUAWEI AI Life angewiesen zu sein.

Die Anwendung soll die offizielle App auf dem Smartphone nicht vollständig ersetzen. Erweiterte Funktionen wie benutzerdefinierte Equalizer-Kurven, Ladeetui-Signaltöne, Suchfunktionen oder Passformtests sind derzeit nicht enthalten.

Die Idee ist schlicht, den täglichen Komfort zu steigern, indem grundlegende Funktionen direkt unter Windows zur Verfügung stehen – eine Lücke, die Huawei ab Werk nicht schließt.

Es handelt sich um kein kommerzielles Produkt; es gibt keinen offiziellen Support und keine Garantie. Der Code wurde mit KI-Unterstützung geschrieben und auf eigener Hardware getestet. Wenn Sie Fehler finden, melden Sie diese gerne.

## Wichtige Hinweise

- **Nutzung auf eigene Verantwortung.** Die Software kommuniziert per Bluetooth mit Ihren Kopfhörern und verändert Geräteeinstellungen.
- **Inoffizielles Projekt.** Keine Zugehörigkeit zu, Förderung oder Billigung durch Huawei, HONOR oder andere Hersteller. Marken und Logos gehören ihren jeweiligen Eigentümern; siehe [`NOTICE.md`](NOTICE.md).
- **Keine Firmware-Updates** und keine Umgehung von Windows-Sicherheitsabfragen (Kopplung, PIN-Eingabe).
- **Keine persönlichen Daten veröffentlichen.** Bitte teilen Sie keine vollständigen Bluetooth-MAC-Adressen, Seriennummern oder Datenmitschnitte in öffentlichen Issues.

## Projektstatus

> **Status:** Kernfunktionen erfolgreich implementiert. Protokoll-Engine, Diagnose-CLI und Hardware-Reverse-Engineering wurden am **2026-10-21** auf Hardware mit FreeBuds Pro 5 auf Kanal `1` validiert: Geräteauflistung, Handshake, Akkuabfrage und alle drei ANC-Modi arbeiten zuverlässig. Die PySide6-Benutzeroberfläche unterstützt ANC-Schreibbefehle (`0x2B04`), HUAWEI SOUND, Raumklang, adaptive Lautstärke, Gesprächserkennung und Kopfsteuerung. Die Testsuite umfasst **90 automatisierte Tests**. Multipoint und Wischgesten bleiben aus Sicherheitsgründen schreibgeschützt.

## Dokumentation

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — Frame-Format, CRC16, TLVs und bekannte Befehle.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Architektur, Threading und UI-Worker.
- [`docs/CAPTURE_GUIDE.md`](docs/CAPTURE_GUIDE.md) — Anleitung zum Mitschnitt von Bluetooth-HCI-Daten unter Android.
- [`CHECKPOINT.md`](CHECKPOINT.md) — Wiederherstellungspunkt und technische Validierung.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Hinweise zum Mitwirken und Erstellen von Pull Requests.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Community-Verhaltenskodex.
- [`SECURITY.md`](SECURITY.md) — Sicherheits- und Datenschutzrichtlinien.
- [`NOTICE.md`](NOTICE.md) — Markennachweise und Drittanbieterlizenzen.
- [`LICENSE`](LICENSE) — MIT-Lizenz.
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — Veröffentlichungshandbuch.

## Benutzeroberfläche

Die Oberfläche adaptiert das moderne HUAWEI Audio Connect Design für Windows-Desktop-Monitore:

- Feste linke Navigationsleiste mit Geräteselektor;
- Zentraler Inhaltsbereich mit maximaler Breite gegen unschönes Strecken auf Widescreen-Monitoren;
- Abgerundete Karten (24 px Radius, Hero 28 px) und feine Trennlinien;
- Klare typografische Hierarchie;
- Segmentierte Schalter mit Symbolen für die Geräuschsteuerung;
- Typisches HUAWEI-Blau `#0A59F7` für aktive Elemente und Links;
- Gestochen scharfe SVG-Vektorsymbole;
- Vertikale Akku-Pills mit Ladeanzeigen und zentrierten Prozentwerten;
- Eigene Seiten für **Übersicht**, **Audio**, **Gesten**, **Verbindung** und **Diagnose**.

![FreeBuds Client Übersicht](docs/ui/visao-geral.png)

## Funktionsumfang

- Erkennung und Kopplung von Bluetooth Classic über Windows-APIs.
- RFCOMM/SPP-Verbindung mit automatischem Kanalversuch (`1` und `16`).
- Vollständiger Huawei-Protokoll-Codec (Frame `0x5A`, TLV, CRC16/XMODEM).
- Handshake (`0x0107`), Akkuanzeige (`0x0108`) und ANC-Status (`0x2B2A`).
- Vollwertige ANC-Steuerung (`0x2B04`): Aus, Geräuschunterdrückung, Aufmerksamkeit und Adaptive Intensität (1 bis 11).
- Hintergrund-Worker mit automatischer Wiederverbindung und Live-Benachrichtigungen.
- CLI-Modus mit `--json`, Rohdaten-Inspektion (`--raw`) und Live-Mithören (`--listen`).
- Dunkles Farbschema mit System-Tray-Minimierung.
- Einstellungen für HUAWEI SOUND, Raumklang, Trageerkennung und Spiele-Modus (niedrige Latenz).
- Gestenanpassung für langes Drücken, Doppeltippen, Dreifachtippen und Kopfbewegungen.
- Vollständige Mehrsprachigkeit.
- Persistente Konfiguration unter `%APPDATA%\FreeBudsClient\settings.json`.

## Voraussetzungen

- Windows 10 oder 11 mit aktiviertem Bluetooth.
- Gekoppelte, eingeschaltete FreeBuds außerhalb des Ladeetuis.

## Download & Installation

Vorkompilierte `.exe`-Dateien finden Sie im Bereich [Releases](https://github.com/hrbtnog/freebuds-client/releases).

Ausführung aus dem Quellcode:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ui]"
freebuds-ui
```

## Standalone-Executable (.exe) erstellen

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui]" pyinstaller
.\.venv\Scripts\pyinstaller.exe FreeBudsClient.spec --clean -y
```
Die fertige Datei liegt in `dist\FreeBudsClient.exe`.

## Lizenz

Lizenziert unter der **MIT-Lizenz** — siehe [`LICENSE`](LICENSE). Fremde Marken und Produktbilder verbleiben im Eigentum ihrer Rechteinhaber (siehe [`NOTICE.md`](NOTICE.md)).
