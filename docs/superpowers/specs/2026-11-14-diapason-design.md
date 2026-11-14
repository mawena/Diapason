# Diapason — conception de la version 0.1.0

Date : 14/11/2026 · Statut : relu, en attente de validation par Charles · Feuille de route : `ROADMAP.md`

## 1. Intention

Charles trouve que le son de son PC Ubuntu « peut être amélioré ». Il ne cherche pas
à corriger un défaut précis. Il veut un son plus beau, jugé à l'oreille, qui s'adapte
à l'appareil sur lequel il écoute.

L'essai du 14/11 a montré ce qui lui plaît :

- **La « basse douce ».** Les basses sont larges et arrondies, sans grondement : ce
  qui est sous 50 Hz est coupé, le grave est relevé par une étagère large vers
  100-110 Hz et le bas-médium un peu creusé.
- **Des humeurs.** Plusieurs couleurs de son, à changer selon l'envie, sans couper la
  musique. Sa préférée est **Cocon**.
- **Le meilleur codec Bluetooth.** L'enceinte LN-1008BT est passée de SBC à SBC-XQ.

Diapason est un projet personnel de Charles. Il doit rester léger : le poste a 14 Go
de RAM et il est souvent très chargé.

## 2. Objectifs de la 0.1.0

1. Le son de chaque appareil de sortie passe par un égaliseur Diapason, réglé selon
   l'humeur choisie pour cet appareil.
2. Changer d'humeur se fait sans coupure, depuis la barre du haut (indicateur) ou par
   la commande `diapason`.
3. Chaque appareil retient sa propre humeur. En revenant à l'enceinte, on retrouve
   son humeur à elle.
4. Un appareil Bluetooth passe tout seul au meilleur codec A2DP qu'il accepte.
5. Des jeux d'humeurs réglés pour deux types d'appareils : **petite enceinte
   Bluetooth** (ceux de l'essai, à reprendre tels quels) et **haut-parleurs du PC**
   (à régler avec Charles, voir § 9).
6. L'installation se fait en paquet `.deb`, depuis le dépôt APT signé du projet
   (règle commune des projets Ubuntu de Charles, sur le modèle de Gagarine).

## 3. Hors du champ de la 0.1.0 (plus tard)

- La grande fenêtre GTK4 de réglage fin, avec courbe et écoute avant/après.
- Les corrections de casques de la base AutoEq.
- Les humeurs créées ou modifiées par l'utilisateur dans l'interface. Le fichier de
  surcharge (§ 6.4) suffit pour l'instant.
- Le compresseur, le limiteur et la spatialisation : le `filter-chain` de PipeWire 1.0
  sur Ubuntu 24.04 n'a pas LV2, seulement ses filtres biquad intégrés.
- Les sorties de plus de deux canaux (5.1 en HDMI) : Diapason les laisse passer sans
  filtre.

## 4. Anti-objectifs (échec même si « ça marche »)

- **Couper le son ou le laisser muet** : en cas de plantage, de désactivation ou de
  désinstallation, le son doit revenir sur l'appareil réel, sans action de Charles.
- **Saturer** : aucune humeur ne doit faire craquer le son à volume maximal.
- **Se battre avec Charles** :
  - ne jamais imposer un codec ou un profil qu'il a choisi d'enlever ;
  - ne jamais basculer un casque Bluetooth du mode appel (HFP/HSP) au mode musique
    pendant un appel ;
  - ne jamais ramener le son sur un appareil qu'il vient de quitter.
- **Être lourd** : pas d'EasyEffects ni de programme graphique permanent pour le
  traitement. Objectif : moins de 50 Mo de RAM pour l'ensemble (service +
  indicateur + filtre) et moins de 1 % de processeur au repos.
- **Faire un saut de volume** au changement d'appareil ou d'humeur.

## 5. Approches étudiées

| | Approche | Avantages | Inconvénients |
|---|---|---|---|
| **Retenue** | **Filtre `filter-chain` de PipeWire, propre à Diapason**, piloté par un petit service | Très léger (≈ 10 Mo, 0,4 % CPU mesurés), humeurs changées à chaud par `pw-cli` sans coupure (vérifié), aucune dépendance à un autre logiciel de traitement | Pas de limiteur ni de compresseur : la sécurité repose sur les marges de gain |
| Écartée | Faire piloter EasyEffects (préréglages + chargement automatique) | Beaucoup d'effets déjà prêts | Programme graphique permanent (> 100 Mo), traitement lourd, format de préréglages qui change entre versions (7 → 8), dépendance non maîtrisée |

