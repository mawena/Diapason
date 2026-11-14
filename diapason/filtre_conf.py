"""Configuration `filter-chain` pour `pipewire -c` et paramètres à poser à chaud (`pw-cli`)."""

import math

from .appareils import Sortie
from .profils import CONTROLES, Humeur, Profil

NOEUD = "diapason"
NOEUD_SORTIE = "diapason.sortie"


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


def _controles(filtre: str) -> tuple[str, ...]:
    # Le passe-haut de PipeWire n'a pas de port « Gain » (seulement Freq et Q).
    return tuple(c for c in CONTROLES if not (filtre == "bq_highpass" and c == "Gain"))


def parametres(profil: Profil, humeur: Humeur) -> dict[str, float]:
    """Clés « <nom>:<Freq|Q|Gain> », dans l'ordre de la chaîne."""
    resultat = {}
    for nom, _filtre in profil.chaine:
        for controle in CONTROLES:
            valeur = float(humeur.reglages[nom][controle])
            if not math.isfinite(valeur):
                raise ValueError(f"valeur de réglage non finie : {nom}:{controle}")
            resultat[f"{nom}:{controle}"] = valeur
    return resultat


def texte_conf(sortie: Sortie, profil: Profil, humeur: Humeur) -> str:
    noeuds = []
    for nom, filtre in profil.chaine:
        reglage = humeur.reglages[nom]
        controle = " ".join(f'"{c}" = {_nombre(reglage[c])}' for c in _controles(filtre))
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
