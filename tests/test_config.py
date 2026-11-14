import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from diapason.config import Forcage, lire_forcages


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.chemin = Path(self.dossier.name) / "appareils.toml"

    def ecrire(self, texte):
        self.chemin.write_text(texte, encoding="utf-8")

    def test_forcage_lu(self):
        self.ecrire('["bluez:AA:BB:CC:DD:EE:02"]\ntype = "casque"\ncodec = "sbc"\n')
        self.assertEqual(
            lire_forcages(self.chemin),
            {"bluez:AA:BB:CC:DD:EE:02": Forcage("casque", "sbc")},
        )

    def test_type_inconnu_ignore(self):
        self.ecrire('["bluez:X"]\ntype = "frigo"\ncodec = "ldac"\n')
        with self.assertLogs("diapason.config", level="WARNING"):
            forcages = lire_forcages(self.chemin)
        self.assertEqual(forcages, {"bluez:X": Forcage(None, "ldac")})

    def test_codec_inconnu_ignore(self):
        self.ecrire('["bluez:X"]\ntype = "hdmi"\ncodec = "mp3"\n')
        with self.assertLogs("diapason.config", level="WARNING"):
            forcages = lire_forcages(self.chemin)
        self.assertEqual(forcages, {"bluez:X": Forcage("hdmi", None)})

    def test_fichier_absent(self):
        with self.assertLogs("diapason.config", level="INFO"):
            self.assertEqual(lire_forcages(self.chemin), {})

    def test_fichier_invalide(self):
        self.ecrire("[pas du toml")
        with self.assertLogs("diapason.config", level="WARNING"):
            self.assertEqual(lire_forcages(self.chemin), {})

    def test_table_non_table_ignoree(self):
        self.ecrire('rien = 3\n["bluez:X"]\ntype = "casque"\n')
        with self.assertLogs("diapason.config", level="WARNING"):
            forcages = lire_forcages(self.chemin)
        self.assertEqual(forcages, {"bluez:X": Forcage("casque", None)})

    def test_chemin_par_defaut(self):
        (Path(self.dossier.name) / "diapason").mkdir()
        (Path(self.dossier.name) / "diapason" / "appareils.toml").write_text(
            '["alsa:Y"]\ntype = "hdmi"\n', encoding="utf-8")
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self.dossier.name}):
            self.assertEqual(lire_forcages(), {"alsa:Y": Forcage("hdmi", None)})


if __name__ == "__main__":
    unittest.main()
