"""Tests du calcul des biquads, identique à PipeWire 1.0.5."""

import json
import unittest
from pathlib import Path

from diapason.biquad import coefficients, gain_max_db, reponse_db

EXEMPLE = json.loads(
    (Path(__file__).parent / "exemples" / "coefficients-pipewire.json").read_text(encoding="utf-8")
)


class TestCoefficients(unittest.TestCase):
    def test_identiques_a_pipewire(self):
        self.assertEqual(len(EXEMPLE["filtres"]), 6)
        for f in EXEMPLE["filtres"]:
            with self.subTest(filtre=f["nom"]):
                calcules = coefficients(f["filtre"], f["Freq"], f["Q"], f["Gain"], EXEMPLE["taux"])
                attendus = (f["b0"], f["b1"], f["b2"], f["a1"], f["a2"])
                for calc, attendu in zip(calcules, attendus):
                    self.assertAlmostEqual(calc, attendu, delta=1e-5)

    def test_etagere_a_zero_est_un_gain(self):
        self.assertAlmostEqual(coefficients("bq_highshelf", 0.0, 1.0, -6.0)[0], 10 ** (-6 / 20), places=9)

    def test_etagere_ignore_q(self):
        self.assertEqual(coefficients("bq_lowshelf", 100, 0.3, 4), coefficients("bq_lowshelf", 100, 2.0, 4))

    def test_filtre_inconnu(self):
        with self.assertRaises(ValueError):
            coefficients("bq_notch", 100, 1, 0)


class TestReponse(unittest.TestCase):
    def test_pic_a_sa_frequence(self):
        self.assertAlmostEqual(reponse_db([("bq_peaking", {"Freq": 1000, "Q": 1, "Gain": 6})], 1000), 6.0, places=2)

    def test_passe_haut_coupe(self):
        self.assertLess(reponse_db([("bq_highpass", {"Freq": 50, "Q": 0.707, "Gain": 0})], 20), -12)

    def test_gain_max_chaine_plate(self):
        self.assertAlmostEqual(gain_max_db([("bq_highshelf", {"Freq": 0, "Q": 1, "Gain": -3})]), -3.0, places=6)


if __name__ == "__main__":
    unittest.main()
