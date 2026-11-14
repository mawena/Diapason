"""Fine couche sur pactl, pw-cli et pw-dump."""

import json
import os
import re
import subprocess
from dataclasses import dataclass

DELAI = 5


class ErreurPipeWire(Exception):
    """Une commande PipeWire ou PulseAudio a échoué."""


@dataclass(frozen=True)
class Flux:
    index: int
    noeud: str | None
    sortie: str | None


def _executer_reel(args: list[str]) -> str:
    env = {**os.environ, "LC_ALL": "C"}
    try:
        r = subprocess.run(args, capture_output=True, text=True,
                           timeout=DELAI, env=env)
    except (OSError, subprocess.SubprocessError) as e:
        raise ErreurPipeWire(f"{args[0]} : {e}") from e
    if r.returncode != 0:
        raise ErreurPipeWire(
            f"{args[0]} a échoué (code {r.returncode}) : {r.stderr.strip()}")
    return r.stdout


class PipeWire:
    def __init__(self, executer=None):
        self._executer = executer or _executer_reel

    def etat(self) -> list[dict]:
        try:
            return json.loads(self._executer(["pw-dump"]))
        except json.JSONDecodeError as e:
            raise ErreurPipeWire(f"sortie de pw-dump illisible : {e}") from e

    def definir_defaut(self, noeud: str):
        self._executer(["pactl", "set-default-sink", noeud])

    def flux(self) -> list[Flux]:
        try:
            entrees = json.loads(
                self._executer(["pactl", "-f", "json", "list", "sink-inputs"]))
        except json.JSONDecodeError as e:
            raise ErreurPipeWire(f"sortie de pactl illisible : {e}") from e
        noms = {}
        for ligne in self._executer(["pactl", "list", "sinks", "short"]).splitlines():
            champs = ligne.split("\t")
            if len(champs) >= 2 and champs[0].isdigit():
                noms[int(champs[0])] = champs[1]
        return [
            Flux(e["index"],
                 e.get("properties", {}).get("node.name"),
                 noms.get(e.get("sink")))
            for e in entrees
        ]

    def deplacer_flux(self, index: int, vers: str):
        self._executer(["pactl", "move-sink-input", str(index), vers])

    def volume(self, noeud: str) -> float:
        sortie = self._executer(["pactl", "get-sink-volume", noeud])
        pourcents = [int(p) for p in re.findall(r"(\d+)%", sortie)]
        if not pourcents:
            raise ErreurPipeWire(f"volume illisible pour {noeud} : {sortie!r}")
        return sum(pourcents) / len(pourcents) / 100

    def definir_volume(self, noeud: str, v: float):
        self._executer(["pactl", "set-sink-volume", noeud, f"{round(v * 100)}%"])

    def definir_profil(self, carte: str, profil: str):
        self._executer(["pactl", "set-card-profile", carte, profil])

    def _id_noeud(self, noeud: str) -> int | None:
        for objet in self.etat():
            props = objet.get("info", {}).get("props", {})
            if props.get("node.name") == noeud:
                return objet["id"]
        return None

    def noeud_present(self, noeud: str) -> bool:
        return self._id_noeud(noeud) is not None

    def appliquer(self, noeud: str, parametres: dict[str, float]):
        id_noeud = self._id_noeud(noeud)
        if id_noeud is None:
            raise ErreurPipeWire(f"nœud {noeud} absent")
        liste = " ".join(f'"{k}" {float(v)!r}' for k, v in parametres.items())
        self._executer(["pw-cli", "s", str(id_noeud), "Props",
                        f"{{ params = [ {liste} ] }}"])
