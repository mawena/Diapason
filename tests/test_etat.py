import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from diapason.etat import Etat


class TestEtat(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.chemin = Path(self.dossier.name) / "sous" / "etat.json"

    def test_aller_retour(self):
        etat = Etat.charger(self.chemin)
        etat.memoriser("bluez:X", "LN-1008BT", "enceinte-bluetooth", "cocon")
        etat.enregistrer()
        relu = Etat.charger(self.chemin)
        self.assertEqual(relu.humeur("bluez:X"), "cocon")
        appareil = relu.appareils()["bluez:X"]
        self.assertEqual(appareil["nom"], "LN-1008BT")
        self.assertEqual(appareil["type"], "enceinte-bluetooth")
        self.assertIn("vu", appareil)

    def test_humeur_inconnue(self):
        self.assertIsNone(Etat.charger(self.chemin).humeur("absent"))

    def test_pause_retenue(self):
        etat = Etat.charger(self.chemin)
        self.assertFalse(etat.en_pause)
        etat.en_pause = True
        etat.enregistrer()
        self.assertTrue(Etat.charger(self.chemin).en_pause)

    def test_fichier_corrompu(self):
        self.chemin.parent.mkdir(parents=True)
        self.chemin.write_text("{pas du json")
        with self.assertLogs("diapason.etat", level="WARNING"):
            etat = Etat.charger(self.chemin)
        self.assertEqual(etat.appareils(), {})
        self.assertFalse(etat.en_pause)
        self.assertTrue(self.chemin.with_name("etat.json.corrompu").exists())
        self.assertFalse(self.chemin.exists())

    def test_structure_invalide(self):
        self.chemin.parent.mkdir(parents=True)
        self.chemin.write_text(json.dumps([1, 2]))
        with self.assertLogs("diapason.etat", level="WARNING"):
            etat = Etat.charger(self.chemin)
        self.assertEqual(etat.appareils(), {})

    def test_ecriture_atomique(self):
        etat = Etat.charger(self.chemin)
        etat.memoriser("bluez:X", "A", "casque", "voix")
        etat.enregistrer()
        etat.enregistrer()
        self.assertEqual(list(self.chemin.parent.glob("*.tmp")), [])
        self.assertEqual([p.name for p in self.chemin.parent.iterdir()], ["etat.json"])

    def test_chemin_par_defaut(self):
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": self.dossier.name}):
            etat = Etat.charger()
            etat.en_pause = True
            etat.enregistrer()
            self.assertTrue((Path(self.dossier.name) / "diapason" / "etat.json").exists())
            self.assertTrue(Etat.charger().en_pause)


if __name__ == "__main__":
    unittest.main()
