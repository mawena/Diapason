"""Catalogue des humeurs : profils livrés, surcharges de l'utilisateur, humeur neutre."""

import os
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .biquad import gain_max_db

DOSSIER_LIVRE = Path("/usr/share/diapason/profils")
CONTROLES = ("Freq", "Q", "Gain")
FILTRES = ("bq_highpass", "bq_lowshelf", "bq_peaking", "bq_highshelf")
IDS_RESERVES = ("desactive", "neutre")
CHAINE_NEUTRE = [("marge", "bq_highshelf")]
FREQ_COUPE_NEUTRE = 5.0
# Le Q d'un bq_highpass de PipeWire est une résonance en dB : à 0,707 il bombe de +0,2 dB
# vers 20 Hz, ce qui dépasserait 0 dB. À 0, la réponse est plate (Butterworth).
Q_COUPE_NEUTRE = 0.0


def dossier_utilisateur() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "diapason" / "profils"


def normaliser_id(texte: str) -> str:
    sans_accents = "".join(c for c in unicodedata.normalize("NFKD", texte) if not unicodedata.combining(c))
    return "".join(sans_accents.lower().split())


@dataclass(frozen=True)
class Humeur:
    id: str
    titre: str
    description: str
    reglages: dict[str, dict[str, float]]

    def chaine_calcul(self, profil: "Profil") -> list[tuple[str, dict]]:
        return [(filtre, dict(self.reglages[nom])) for nom, filtre in profil.chaine]


@dataclass(frozen=True)
class Profil:
    type: str
    nom: str
    humeur_par_defaut: str
    chaine: list[tuple[str, str]]
    humeurs: dict[str, Humeur]


def _neutre(chaine, defaut: Humeur | None) -> Humeur:
    reglages = {}
    for nom, filtre in chaine:
        base = defaut.reglages[nom] if defaut else {"Freq": 0.0, "Q": 1.0, "Gain": 0.0}
        reglages[nom] = {**base, "Gain": 0.0}
        if filtre == "bq_highpass":
            reglages[nom].update(Freq=FREQ_COUPE_NEUTRE, Q=Q_COUPE_NEUTRE)
    return Humeur("neutre", "Neutre", "Son d'origine, filtre à plat", reglages)


def _nombre(valeur) -> bool:
    return isinstance(valeur, (int, float)) and not isinstance(valeur, bool)


def _lire_chaine(brut) -> list[tuple[str, str]]:
    """Lève ValueError si la chaîne n'est pas une liste de paires [nom, filtre] valides."""
    if not isinstance(brut, list) or not brut:
        raise ValueError("« chaine » doit être une liste de paires [nom, filtre]")
    chaine = []
    for paire in brut:
        if not (isinstance(paire, list) and len(paire) == 2 and all(isinstance(x, str) for x in paire)):
            raise ValueError("« chaine » doit être une liste de paires [nom, filtre]")
        if paire[1] not in FILTRES:
            raise ValueError(f"filtre inconnu « {paire[1]} » dans « chaine »")
        chaine.append((paire[0], paire[1]))
    if len({nom for nom, _ in chaine}) != len(chaine):
        raise ValueError("« chaine » a des noms de filtre en double")
    return chaine


def _lire_humeur(identifiant, brut, chaine) -> Humeur:
    """Lève ValueError, en citant l'humeur et le filtre, si un réglage manque."""
    if not isinstance(brut, dict):
        raise ValueError(f"humeur « {identifiant} » : une table est attendue")
    reglages = {}
    for nom, _ in chaine:
        r = brut.get(nom)
        if not isinstance(r, dict) or not all(_nombre(r.get(c)) for c in CONTROLES):
            raise ValueError(f"humeur « {identifiant} » : réglage « {nom} » absent ou incomplet "
                             f"(Freq, Q et Gain attendus)")
        reglages[nom] = {c: float(r[c]) for c in CONTROLES}
    titre, description = brut.get("titre", identifiant), brut.get("description", "")
    return Humeur(identifiant, titre if isinstance(titre, str) else identifiant,
                  description if isinstance(description, str) else "", reglages)


