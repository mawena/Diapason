"""Forçages de l'utilisateur par appareil (`~/.config/diapason/appareils.toml`)."""

import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from diapason.appareils import TYPES
from diapason.codec import PREFERENCE

journal = logging.getLogger(__name__)

CODECS = ("sbc",) + PREFERENCE


@dataclass(frozen=True)
class Forcage:
    type: str | None = None
    codec: str | None = None


def chemin_par_defaut() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "diapason" / "appareils.toml"


def lire_forcages(chemin: Path | None = None) -> dict[str, Forcage]:
    """Lit les forçages par identité ; `{}` si le fichier est absent ou invalide."""
    chemin = chemin or chemin_par_defaut()
    try:
        with open(chemin, "rb") as f:
            donnees = tomllib.load(f)
    except FileNotFoundError:
        journal.info("Aucun fichier de forçages : %s", chemin)
        return {}
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as erreur:
        journal.warning("Fichier de forçages illisible (%s) : %s", chemin, erreur)
        return {}

    forcages = {}
    for identite, table in donnees.items():
        if not isinstance(table, dict):
            journal.warning("Forçage ignoré pour %r : ce n'est pas une table", identite)
            continue
        type_ = table.get("type")
        if type_ is not None and type_ not in TYPES:
            journal.warning("Type inconnu ignoré pour %r : %r", identite, type_)
            type_ = None
        codec = table.get("codec")
        if codec is not None and codec not in CODECS:
            journal.warning("Codec inconnu ignoré pour %r : %r", identite, codec)
            codec = None
        forcages[identite] = Forcage(type_, codec)
    return forcages