Charles a choisi la première approche le 14/11, après l'avoir écoutée.

## 6. Conception

### 6.1 Vue d'ensemble

```
applications ──► [ « Diapason » : sortie virtuelle (filter-chain) ] ──► appareil réel
                        ▲ réglages à chaud (pw-cli)                    (enceinte, HP…)
                        │
              diapason-service (systemd --user) ◄── D-Bus ──► diapason-indicateur
                        ▲                                      (barre du haut)
                        └──────────── D-Bus ◄──────── commande `diapason`
```

Il y a trois programmes Python 3.12, sans autre dépendance que ce que fournit
Ubuntu (`python3-gi`, `pactl`, `pw-cli`, `pw-dump`) :

- **`diapason-service`** : service utilisateur systemd. Il suit les sorties, gère le
  filtre, applique l'humeur et le codec, et expose une API D-Bus de session.
- **`diapason-indicateur`** : icône dans la barre du haut (AyatanaAppIndicator3 sur
  GTK3, comme l'indicateur de Gagarine), lancée par le démarrage automatique du
  bureau.
- **`diapason`** : la commande (§ 6.6).

Le paquet Python s'appelle `diapason/`. Les modules sans effet de bord (profils,
classement des appareils, choix du codec, écriture de la configuration du filtre)
sont séparés de ceux qui parlent à PipeWire, pour pouvoir être testés.

### 6.2 La sortie virtuelle et le suivi de l'appareil

- Diapason lance **un seul** filtre, comme l'essai : un processus enfant
  `pipewire -c <conf générée>`. La configuration est écrite dans
  `$XDG_RUNTIME_DIR/diapason/`. Le filtre crée une sortie virtuelle (nœud
  `diapason`, classe `Audio/Sink`) dont la sortie vise l'appareil réel
  (`target.object`). C'est cette sortie virtuelle qui est la sortie par défaut du
  système.
- La sortie virtuelle porte le nom de l'appareil réel : « LN-1008BT · Diapason »,
  « Haut-parleurs · Diapason ». Dans les réglages Son d'Ubuntu, Charles voit ainsi où
  part le son.
- **Changement d'appareil.** Charles choisit une sortie réelle dans les réglages Son,
  ou un appareil se connecte et WirePlumber en fait la sortie par défaut. Le service
  voit alors la sortie par défaut devenir un appareil réel. Il :
  1. redirige le filtre vers cet appareil ;
  2. applique l'humeur et le codec de l'appareil ;
  3. refait de la sortie virtuelle la sortie par défaut ;
  4. y déplace les flux en cours.

  Une courte coupure est admise au changement d'appareil, mais jamais au changement
  d'humeur. Rediriger le filtre peut se faire en relançant le processus filtre avec
  une nouvelle configuration, ou en changeant sa cible à chaud : au constructeur de
  choisir ce qui marche de façon fiable avec WirePlumber 0.4.
- **Changement de port.** Les haut-parleurs et la prise casque du PC sont **une seule
  sortie ALSA à deux ports** (« Speaker + Headphones »). Un casque branché ou
  débranché change le port actif sans changer de sortie. Le service doit le voir
  (événements de la carte) et traiter chaque port comme un appareil à part.
- **Appareils laissés sans filtre** : sortie de plus de deux canaux, appareil mis sur
  « Désactivé » par Charles. Le filtre est alors arrêté et la sortie réelle reste la
  sortie par défaut.
- **Écoute des événements** : `pactl subscribe` (événements `server`, `sink`, `card`)
  suivi de lectures en `pactl -f json` ou `pw-dump`. Au constructeur de choisir.
  Contrainte : aucune boucle d'attente active.

### 6.3 Volume

- Le curseur de volume d'Ubuntu agit sur la sortie virtuelle (volume logiciel), comme
  dans l'essai.
