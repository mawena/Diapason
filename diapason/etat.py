"""État retenu : humeur de chaque appareil et pause (`~/.local/state/diapason/etat.json`)."""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

journal = logging.getLogger(__name__)


def chemin_par_defaut() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "diapason" / "etat.json"


class Etat:
    def __init__(self, chemin: Path, appareils: dict[str, dict] | None = None,
                 en_pause: bool = False):
        self._chemin = chemin
        self._appareils = appareils if appareils is not None else {}
        self.en_pause = en_pause

    @classmethod
    def charger(cls, chemin: Path | None = None) -> "Etat":
        chemin = chemin or chemin_par_defaut()
        try:
            donnees = json.loads(chemin.read_text(encoding="utf-8"))
            if not isinstance(donnees, dict):
                raise ValueError("la racine n'est pas un objet")
            appareils = donnees.get("appareils", {})
            if not isinstance(appareils, dict) or not all(
                    isinstance(v, dict) for v in appareils.values()):
                raise ValueError("« appareils » invalide")
            return cls(chemin, appareils, bool(donnees.get("en_pause", False)))
        except FileNotFoundError:
            return cls(chemin)
        except (OSError, ValueError) as erreur:  # JSON invalide inclus (ValueError)
            corrompu = chemin.with_name(chemin.name + ".corrompu")
            journal.warning("État corrompu (%s), renommé en %s : %s", chemin, corrompu, erreur)
            try:
                os.replace(chemin, corrompu)
            except OSError:
                pass
            return cls(chemin)

    def humeur(self, identite: str) -> str | None:
        return self._appareils.get(identite, {}).get("humeur")

    def memoriser(self, identite: str, nom: str, type: str, humeur: str) -> None:
        self._appareils[identite] = {
            "nom": nom,
            "type": type,
            "humeur": humeur,
            "vu": datetime.now().astimezone().isoformat(timespec="seconds"),
        }

    def appareils(self) -> dict[str, dict]:
        return self._appareils

    def enregistrer(self) -> None:
        self._chemin.parent.mkdir(parents=True, exist_ok=True)
        fd, temporaire = tempfile.mkstemp(
            dir=self._chemin.parent, prefix="etat.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"en_pause": self.en_pause, "appareils": self._appareils},
                          f, ensure_ascii=False, indent=2)
                f.write("\n")
            os.replace(temporaire, self._chemin)
        except BaseException:
            Path(temporaire).unlink(missing_ok=True)
            raise
