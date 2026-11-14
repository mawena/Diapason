"""Configuration `filter-chain` pour `pipewire -c` et paramètres à poser à chaud (`pw-cli`)."""

import math
import re

from .appareils import Sortie
from .profils import CONTROLES, FILTRES, Humeur, Profil

NOEUD = "diapason"
NOEUD_SORTIE = "diapason.sortie"
_NOM = re.compile(r"[a-z0-9_]+")


def _chaine(texte: str) -> str:
    """Chaîne entre guillemets doubles : `\\` et `"` échappés, retour à la ligne remplacé par une espace."""
    texte = texte.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return '"' + texte.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _nombre(valeur) -> str:
    x = float(valeur)
    if not math.isfinite(x):
        raise ValueError(f"valeur de réglage non finie : {valeur!r}")
    texte = f"{x:.6f}".rstrip("0")
    return texte + "0" if texte.endswith(".") else texte


def _verifier(profil: Profil, humeur: Humeur) -> None:
    """Lève ValueError si la chaîne ou les réglages ne peuvent pas être écrits sans risque."""
    for nom, filtre in profil.chaine:
        if not _NOM.fullmatch(nom):
            raise ValueError(f"nom de filtre invalide « {nom} » : seuls a-z, 0-9 et _ sont permis")
        if filtre not in FILTRES:
            raise ValueError(f"filtre inconnu « {filtre} » pour « {nom} »")
        reglage = humeur.reglages.get(nom)
        if reglage is None:
            raise ValueError(f"l'humeur « {humeur.id} » n'a pas de réglage pour le filtre « {nom} »")
        for controle in CONTROLES:
            if controle not in reglage:
                raise ValueError(f"réglage « {nom}:{controle} » absent de l'humeur « {humeur.id} »")


def parametres(profil: Profil, humeur: Humeur) -> dict[str, float]:
    """Clés « <nom>:<Freq|Q|Gain> », dans l'ordre de la chaîne."""
    _verifier(profil, humeur)
    resultat = {}
    for nom, _filtre in profil.chaine:
        for controle in CONTROLES:
            valeur = float(humeur.reglages[nom][controle])
            if not math.isfinite(valeur):
                raise ValueError(f"valeur de réglage non finie : {nom}:{controle}")
            resultat[f"{nom}:{controle}"] = valeur
    return resultat


def texte_conf(sortie: Sortie, profil: Profil, humeur: Humeur) -> str:
    _verifier(profil, humeur)
    noeuds = []
    for nom, filtre in profil.chaine:
        reglage = humeur.reglages[nom]
        controle = " ".join(f'"{c}" = {_nombre(reglage[c])}' for c in CONTROLES)
        noeuds.append(f"                    {{ type = builtin name = {nom} label = {filtre} control = {{ {controle} }} }}")
    liens = [
        f'                    {{ output = "{a[0]}:Out" input = "{b[0]}:In" }}'
        for a, b in zip(profil.chaine, profil.chaine[1:])
    ]
    return f"""# Généré par Diapason : ne pas modifier à la main.
context.properties = {{ log.level = 0 }}
context.spa-libs = {{
    audio.convert.* = audioconvert/libspa-audioconvert
    support.*       = support/libspa-support
}}
context.modules = [
    {{ name = libpipewire-module-rt args = {{ }} flags = [ ifexists nofail ] }}
    {{ name = libpipewire-module-protocol-native }}
    {{ name = libpipewire-module-client-node }}
    {{ name = libpipewire-module-adapter }}
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = {_chaine(f"{sortie.nom} · Diapason")}
            media.name = {_chaine("Diapason")}
            filter.graph = {{
                nodes = [
{chr(10).join(noeuds)}
                ]
                links = [
{chr(10).join(liens)}
                ]
            }}
            audio.channels = 2
            audio.position = [ FL FR ]
            capture.props = {{
                node.name = {_chaine(NOEUD)}
                media.class = Audio/Sink
            }}
            playback.props = {{
                node.name = {_chaine(NOEUD_SORTIE)}
                node.passive = true
                target.object = {_chaine(sortie.noeud)}
                node.dont-reconnect = true
            }}
        }}
    }}
]
"""
