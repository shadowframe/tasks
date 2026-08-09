# Task-Stack

Ein einfacher, selbst gehosteter Task-Stack für persönliche Aufgaben, Anhänge und spätere Workflows.

Repository:

https://github.com/shadowframe/tasks

## Grundidee

Der Task-Stack bildet eine kleine, stabile Aufgabenbasis. Er speichert Aufgaben, Zustände, optionale Tags, Zeitbezüge und Verweise auf Anhänge.

Hermes kann darauf aufsetzen und Aufgaben erfassen, suchen, zusammenfassen oder mit zusätzlichen Informationen anreichern. Hermes ist aber nicht Teil der eigentlichen Datenhaltung und soll unabhängig vom Task-Stack funktionieren.

Die Grundaufteilung:

```text
Task-Stack
├── TaskLite als einfaches Task-Backend
├── Attachment-Service
├── optionale Hermes-Integration
└── Prometheus-Metriken
```

TaskLite ist dabei nur eine Komponente des Task-Stacks und nicht dessen übergeordneter Name.

## Einfache Aufgabenverwaltung

Der Schwerpunkt liegt auf einer persönlichen Taskliste für:

- Einkäufe
- allgemeine Ideen
- Homelab-Aufgaben
- Recherche
- Wartung und Reparaturen

Eine Aufgabe braucht zunächst nur:

- Beschreibung
- Zustand
- Erstellungsdatum
- optional Notizen
- optional Tags
- optional Zeitbezug
- optional Anhänge

Bewusst nicht vorgesehen sind zunächst:

- Prioritätsstufen
- komplizierte Projektstrukturen
- Bewertungspunkte
- verpflichtende Kategorien
- automatische Massenänderungen

Die Taskliste soll schnell und unkompliziert bleiben. Neue Aufgaben müssen nicht zuerst vollständig klassifiziert werden.

## Tags und spätere Workflows

Tags oder Kategorien können später als einfache Ordnungsebene verwendet werden:

```text
einkauf
idee
homelab
hermes
recherche
wartung
warten
```

Darauf könnten später Workflows aufbauen, zum Beispiel:

- Aufgaben mit `einkauf` als Einkaufsliste anzeigen
- `homelab`-Aufgaben nach Dienst oder Gerät gruppieren
- `warten`-Aufgaben regelmäßig prüfen
- `wartung`-Aufgaben wiederkehrend anzeigen
- `recherche`-Aufgaben in einer passenden Ansicht anzeigen

Tags sollen zunächst keine starre Hierarchie erzwingen.

## Zeitbezogene Aufgaben

Die Aufgabenverwaltung kann später um Zeitinformationen erweitert werden:

- Fälligkeitszeitpunkt
- Startzeitpunkt
- Abschlusszeitpunkt
- geschätzte Dauer
- tatsächliche Laufzeit
- Wiederholung
- nächster Prüftermin

Damit lassen sich einfache zeitabhängige Aufgaben abbilden, ohne den Task-Stack sofort zu einem vollständigen Kalender- oder Zeiterfassungssystem zu machen.

## Unabhängige Anhänge

Anhänge werden unabhängig von der Task-Datenbank gespeichert und verwaltet.

Mögliche Dateitypen:

```text
PDF, PNG, JPG, JSON, SQL, DOCX, TXT
```

Der Task-Stack speichert nur die Verweise und Metadaten. Die Dateien liegen separat im Attachment-Service:

```text
attachments/
└── <task-id>/
    ├── <attachment-id>--rechnung.pdf
    └── <attachment-id>--screenshot.png
```

Zu den Metadaten gehören beispielsweise:

- Dateiname
- MIME-Type
- Größe
- Hash
- Erstellungszeitpunkt
- zugehörige Task-ID

Größere Dokumente können außerhalb des Task-Stacks abgelegt und aus einer Aufgabe heraus verlinkt werden.

## Hermes-Integration

Hermes soll den Task-Stack über eine API verwenden und nicht direkt auf die TaskLite-Datenbank zugreifen.

