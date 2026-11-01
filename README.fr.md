# FreeBuds Client

[![CI](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml/badge.svg)](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml)
[![Licence : MIT](https://img.shields.io/badge/licence-MIT-green)](LICENSE)

[**English**](README.md) | [**Português (Brasil)**](README.pt-BR.md) | [**Español**](README.es.md) | [**Русский**](README.ru.md) | [**简体中文**](README.zh-CN.md) | [**Français**](README.fr.md) | [**Deutsch**](README.de.md) | [**日本語**](README.ja.md)

> ⚠️ **Remarque :** Cette traduction a été effectuée par intelligence artificielle (IA) et peut contenir des erreurs ou inexactitudes. La documentation de référence originale est disponible en [anglais](README.md) et en [portugais](README.pt-BR.md).

Client de bureau **non officiel** pour Windows permettant de gérer les écouteurs HUAWEI FreeBuds, inspiré de l'ergonomie de Galaxy Buds Client. Son objectif est de fournir l'état de la batterie, le contrôle du bruit, les profils sonores, les gestes, l'état multipoint et les diagnostics matériels, sans compte Huawei et sans HUAWEI AI Life.

---

## ⚡ Résumé Rapide (TL;DR)

Si vous êtes pressé et souhaitez aller à l'essentiel :

- **Qu'est-ce que c'est :** Une application légère pour Windows (dotée d'une interface graphique moderne inspirée d'HarmonyOS et d'une CLI) pour consulter la batterie et configurer vos HUAWEI FreeBuds directement depuis votre PC.
- **Ce qu'elle fait :**
  - Affiche en temps réel le pourcentage de batterie des deux écouteurs (G/D) et du boîtier de charge.
  - Alterne entre les modes de contrôle du bruit (ANC : Réduction de bruit, Désactivé, Transparence) et Perception Adaptative (11 niveaux).
  - Configure les profils sonores (HUAWEI SOUND), l'audio spatial, la détection de port et les gestes tactiles ou de tête.
  - Se minimise discrètement dans la zone de notification (systray).
  - Support multilingue complet (avec sélecteur de langue dans les préférences).
- **Ce qu'elle NE fait PAS :** Elle ne remplace pas l'application mobile officielle (pas de mise à jour de firmware, pas d'égaliseur paramétrique personnalisé avancé, pas de recherche d'écouteurs perdus).
- **Démarrage rapide :** Téléchargez l'exécutable autonome (`.exe`) sur la page des [Releases](https://github.com/hrbtnog/freebuds-client/releases) ou lancez le code source avec Python 3.10+ (`pip install -e ".[ui]"` puis `freebuds-ui`).
- **Projet personnel :** Développé sans but commercial par un passionné avec l'aide de l'IA. Vos retours, suggestions et contributions sont chaleureusement bienvenus !

---

## À propos de moi et genèse du projet

Je **ne suis pas développeur** et n'ai jamais travaillé dans le secteur logiciel. C'est un projet personnel d'apprentissage : je souhaitais pouvoir surveiller la batterie et régler la réduction active du bruit de mes FreeBuds Pro 5 depuis mon PC, sans devoir sortir mon téléphone ni utiliser HUAWEI AI Life.

L'objectif de cette application n'est pas de se substituer intégralement à l'application officielle smartphone pour toutes les opérations avancées. Certaines fonctionnalités (égaliseur personnalisé, sonneries du boîtier, localisation ou tests d'ajustement d'embouts) ne sont pas présentes pour l'instant.

L'idée est simplement de compléter l'expérience quotidienne en offrant un accès rapide et ergonomique aux fonctions essentielles directement depuis Windows, comblant ainsi un manque natif sur PC.

Ce n'est pas un produit commercial et il est fourni sans garantie. Le code a été rédigé avec l'assistance de l'IA et testé sur mon propre matériel. Si vous rencontrez un problème, signalez-le pour que nous puissions l'améliorer. Les retours, issues et pull requests sont les bienvenus !

## Avertissement Important

- **Utilisation à vos risques et périls.** Ce logiciel communique en Bluetooth avec vos écouteurs et modifie leurs paramètres. Il n'y a aucune garantie sur d'autres modèles ou firmwares.
- **Projet non officiel.** Non affilié à, sponsorisé ni approuvé par Huawei, HONOR ou tout autre fabricant. Les marques et logos appartiennent à leurs propriétaires respectifs ; voir [`NOTICE.md`](NOTICE.md).
- **Aucune mise à jour de firmware** et aucun contournement des mécanismes de sécurité Windows (appairage, code PIN, invite de confirmation).
- **Ne publiez pas de données personnelles.** Évitez de diffuser vos adresses MAC Bluetooth complètes, numéros de série ou captures brutes dans les issues publiques.

## État du Projet

> **Statut :** Fonctionnalités majeures opérationnelles. Le moteur de communication, la CLI de diagnostic et la rétro-ingénierie du protocole ont été validés sur matériel réel (**2026-10-21**) avec des FreeBuds Pro 5 sur le canal `1` : détection, handshake, lecture de batterie et les 3 modes ANC ont répondu parfaitement. Le niveau de transparence `4` a été identifié comme la **Perception Adaptative** à 11 paliers. L'interface PySide6 avec intégration barre des tâches prend en charge l'écriture d'ANC (`0x2B04`), HUAWEI SOUND, l'audio spatial, le volume adaptatif, la détection vocale, les gestes et la détection de port. L'application dispose de **90 tests automatisés réussis**. La connexion multipoint et le balayage restent en lecture seule par sécurité.

## Documentation

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — Format des trames, CRC16, TLVs et commandes répertoriées.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Architecture logicielle, threading et workers UI.
- [`docs/CAPTURE_GUIDE.md`](docs/CAPTURE_GUIDE.md) — Guide pour capturer les paquets HCI Bluetooth sur Android.
- [`CHECKPOINT.md`](CHECKPOINT.md) — État des validations matérielles et historique technique.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — Comment contribuer, tester et soumettre des PRs.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Charte de conduite communautaire.
- [`SECURITY.md`](SECURITY.md) — Politique de sécurité et signalement de vulnérabilités.
- [`NOTICE.md`](NOTICE.md) — Mentions de marques et crédits tiers.
- [`LICENSE`](LICENSE) — Licence MIT.
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — Guide de publication des versions.

## Design de l'Interface

L'interface adopte les codes visuels des applications mobiles modernes adaptés à l'environnement Windows :

- Barre latérale de navigation fixe avec sélecteur d'appareil ;
- Contenu centré avec largeur maximale pour éviter l'étirement sur écrans larges ;
- Cartes aux coins arrondis (rayon 24 px, hero 28 px) et séparateurs subtils ;
- Typographie soignée avec hiérarchie visuelle claire ;
- Contrôles segmentés avec icônes pour le contrôle du bruit ;
- Bleu HUAWEI `#0A59F7` réservé aux états actifs et actions principales ;
- Icônes vectorielles SVG nettes et stylisées ;
- Pastilles verticales de batterie avec anneau et pourcentages centrés ;
- Pages dédiées pour **Aperçu**, **Audio**, **Gestes**, **Connexion** et **Diagnostics**.

![Vue d'ensemble FreeBuds Client](docs/ui/visao-geral.png)

## Fonctionnalités

- Détection et énumération Bluetooth Classic via l'API native Windows.
- Appairage assisté sous Windows (`BluetoothAuthenticateDeviceEx`).
- Transport RFCOMM/SPP avec négociation automatique sur les canaux `1` et `16`.
- Décodeur de protocole Huawei robuste : trames `0x5A`, TLVs, CRC16/XMODEM et tolérance aux paquets fragmentés.
- Handshake (`0x0107`), lecture de batterie (`0x0108`) et statut ANC (`0x2B2A`).
- Contrôle de l'ANC par `0x2B04` : modes normal, réduction de bruit, transparence et intensité adaptative (1 à 11).
- Client de haut niveau (`core/client.py`) avec reconnexion automatique et notifications en direct.
- CLI polyvalente avec modes `--json`, `--raw` (hexadécimal) et écoute active (`--listen`).
- Interface moderne PySide6 avec thème sombre et icône dans la zone de notification.
- Profils HUAWEI SOUND, audio spatial, volume adaptatif et reconnaissance vocale.
- Configuration des gestes d'appui long, double/triple tapotement et mouvements de tête.
- Détection intelligente de port et gestion du mode faible latence pour jeux et vidéos.
- Support multilingue complet.
- Configuration persistante enregistrée dans `%APPDATA%\FreeBudsClient\settings.json`.

## Prérequis

- Windows 10 ou 11 avec récepteur Bluetooth actif.
- Écouteurs appairés à Windows, allumés et hors du boîtier.

## Téléchargement

Un fichier exécutable autonome officiel est disponible directement dans la section [Releases](https://github.com/hrbtnog/freebuds-client/releases).

Pour lancer le projet depuis les sources :
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ui]"
freebuds-ui
```

## Compilation de l'exécutable (.exe)

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui]" pyinstaller
.\.venv\Scripts\pyinstaller.exe FreeBudsClient.spec --clean -y
```
Le fichier généré se trouvera dans `dist\FreeBudsClient.exe`.

## Licence

Sous licence **MIT** — consultez [`LICENSE`](LICENSE). Les marques et éléments visuels tiers appartiennent à leurs propriétaires respectifs (voir [`NOTICE.md`](NOTICE.md)).