- Quand Diapason prend un appareil, il ne doit **pas** changer ce que Charles entend
  en volume. Si le volume matériel de l'appareil n'est pas à 100 %, le service le
  reporte sur la sortie virtuelle puis met le matériel à 100 %, dans cet ordre, pour
  ne jamais passer par un pic.
- Quand Diapason rend l'appareil, il fait l'inverse : le volume de la sortie
  virtuelle est reporté sur l'appareil.
- Les marges de gain des humeurs (§ 6.4) baissent un peu le niveau. Pour 0.1.0, c'est
  accepté et documenté. Le service ne compense pas automatiquement : une
  compensation risquerait la saturation.

### 6.4 Humeurs et profils

- **Une humeur** est une liste de filtres biquad (`bq_highpass`, `bq_lowshelf`,
  `bq_peaking`, `bq_highshelf`), chacun avec ses paramètres (Freq, Q, Gain), plus une
  **marge** (gain négatif, réalisé comme dans l'essai par un `bq_highshelf` à
  0 Hz).
- **Un jeu d'humeurs** existe par **type d'appareil** : `enceinte-bluetooth`,
  `haut-parleurs-pc`, puis plus tard `casque`, `hdmi`… Les mêmes noms d'humeur
  existent pour chaque type (Douceur, Éclat, Cocon, Voix, Fête), avec des réglages
  propres au type. Il y a aussi **Neutre** (filtre plat, marge 0) et **Désactivé**
  (pas de filtre du tout).
- **Contrainte de chaîne fixe.** Pour changer d'humeur à chaud, toutes les humeurs
  d'un type ont la **même chaîne** de filtres : mêmes types, même ordre. Seules les
  valeurs changent. La chaîne de l'essai (marge, coupe, grave, boîte, voix, air) est
  celle de `enceinte-bluetooth`. Un type peut avoir sa propre chaîne.
- **Règle anti-saturation**, vérifiée par un test sur chaque humeur livrée : le gain
  maximal de la réponse en fréquence de toute la chaîne (marge comprise), calculé de
  20 Hz à 20 kHz, doit rester **≤ 0 dB**.
- **Fichiers** : profils livrés dans `/usr/share/diapason/profils/<type>.toml`,
  surcharges de Charles dans `~/.config/diapason/profils/<type>.toml` (mêmes clés ;
  une humeur du même nom remplace celle livrée). Lecture avec `tomllib`.
- **Valeurs de départ de `enceinte-bluetooth`** (celles de l'essai, validées par
  Charles) :

| Humeur | marge | grave (Hz / dB / Q) | boîte (Hz / dB) | voix (Hz / Q / dB) | air (Hz / dB) |
|---|---|---|---|---|---|
| Douceur | −4,5 | 110 / +3,5 / 0,7 | 300 / −2,5 | 2800 / 1,4 / +1,0 | 9000 / +3,0 |
| Éclat | −4,0 | 110 / +3,5 / 0,7 | 300 / −1,5 | 3000 / 0,9 / +2,5 | 8000 / +4,0 |
| **Cocon** | −5,5 | 100 / +5,0 / 0,6 | 320 / −2,0 | 2800 / 1,0 / −0,5 | 10000 / +1,5 |
| Voix | −4,0 | 120 / +2,0 / 0,7 | 300 / −2,5 | 2500 / 0,8 / +3,5 | 8000 / +2,0 |
| Fête | −6,0 | 90 / +5,5 / 0,7 | 350 / −3,0 | 3200 / 1,0 / +1,5 | 9000 / +4,5 |

  Pour toutes les humeurs : coupe en passe-haut à 50 Hz, Q 0,707 ; air en étagère
  haute, Q 0,7 ; boîte en pic, Q 1,0. Si la règle anti-saturation refuse l'une de ces
  humeurs, on augmente la marge, sans toucher la courbe.

- **Valeurs de départ de `haut-parleurs-pc`** : à régler à l'oreille avec Charles
  (§ 9). Même famille « basse douce », mais la coupure se fait plus haut : les
  haut-parleurs de portable ne descendent pas sous 120-200 Hz.
- **Humeur par défaut** : Cocon pour un appareil jamais vu d'un type connu, Neutre
  pour un type sans profil livré.

