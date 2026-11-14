import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path

from diapason.filtre import ProcessusFiltre


class FauxPopen:
    def __init__(self, commande, **kw):
        self.commande = commande
        self.kw = kw
        self.pid = 4242
        self.signaux = []
        self.code = None

    def poll(self):
        return self.code

    def send_signal(self, sig):
        self.signaux.append(sig)
        self.code = -sig

    def wait(self, timeout=None):
        return self.code


class TestFiltre(unittest.TestCase):
    def test_demarrer_ecrit_la_conf(self):
        with tempfile.TemporaryDirectory() as tmp:
            appels = []

            def lancer(cmd, **kw):
                p = FauxPopen(cmd, **kw)
                appels.append(p)
                return p

            f = ProcessusFiltre(Path(tmp), lancer)
            f.demarrer("context.modules = []\n")
            conf = Path(tmp) / "filtre.conf"
            self.assertEqual(conf.read_text(), "context.modules = []\n")
            self.assertEqual(appels[0].commande, ["pipewire", "-c", str(conf)])
            self.assertTrue(callable(appels[0].kw["preexec_fn"]))
            self.assertTrue(f.vivant)
            self.assertEqual(f.pid, 4242)
            f.arreter()
            self.assertEqual(appels[0].signaux, [signal.SIGTERM])
            self.assertFalse(f.vivant)
            self.assertIsNone(f.pid)

    def test_demarrer_deux_fois_arrete_le_premier(self):
        with tempfile.TemporaryDirectory() as tmp:
            appels = []

            def lancer(cmd, **kw):
                p = FauxPopen(cmd, **kw)
                p.pid = 100 + len(appels)
                appels.append(p)
                return p

            f = ProcessusFiltre(Path(tmp), lancer)
            f.demarrer("a\n")
            f.demarrer("b\n")
            self.assertEqual(appels[0].signaux, [signal.SIGTERM])
            self.assertEqual(appels[1].signaux, [])
            self.assertEqual(f.pid, 101)
            self.assertEqual((Path(tmp) / "filtre.conf").read_text(), "b\n")
            f.arreter()

    def test_arreter_sans_processus(self):
        f = ProcessusFiltre(Path("/tmp/inutile"), lambda *a, **k: None)
        f.arreter()
        self.assertFalse(f.vivant)
        self.assertIsNone(f.pid)

    def test_dossier_par_defaut(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/run/user/1"}):
            self.assertEqual(ProcessusFiltre().dossier, Path("/run/user/1/diapason"))

    def test_vrai_processus(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = ProcessusFiltre(
                Path(tmp),
                programme=(sys.executable, "-c", "import time; time.sleep(30)"))
            f.demarrer("x\n")
            try:
                self.assertTrue(f.vivant)
            finally:
                debut = time.monotonic()
                f.arreter()
            self.assertFalse(f.vivant)
            self.assertLess(time.monotonic() - debut, 3)


if __name__ == "__main__":
    unittest.main()
