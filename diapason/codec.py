"""Choix du meilleur profil Bluetooth A2DP, sans jamais toucher au mode appel.

Le moteur appelle `profil_a2dp_ideal` une fois par connexion. Les profils
d'appel (`headset-head-unit*`) et `off` ne sont jamais modifiés.
"""

# Ordre de préférence des codecs A2DP, du meilleur au moins bon.
PREFERENCE = ("ldac", "aptx_hd", "aptx", "aac", "sbc_xq")

_NOMS = {
    "a2dp-sink": "SBC",
    "a2dp-sink-sbc_xq": "SBC-XQ",
    "a2dp-sink-aptx_hd": "aptX HD",
    "a2dp-sink-aptx": "aptX",
    "a2dp-sink-aac": "AAC",
    "a2dp-sink-ldac": "LDAC",
}


def profil_a2dp_ideal(profils: tuple[str, ...], actif: str | None,
                      force: str | None = None) -> str | None:
    """Renvoie le profil A2DP à poser, ou `None` s'il n'y a rien à faire.

    `profils` : profils proposés par l'appareil ; `actif` : profil courant ;
    `force` : `"sbc"` (profil `a2dp-sink`) ou un nom de `PREFERENCE` imposé.
    """
    if actif is None or not actif.startswith("a2dp-sink"):
        return None
    if force is not None:
        cible = "a2dp-sink" if force == "sbc" else f"a2dp-sink-{force}"
        if cible not in profils:
            return None
    else:
        cible = next((f"a2dp-sink-{codec}" for codec in PREFERENCE
                      if f"a2dp-sink-{codec}" in profils), None)
        if cible is None and "a2dp-sink" in profils:
            cible = "a2dp-sink"
    if cible is None or cible == actif:
        return None
    return cible


def nom_codec(profil: str | None) -> str:
    """Nom lisible du codec d'un profil A2DP, `—` pour tout autre profil."""
    return _NOMS.get(profil, "—")