### 6.5 Reconnaître et classer les appareils

- **Identité stable d'un appareil** :
  - Bluetooth : l'adresse (`api.bluez5.address`) ;
  - ALSA : le nom de la carte plus le port actif (`<card.name>:<port>`) ;
  - USB (dock) : le nom de la carte.

  L'identité sert de clé à l'humeur retenue.
- **Type** :
  - Bluetooth : `device.form-factor` ou `device.icon-name`. Casque ou écouteurs :
    type `casque` (sans profil livré en 0.1.0, donc Neutre). Enceinte, ou forme
    inconnue en A2DP : `enceinte-bluetooth`.
  - Port ALSA « Speaker » du PC : `haut-parleurs-pc`. Port « Headphones » : `casque`.
  - HDMI, DisplayPort ou IEC958 : `hdmi` (Neutre).
- Un fichier `~/.config/diapason/appareils.toml` permet de forcer le type d'un
  appareil mal reconnu. Pas d'interface pour cela en 0.1.0.
- **État retenu** : `~/.local/state/diapason/etat.json` (humeur par appareil, dernier
  appareil, nom lisible). Écriture atomique.

### 6.6 Bluetooth : le meilleur codec

- Quand une carte `bluez` apparaît, ou passe sur un profil A2DP, le service choisit le
  meilleur profil A2DP disponible, dans cet ordre : LDAC, aptX HD, aptX, AAC, SBC-XQ,
  SBC.
- Il **ne touche jamais** à une carte en profil appel (HFP/HSP) ni en `off`.
- Il ne change de profil qu'une fois par connexion. Si Charles remet ensuite un autre
  profil à la main, Diapason ne revient pas dessus pendant cette connexion.
- Réglage par appareil : `codec = "auto" | "<nom de codec>"` dans `appareils.toml`.
  Il sert si un codec hache sur un appareil donné.

### 6.7 API D-Bus, commande et indicateur

- **D-Bus de session** : nom `io.github.mawena.Diapason`, objet
  `/io/github/mawena/Diapason`, implémenté avec `Gio` :
  - méthodes : `Etat()`, `Humeurs()`, `ChoisirHumeur(nom)`, `Desactiver()`,
    `Reactiver()` ;
  - signal : `EtatChange` (appareil, type, humeur, actif).

  L'indicateur et la commande passent tous les deux par cette API.
- **Commande** `diapason` (sous-commandes en français, comme `ccs` et `gagarine`) :
  - `diapason` ou `diapason etat` : appareil, type, humeur, codec ;
  - `diapason humeurs` : liste des humeurs de l'appareil actuel ;
  - `diapason humeur <nom>` : choisit l'humeur, sans accents obligatoires
    (`fete` = `fête`) ;
  - `diapason pause` et `diapason reprise` : désactivent ou réactivent Diapason ;
  - `diapason appareils` : appareils connus et leur humeur.
- **Indicateur** : icône symbolique d'un diapason. Son menu affiche :
  - l'appareil actuel, en titre grisé ;
  - les humeurs en boutons radio, l'humeur active cochée ;
  - « Son d'origine » (pause) ;
  - « À propos ».

  Il se met à jour par le signal `EtatChange`. Si le service ne répond pas, il
  affiche « Diapason arrêté ».

### 6.8 Robustesse

- **Si le service s'arrête** (y compris en plantage), le processus filtre est arrêté
  avec lui. La sortie virtuelle disparaît, et WirePlumber revient sur un appareil
  réel. Le constructeur vérifie qu'aucune sortie fantôme ne reste. Le service
  systemd redémarre en cas d'échec, avec une limite de redémarrages.
- **Si le processus filtre meurt seul**, le service le relance une fois, puis passe
  en pause et prévient par une notification.
- **À l'arrêt propre** et à la désinstallation, la sortie réelle redevient la sortie
  par défaut avant l'arrêt du filtre.
- **Journal** : `journalctl --user -u diapason`.

### 6.9 Paquet et publication

- Paquet `.deb` construit avec debhelper 13. Le modèle à suivre est Gagarine
  (`~/Work/perso/Gagarine` : `debian/`, `scripts/build-deb.sh`,
  `scripts/publier-apt.sh`, `data/apt/`, `site/`, cibles `make deb` et `make apt`).
