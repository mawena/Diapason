import copy
import json
import unittest
from pathlib import Path

from diapason.appareils import lire_cartes, lire_sorties, sortie_par_defaut

EXEMPLES = Path(__file__).parent / "exemples"
DUMP = json.loads((EXEMPLES / "poste-enceinte-bt.json").read_text(encoding="utf-8"))
DUMP_CASQUE = json.loads((EXEMPLES / "poste-prise-casque.json").read_text(encoding="utf-8"))
HAUT_PARLEURS = "alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__sink"


class TestAppareils(unittest.TestCase):
    def test_enceinte(self):
        s = lire_sorties(DUMP)["bluez_output.AA_BB_CC_DD_EE_02.1"]
        self.assertEqual((s.type, s.nom, s.identite, s.canaux, s.carte),
                         ("enceinte-bluetooth", "LN-1008BT", "bluez:AA:BB:CC:DD:EE:02", 2,
                          "bluez_card.AA_BB_CC_DD_EE_02"))

    def test_haut_parleurs(self):
        s = lire_sorties(DUMP)[HAUT_PARLEURS]
        self.assertEqual((s.type, s.nom, s.identite),
                         ("haut-parleurs-pc", "Haut-parleurs du PC",
                          "alsa_card.pci-0000_00_1f.3-platform-skl_hda_dsp_generic:[Out] Speaker"))

    def test_type_prise_casque(self):
        s = lire_sorties(DUMP_CASQUE)[HAUT_PARLEURS]
        self.assertEqual((s.type, s.nom, s.identite),
                         ("casque", "Prise casque",
                          "alsa_card.pci-0000_00_1f.3-platform-skl_hda_dsp_generic:[Out] Headphones"))

    def test_hdmi_et_dock(self):
        sorties = lire_sorties(DUMP)
        for noeud in ("alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp_3__sink",
                      "alsa_output.usb-DisplayLink_Dell_Universal_Dock_D6000_0000000000-02.iec958-stereo"):
            self.assertEqual(sorties[noeud].type, "hdmi")

    def test_sortie_d_essai_exclue(self):
        self.assertNotIn("diapason_essai_bt", lire_sorties(DUMP))

    def test_defaut(self):
        self.assertEqual(sortie_par_defaut(DUMP), "diapason_essai_bt")

    def test_carte_bluetooth(self):
        c = lire_cartes(DUMP)["bluez_card.AA_BB_CC_DD_EE_02"]
        self.assertEqual(c.identite, "bluez:AA:BB:CC:DD:EE:02")
        self.assertTrue(c.bluetooth)
        self.assertEqual(c.actif, "a2dp-sink-sbc_xq")
        self.assertIn("headset-head-unit", c.profils)

    def test_carte_alsa(self):
        c = lire_cartes(DUMP)["alsa_card.pci-0000_00_1f.3-platform-skl_hda_dsp_generic"]
        self.assertFalse(c.bluetooth)
        self.assertIsNone(c.identite)
        self.assertEqual(c.actif, "HiFi")

    def test_dump_vide(self):
        self.assertEqual((lire_sorties([]), sortie_par_defaut([])), ({}, None))

    def test_nom_accentue_garde(self):
        dump = copy.deepcopy(DUMP)
        for o in dump:
            if o.get("info", {}).get("props", {}).get("device.name") == "bluez_card.AA_BB_CC_DD_EE_02":
                o["info"]["props"]["device.description"] = "Écouteurs"
        self.assertEqual(lire_sorties(dump)["bluez_output.AA_BB_CC_DD_EE_02.1"].nom, "Écouteurs")


if __name__ == "__main__":
    unittest.main()
