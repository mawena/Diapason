"""Tests du choix du codec Bluetooth A2DP (tâche 4)."""

import unittest

from diapason.codec import PREFERENCE, nom_codec, profil_a2dp_ideal

P = ("off", "headset-head-unit", "a2dp-sink", "a2dp-sink-sbc_xq",
     "headset-head-unit-cvsd", "headset-head-unit-msbc")


class ChoixProfilA2dp(unittest.TestCase):

    def test_enceinte_de_charles(self):
        self.assertEqual(profil_a2dp_ideal(P, "a2dp-sink"), "a2dp-sink-sbc_xq")

    def test_deja_au_mieux(self):
        self.assertIsNone(profil_a2dp_ideal(P, "a2dp-sink-sbc_xq"))

    def test_profil_appel_intouche(self):
        self.assertIsNone(profil_a2dp_ideal(P, "headset-head-unit-msbc"))
        self.assertIsNone(profil_a2dp_ideal(P, "off"))

    def test_ldac_prefere(self):
        self.assertEqual(
            profil_a2dp_ideal(P + ("a2dp-sink-ldac", "a2dp-sink-aac"), "a2dp-sink"),
            "a2dp-sink-ldac")

    def test_force_sbc(self):
        self.assertEqual(profil_a2dp_ideal(P, "a2dp-sink-sbc_xq", force="sbc"), "a2dp-sink")

    def test_force_absent(self):
        self.assertIsNone(profil_a2dp_ideal(P, "a2dp-sink-sbc_xq", force="ldac"))

    def test_nom_codec(self):
        self.assertEqual([nom_codec(x) for x in ("a2dp-sink-sbc_xq", "a2dp-sink", None)],
                         ["SBC-XQ", "SBC", "—"])

    def test_aucun_profil_a2dp_disponible(self):
        self.assertIsNone(profil_a2dp_ideal(("off", "headset-head-unit"), "a2dp-sink"))

    def test_ordre_de_preference(self):
        self.assertEqual(PREFERENCE, ("ldac", "aptx_hd", "aptx", "aac", "sbc_xq"))
        self.assertEqual(
            profil_a2dp_ideal(P + ("a2dp-sink-aptx", "a2dp-sink-aptx_hd"), "a2dp-sink"),
            "a2dp-sink-aptx_hd")

    def test_noms_des_autres_codecs(self):
        self.assertEqual(
            [nom_codec(x) for x in ("a2dp-sink-ldac", "a2dp-sink-aptx_hd",
                                    "a2dp-sink-aptx", "a2dp-sink-aac",
                                    "headset-head-unit-msbc")],
            ["LDAC", "aptX HD", "aptX", "AAC", "—"])


if __name__ == "__main__":
    unittest.main()