- **Dépendances** : `python3 (>= 3.11)`, `python3-gi`, `pipewire (>= 1.0)`,
  `wireplumber`, `pulseaudio-utils` (pour `pactl`), `pipewire-bin` (pour `pw-cli`,
  `pw-dump`), `gir1.2-ayatanaappindicator3-0.1`, `gir1.2-gtk-3.0`, `libnotify-bin`.
- **Le paquet installe** :
  - l'unité systemd utilisateur `diapason.service`, activée pour tous les
    utilisateurs ;
  - le démarrage automatique de l'indicateur (`/etc/xdg/autostart`) ;
  - les profils dans `/usr/share/diapason/profils/` ;
  - la page de manuel `diapason(1)` ;
  - l'icône ;
  - la source APT deb822 `/etc/apt/sources.list.d/diapason.sources` et la clé
    `/usr/share/keyrings/diapason.gpg`.
- **Dépôt APT** : `https://mawena.github.io/Diapason/apt` (branche `gh-pages`). Clé
  « Diapason APT (mawena) » ed25519 sans phrase de passe, empreinte notée dans
  `data/apt/LISEZMOI`. Index `binary-all` et `binary-amd64`, `InRelease` et
  `Release.gpg`, anciennes versions gardées dans `pool/`. La page d'accueil, avec le
  script `installer.sh`, est servie depuis `site/`.
- **Publication** : README avec le site et la section Installation (apt) en tête,
  « About » GitHub avec le site github.io, release GitHub avec le `.deb` et
  `SHA256SUMS`.

## 7. Contraintes

- Ubuntu 24.04 : PipeWire 1.0.5, WirePlumber 0.4.17, Python 3.12, `pactl` 16.1
  (sortie JSON disponible).
- Le `filter-chain` n'a pas LV2 : seulement les filtres intégrés.
- Ubuntu fait déjà tourner son propre `pipewire -c filter-chain.conf` (service
  `filter-chain.service` de l'utilisateur). Diapason ne le touche pas et n'écrit rien
  dans `~/.config/pipewire/`.
- **Ressources du poste** : tout ce qui calcule (tests, `make deb`) passe par la file
  Gagarine (`gagarine file "<nom>" <Go> <cœurs> -- <commande>`), en annonçant la vraie
  RAM.
- **Git flow** : branches `feature/*` partant de `develop`, commits conventionnels en
  français, signés du seul nom de Charles, sans ligne `Co-Authored-By`.
- Documentation et textes de l'interface en français.

## 8. Tests

- **Tests unitaires** (`unittest`, sans PipeWire) :
  - lecture et fusion des profils ;
  - règle anti-saturation sur chaque humeur livrée (réponse calculée des biquads,
    formules RBJ du « Audio EQ Cookbook », celles de PipeWire) ;
  - classement des appareils à partir de vrais `pactl -f json` et `pw-dump`
    enregistrés comme exemples (ceux du poste de Charles) ;
  - choix du codec ;
  - génération de la configuration du filtre ;
  - analyse des sous-commandes.
- **Essais réels sur le poste**, chacun lancé à la main et décrit dans
  `docs/essais.md` :
  - changer d'humeur sans coupure ;
  - passer de l'enceinte aux haut-parleurs et inversement ;
  - brancher et débrancher un casque sur la prise ;
  - couper et reconnecter le Bluetooth ;
  - tuer le service (le son doit revenir) ;
  - désinstaller le paquet (le son doit revenir) ;
  - mesurer la RAM et le processeur.

## 9. Ce qui reste au constructeur, et ce qui demande Charles

- **Au constructeur** :
  - la façon de rediriger le filtre (§ 6.2) et de lire les événements ;
  - le découpage des modules ;
  - la mise en page du menu ;
  - le dessin de l'icône ;
  - les textes de la page de manuel.
- **Avec Charles, à l'oreille** : les valeurs des humeurs `haut-parleurs-pc`. Il y
  aura un essai jetable comme pour l'enceinte, puis Charles valide. Cette tâche
  bloque la release, pas le reste.
- **Essai de Charles** sur le paquet installé, avant la release 0.1.0.
