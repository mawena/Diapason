"""Processus enfant `pipewire -c <conf>` qui porte le filtre."""

import ctypes
import os
import signal
import subprocess
from pathlib import Path


def _mourir_avec_le_pere():
    # PR_SET_PDEATHSIG = 1 : SIGTERM à l'enfant quand le service disparaît.
    ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGTERM)


class ProcessusFiltre:
    def __init__(self, dossier: Path | None = None, lancer=None,
                 programme: tuple[str, ...] = ("pipewire",)):
        if dossier is None:
            dossier = Path(os.environ["XDG_RUNTIME_DIR"]) / "diapason"
        self.dossier = Path(dossier)
        self._lancer = lancer or subprocess.Popen
        self._programme = programme
        self._processus = None

    def demarrer(self, conf: str) -> None:
        self.arreter()
        self.dossier.mkdir(parents=True, exist_ok=True)
        chemin = (self.dossier / "filtre.conf").resolve()
        chemin.write_text(conf)
        self._processus = self._lancer(
            [*self._programme, "-c", str(chemin)],
            preexec_fn=_mourir_avec_le_pere)

    def arreter(self, delai: float = 2.0) -> None:
        p, self._processus = self._processus, None
        if p is None or p.poll() is not None:
            return
        p.send_signal(signal.SIGTERM)
        try:
            p.wait(timeout=delai)
        except subprocess.TimeoutExpired:
            p.send_signal(signal.SIGKILL)
            p.wait()

    @property
    def vivant(self) -> bool:
        return self._processus is not None and self._processus.poll() is None

    @property
    def pid(self) -> int | None:
        return self._processus.pid if self.vivant else None
