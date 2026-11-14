# Diapason

**Le son s'accorde à ton équipement.** Diapason est une application Ubuntu qui
reconnaît l'appareil sur lequel joue le son (casque, enceinte Bluetooth,
haut-parleurs du PC, dock, téléviseur ou ampli en HDMI). Elle lui applique tout seul
les réglages qui le font le mieux sonner.

Site (à partir de la première version) : https://mawena.github.io/Diapason/

> **État : en conception.** Rien n'est encore installable. L'avancement est suivi
> dans la [feuille de route](ROADMAP.md).

## À quoi il sert

Chaque appareil de sortie a sa propre couleur sonore. Les haut-parleurs d'un portable
manquent de basses, une enceinte Bluetooth peut les avoir trop chargées et chaque
casque a sa courbe. Avec un réglage unique, une partie des appareils sonne toujours
mal, et refaire l'égaliseur à chaque changement est fastidieux.

Diapason vise à :

- suivre la sortie audio active, au branchement comme à la connexion Bluetooth ;
- reconnaître chaque appareil et retrouver son profil de son ;
- appliquer ce profil aussitôt, sans coupure ni saturation ;
- proposer un bon profil de départ pour un appareil nouveau, à partir de son type ou
  des corrections connues pour son modèle de casque ;
- laisser affiner chaque profil à l'oreille, avec une écoute avant/après.

## Installation

Pas encore disponible. Dès la première version, Diapason sera livré :

- en paquet `.deb` ;
- dans un dépôt APT signé (`https://mawena.github.io/Diapason/apt`), pour que
  `sudo apt update && sudo apt upgrade` installe les nouvelles versions.

Cette section donnera alors l'installation pas à pas.

## Utilisation

À venir. Prévu : une application graphique (appareils reconnus, profil actif,
réglage fin), un indicateur dans la barre du haut et une commande `diapason`.

## Configuration

À venir. Les profils seront rangés dans le dossier de l'utilisateur
(`~/.config/diapason/`).

## Prérequis visés

- Ubuntu 24.04 LTS ou plus récent
- PipeWire avec WirePlumber (la pile audio par défaut d'Ubuntu)

## Structure du dépôt

| Chemin | Rôle |
|---|---|
| `ROADMAP.md` | Feuille de route, phase par phase |
| `CHANGELOG.md` | Historique des versions |
| `docs/` | Conception et documentation |
| `LICENSE` | Licence MIT |

## Développement

Le dépôt suit **git flow** : `main` (versions publiées), `develop` (intégration),
branches `feature/*`, `release/*` et `hotfix/*`, tags `vX.Y.Z`. Les messages de
commit sont en français (commits conventionnels).

## Licence

[MIT](LICENSE), © 2026 mawena.
