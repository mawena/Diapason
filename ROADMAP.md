# Feuille de route — Diapason

Diapason est une application Ubuntu qui reconnaît l'appareil de sortie audio (casque,
enceinte Bluetooth, haut-parleurs du PC, dock, HDMI) et lui applique tout seul les
réglages qui le font le mieux sonner.

Les phases 2 et suivantes sont **provisoires**. Elles seront revues à la fin de la
phase 1, une fois le besoin et l'approche validés.

## Phase 0 — Mise en place du projet

- [x] Dossier `~/Work/perso/Diapason`, dépôt git, git flow (`main`, `develop`, tags `v`)
- [x] README, licence MIT, CHANGELOG, feuille de route
- [x] Dépôt GitHub public `mawena/Diapason` (description, sujets), remote `origin` en SSH
- [x] Conversation de lancement rattachée au dossier du projet

## Phase 1 — Conception

- [ ] Cerner le besoin : ce qui gêne dans le son aujourd'hui, sur quels appareils, ce qu'est un son « magnifique » pour Charles
- [ ] Inventaire des sorties du poste et de ce que PipeWire sait d'elles (Bluetooth LN-1008BT, haut-parleurs et prise casque du PC, dock Dell D6000, HDMI)
- [x] Essai jetable sur l'enceinte LN-1008BT : codec SBC-XQ au lieu de SBC, égaliseur `filter-chain` réglé à chaud sans coupure ; Charles aime la « basse douce »
- [x] Essai des humeurs : cinq profils à basse douce (Douceur, Éclat, Cocon, Voix, Fête) changés à chaud
- [ ] Étude de l'existant : EasyEffects (déjà installé, 7.1.6, préréglages chargés selon la sortie), filtres `filter-chain` de PipeWire, base de corrections de casques AutoEq
- [x] Choisir l'approche : filtre `filter-chain` PipeWire propre à Diapason (choisi par Charles le 14/11), EasyEffects écarté
- [x] Document de conception dans `docs/superpowers/specs/`, validé par Charles le 14/11
- [ ] Plan de mise en œuvre et révision de cette feuille de route

## Phase 2 — Reconnaître la sortie audio (provisoire)

- [ ] Suivre en direct la sortie par défaut (changement de sortie, branchement, connexion Bluetooth)
- [ ] Identifier chaque appareil de façon stable (nom, adresse Bluetooth, carte et port ALSA : haut-parleurs ou casque)
- [ ] Classer l'appareil (casque, écouteurs, enceinte, haut-parleurs de portable, téléviseur ou ampli HDMI)

## Phase 3 — Profils de son (provisoire)

- [ ] Format d'un profil (égaliseur, volume de compensation, basses, spatialisation…)
- [ ] Profils de départ par type d'appareil
- [ ] **Humeurs** : plusieurs profils par appareil, à changer selon l'envie (signature « basse douce » de Charles), sans coupure
- [ ] Choix automatique du meilleur codec Bluetooth disponible (SBC-XQ, AAC, LDAC…)
- [ ] Corrections connues des casques (base AutoEq) quand le modèle est reconnu
- [ ] Application du profil sans coupure ni saturation (marge de gain, limiteur)

## Phase 4 — Service et application (provisoire)

- [ ] Service utilisateur systemd qui applique le bon profil à chaque changement de sortie
- [ ] Application graphique GTK4 / libadwaita : appareils reconnus, profil actif, réglage fin, écoute avant/après
- [ ] Indicateur dans la barre du haut et notification au changement de profil
- [ ] Ligne de commande `diapason`

## Phase 5 — Paquet et publication (provisoire)

- [ ] Paquet `.deb` (lintian propre) et `SHA256SUMS`
- [ ] Dépôt APT signé sur GitHub Pages (`https://mawena.github.io/Diapason/apt`), sur le modèle de Gagarine : clé « Diapason APT (mawena) », source deb822 et clé installées par le paquet
- [ ] Page d'accueil du site et script `installer.sh`
- [ ] README : lien du site et installation par apt ; « About » GitHub avec le site github.io
- [ ] Première release 0.1.0 (git flow, CHANGELOG, tag, release GitHub)