class Catalogue:
    def __init__(self, profils: dict[str, Profil], erreurs: list[str]):
        self._profils = profils
        self._erreurs = erreurs

    @classmethod
    def charger(cls, dossiers: list[Path]) -> "Catalogue":
        meta: dict[str, dict] = {}       # type -> {nom, defaut, chaine}
        humeurs: dict[str, dict[str, Humeur]] = {}
        erreurs: list[str] = []
        for dossier in dossiers:
            if not Path(dossier).is_dir():
                continue
            for fichier in sorted(Path(dossier).glob("*.toml")):
                try:
                    with open(fichier, "rb") as f:
                        brut = tomllib.load(f)
                except (OSError, tomllib.TOMLDecodeError) as e:
                    erreurs.append(f"{fichier.name} : fichier illisible, ignoré ({e})")
                    continue
                cls._integrer(fichier, brut, meta, humeurs, erreurs)
        profils = {}
        for type_, m in meta.items():
            hs = humeurs.get(type_, {})
            if m["defaut"] not in hs and m["defaut"] != "neutre":
                repli = next(iter(sorted(hs)), "neutre")
                erreurs.append(f"{type_} : humeur_par_defaut « {m['defaut']} » inconnue, repli sur « {repli} »")
                m["defaut"] = repli
            hs["neutre"] = _neutre(m["chaine"], hs.get(m["defaut"]) or next(iter(hs.values()), None))
            profils[type_] = Profil(type_, m["nom"], m["defaut"], m["chaine"], dict(sorted(hs.items())))
        return cls(profils, erreurs)

    @staticmethod
    def _integrer(fichier, brut, meta, humeurs, erreurs):
        nom_f = fichier.name
        type_ = brut.get("type", fichier.stem)
        if not isinstance(type_, str):
            erreurs.append(f"{nom_f} : « type » doit être un texte, fichier ignoré")
            return
        chaine_brute = brut.get("chaine")
        if type_ in meta:
            m = meta[type_]
            if chaine_brute is not None:
                try:
                    changee = _lire_chaine(chaine_brute) != m["chaine"]
                except ValueError:
                    changee = True
                if changee:
                    erreurs.append(f"{nom_f} : la clé « chaine » ne peut pas être changée, chaîne livrée gardée")
        else:
            try:
                chaine = _lire_chaine(chaine_brute)
            except ValueError as e:
                erreurs.append(f"{nom_f} : {e}, fichier ignoré")
                return
            m = meta[type_] = {"nom": type_, "defaut": "neutre", "chaine": chaine}
            humeurs[type_] = {}
        if isinstance(brut.get("nom"), str):
            m["nom"] = brut["nom"]
        if "humeur_par_defaut" in brut:
            if isinstance(brut["humeur_par_defaut"], str):
                m["defaut"] = normaliser_id(brut["humeur_par_defaut"])
            else:
                erreurs.append(f"{nom_f} : « humeur_par_defaut » doit être un texte, ignoré")
        brutes = brut.get("humeurs", {})
        if not isinstance(brutes, dict):
            erreurs.append(f"{nom_f} : « humeurs » doit être une table, ignoré")
            return
        for cle, h in brutes.items():
            identifiant = normaliser_id(cle)
            if identifiant in IDS_RESERVES:
                erreurs.append(f"{nom_f} : humeur « {identifiant} » : id réservé, humeur ignorée")
                continue
            try:
                humeurs[type_][identifiant] = _lire_humeur(identifiant, h, m["chaine"])
            except ValueError as e:
                erreurs.append(f"{nom_f} : {e}, humeur ignorée")

    def profil(self, type: str) -> Profil:
        if type in self._profils:
            return self._profils[type]
        neutre = _neutre(CHAINE_NEUTRE, None)
        return Profil(type, type, "neutre", list(CHAINE_NEUTRE), {"neutre": neutre})

    def verifier(self) -> list[str]:
        messages = list(self._erreurs)
        for p in self._profils.values():
            for h in p.humeurs.values():
                gain = gain_max_db(h.chaine_calcul(p))
                if gain > 1e-6:
                    messages.append(f"{p.type}/{h.id} : gain maximal {gain:+.2f} dB, "
                                    f"risque de saturation (baisser la marge)")
        return messages
