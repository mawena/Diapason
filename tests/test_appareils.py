import copy
import json
import unittest
from pathlib import Path

from diapason.appareils import Carte, lire_cartes, lire_sorties, sortie_par_defaut

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

    def test_objets_malformes_ignores(self):
        bizarres = [
            {"type": "PipeWire:Interface:Node", "info": None},
            {"type": "PipeWire:Interface:Node", "info": {"props": None}},
            {"type": "PipeWire:Interface:Device"},
            {"type": "PipeWire:Interface:Device", "info": {"props": {"device.name": "x"}, "params": None}},
            {"type": "PipeWire:Interface:Metadata", "props": {"metadata.name": "default"}, "metadata": None},
            {"type": "PipeWire:Interface:Metadata", "props": None, "metadata": [None, {"key": "default.audio.sink", "value": None}]},
            None,
            "texte",
        ]
        dump = bizarres + copy.deepcopy(DUMP)
        self.assertEqual(lire_sorties(dump), lire_sorties(DUMP))
        cartes = lire_cartes(dump)
        # La carte « x » aux params nuls est gardée, avec des champs de repli.
        self.assertEqual(cartes.pop("x"), Carte("x", False, None, (), None))
        self.assertEqual(cartes, lire_cartes(DUMP))
        self.assertEqual(sortie_par_defaut(dump), "diapason_essai_bt")
        self.assertIsNone(sortie_par_defaut(bizarres))

    def test_route_et_profils_malformes(self):
        dump = copy.deepcopy(DUMP)
        for o in dump:
            if o.get("info", {}).get("props", {}).get("device.name", "").startswith("alsa_card.pci"):
                o["info"]["params"]["Route"] = [None, {"direction": "Output"}]
                o["info"]["params"]["Profile"] = [{}]
                o["info"]["params"]["EnumProfile"] = [None, {"name": "HiFi"}]
        s = lire_sorties(dump)[HAUT_PARLEURS]
        self.assertEqual(s.type, "autre")
        c = lire_cartes(dump)["alsa_card.pci-0000_00_1f.3-platform-skl_hda_dsp_generic"]
        self.assertEqual((c.profils, c.actif), (("HiFi",), None))

    def test_exclusion_prefixe_diapason(self):
        dump = copy.deepcopy(DUMP)
        for o in dump:
            if o.get("info", {}).get("props", {}).get("node.name") == HAUT_PARLEURS:
                o["info"]["props"]["node.name"] = "diapason"
        self.assertNotIn("diapason", lire_sorties(dump))
        self.assertEqual(len(lire_sorties(dump)), len(lire_sorties(DUMP)) - 1)

    def test_canaux_repli(self):
        def canaux(**props):
            dump = copy.deepcopy(DUMP)
            for o in dump:
                p = o.get("info", {}).get("props", {})
                if p.get("node.name") == HAUT_PARLEURS:
                    p.pop("audio.channels", None)
                    p.pop("audio.position", None)
                    p.update(props)
            return lire_sorties(dump)[HAUT_PARLEURS].canaux
        self.assertEqual(canaux(**{"audio.position": "FL,FR,FC,LFE"}), 4)
        self.assertEqual(canaux(**{"audio.position": "[ FL FR FC ]"}), 3)
        self.assertEqual(canaux(), 2)
        self.assertEqual(canaux(**{"audio.channels": 6}), 6)
        self.assertEqual(canaux(**{"audio.channels": "abc", "audio.position": "FL,FR,FC"}), 3)
        self.assertEqual(canaux(**{"audio.channels": 0}), 2)
        self.assertEqual(canaux(**{"audio.channels": "-1"}), 2)

    def test_bluetooth_sans_adresse(self):
        dump = copy.deepcopy(DUMP)
        for o in dump:
            p = o.get("info", {}).get("props", {})
            if p.get("device.name") == "bluez_card.AA_BB_CC_DD_EE_02":
                del p["api.bluez5.address"]
        self.assertIsNone(lire_cartes(dump)["bluez_card.AA_BB_CC_DD_EE_02"].identite)
        s = lire_sorties(dump)["bluez_output.AA_BB_CC_DD_EE_02.1"]
        self.assertEqual(s.identite, "bluez_card.AA_BB_CC_DD_EE_02:bluez_output.AA_BB_CC_DD_EE_02.1")


if __name__ == "__main__":
    unittest.main()