Mögliche Funktionen:

- Aufgaben anlegen und suchen
- Aufgaben nach Tags oder Zuständen filtern
- Aufgaben zusammenfassen
- Anhänge auflisten und verknüpfen
- zeitbezogene Aufgaben für Auswertungen vorbereiten
- Vorschläge für Tags oder externe Links machen

Der Task-Stack muss aber ohne Hermes funktionieren. Ein Ausfall von Hermes darf die Aufgabenverwaltung nicht stoppen.

## Unabhängigkeit von Daemons

Benutzer- und System-Daemons dürfen nicht vom Task-Stack abhängig sein.

Das bedeutet:

- Integrierte Anwendungen müssen ohne Task-Stack starten können.
- Daemons dürfen den Task-Stack optional nutzen.
- Ein Ausfall von TaskLite oder dem Attachment-Service darf keine anderen Dienste stoppen.
- Prometheus und Grafana dürfen ausfallen, ohne die Taskverwaltung zu beeinträchtigen.

Der Task-Stack ist eine optionale Infrastrukturkomponente, kein zentraler Systembus.

## Metriken und mögliche Steuerung

Der Task-Stack kann Metriken für Prometheus bereitstellen:

- offene Aufgaben
- erledigte Aufgaben
- überfällige Aufgaben
- Aufgaben nach Tag
- Aufgaben mit Fälligkeit heute
- Attachment-Anzahl und Speichergröße
- Erreichbarkeit der Dienste

Metriken sind zunächst lesend.

Ob Hermes oder Daemons später auch Aufgaben über diese Infrastruktur verändern dürfen, ist noch offen. Für direkte Steuerung müssten vorher Berechtigungen, Bestätigungen, Fehlerbehandlung und Schutz vor Massenänderungen definiert werden.

## TaskLite im Task-Stack

TaskLite ist das aktuelle Task-Backend des Task-Stacks. Es stellt die API, die Task-Datenbank und die grundlegenden Task-Funktionen bereit.

Die Webapp wird aus dem öffentlichen Downstream-Fork gebaut und über einen festen Commit referenziert. Änderungen am TaskLite-Code werden daher separat vom übrigen Task-Stack behandelt.

Weitere Informationen:

- Originalprojekt: https://github.com/ad-si/TaskLite
- öffentlicher Downstream-Fork: https://github.com/shadowframe/TaskLite-hermes
- Dokumentation des integrierten Forks: https://github.com/shadowframe/TaskLite-hermes#readme
- lokale TaskLite-Konfiguration: `~/.config/tasklite/config.yaml`

Der Task-Stack verwendet TaskLite, bleibt aber als Gesamtprojekt eigenständig.

## Öffentliche Repository-Grenze

Das öffentliche Repository enthält nur Quellcode, Docker-Konfiguration, Vorlagen und Dokumentation.

Nicht veröffentlicht werden:

```text
.env
versions.env
data/
attachments/
*.db
private Hostnamen
Tailscale-Adressen
Passwörter
Tokens
private Schlüssel
```

Die produktiven Werte bleiben auf dem jeweiligen Host. Das öffentliche Repository enthält nur sichere Vorlagen wie:

```text
.env.example
versions.env.example
```

## Start

```bash
cp .env.example .env
cp versions.env.example versions.env
docker compose up -d
docker compose ps
```

Die produktiven Daten bleiben lokal:

```text
data/
attachments/
```

## Grundsätze

- Die Taskliste bleibt klein und praktisch.
- Prioritäten sind zunächst nicht erforderlich.
- Tags und Kategorien bleiben optional.
- Anhänge werden unabhängig verwaltet.
- Zeitbezüge können später ergänzt werden.
- Hermes bleibt eine optionale intelligente Schicht.
- Daemons dürfen den Task-Stack nicht voraussetzen.
- Metriken sind zunächst lesend.
- Komplexität kommt erst hinzu, wenn ein konkreter Bedarf entsteht.
