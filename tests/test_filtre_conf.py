import re
from dataclasses import replace
import unittest
from pathlib import Path

from diapason.appareils import Sortie
from diapason.filtre_conf import NOEUD, NOEUD_SORTIE, parametres, texte_conf
from diapason.profils import Catalogue

DATA = Path(__file__).resolve().parent.parent / "data" / "profils"
ENCEINTE = Sortie("bluez_output.AA_BB_CC_DD_EE_02.1", "LN-1008BT", "AA:BB:CC:DD:EE:02", "enceinte-bluetooth", 2, None)
profil_enceinte = Catalogue.charger([DATA]).profil("enceinte-bluetooth")


def bloc(texte, debut):
    """Contenu du bloc `{ ... }` qui suit `debut = {`."""
    i = texte.index(debut + " = {") + len(debut) + 4
    profondeur, j = 1, i
    while profondeur:
        profondeur += {"{": 1, "}": -1}.get(texte[j], 0)
        j += 1
    return texte[i:j - 1]


class TestFiltreConf(unittest.TestCase):
    def verifier_structure(self, t):
        capture, lecture = bloc(t, "capture.props"), bloc(t, "playback.props")
        for attendu in ('node.name = "diapason"', "media.class = Audio/Sink"):
            self.assertIn(attendu, capture)
        for attendu in ('node.name = "diapason.sortie"', "node.passive = true",
                        'target.object = "bluez_output.AA_BB_CC_DD_EE_02.1"', "node.dont-reconnect = true"):
            self.assertIn(attendu, lecture)
            self.assertNotIn(attendu, capture)
        self.assertNotIn("target.object", capture)
        noeuds = re.findall(r"name = (\w+) label = (\w+) control = \{ ([^}]*) \}", t)
        self.assertEqual([n for n, _, _ in noeuds], [n for n, _ in profil_enceinte.chaine])
        for nom, _, controle in noeuds:
            self.assertEqual(re.findall(r'"(\w+)" =', controle), ["Freq", "Q", "Gain"], nom)
        declares = {n for n, _, _ in noeuds}
        liens = re.findall(r'output = "([^"]*)" input = "([^"]*)"', t)
        self.assertEqual(len(liens), len(noeuds) - 1)
        for sortie, entree in liens:
            self.assertIn(sortie.rsplit(":", 1)[0], declares)
            self.assertIn(entree.rsplit(":", 1)[0], declares)

    def test_nom_de_noeud_invalide_refuse(self):
        h = profil_enceinte.humeurs["cocon"]
        for mauvais in ("a b", 'a"b', "a}b", "Marge", ""):
            profil = replace(profil_enceinte, chaine=[(mauvais, "bq_highshelf")])
            humeur = replace(h, reglages={mauvais: h.reglages["marge"]})
            for appel in (lambda: texte_conf(ENCEINTE, profil, humeur), lambda: parametres(profil, humeur)):
                with self.assertRaisesRegex(ValueError, "nom de filtre"):
                    appel()

    def test_filtre_inconnu_refuse(self):
        h = profil_enceinte.humeurs["cocon"]
        profil = replace(profil_enceinte, chaine=[("marge", "bq_evil } x")])
        with self.assertRaisesRegex(ValueError, "filtre inconnu"):
            texte_conf(ENCEINTE, profil, h)
        with self.assertRaisesRegex(ValueError, "filtre inconnu"):
            parametres(profil, h)

    def test_reglage_manquant_signale(self):
        h = profil_enceinte.humeurs["cocon"]
        sans_air = replace(h, reglages={k: v for k, v in h.reglages.items() if k != "air"})
        sans_gain = replace(h, reglages={**h.reglages, "air": {"Freq": 1.0, "Q": 1.0}})
        for humeur in (sans_air, sans_gain):
            for appel in (lambda: texte_conf(ENCEINTE, profil_enceinte, humeur),
                          lambda: parametres(profil_enceinte, humeur)):
                with self.assertRaisesRegex(ValueError, "air"):
                    appel()

    def test_noms(self):
        self.assertEqual((NOEUD, NOEUD_SORTIE), ("diapason", "diapason.sortie"))

    def test_conf_enceinte(self):
        t = texte_conf(ENCEINTE, profil_enceinte, profil_enceinte.humeurs["cocon"])
        self.assertIn('target.object = "bluez_output.AA_BB_CC_DD_EE_02.1"', t)
        self.assertIn('node.description = "LN-1008BT · Diapason"', t)
        self.assertIn('media.name = "Diapason"', t)
        self.assertIn('node.name = "diapason"', t)
        self.assertIn('node.name = "diapason.sortie"', t)
        self.assertIn("media.class = Audio/Sink", t)
        self.assertIn("node.dont-reconnect = true", t)
        self.assertIn("audio.position = [ FL FR ]", t)
        self.assertLess(t.index("name = marge"), t.index("name = coupe"))
        self.assertIn('{ output = "voix:Out" input = "air:In" }', t)
        self.assertIn('{ output = "marge:Out" input = "coupe:In" }', t)
        self.assertIn('"Freq" = 100.0', t)
        self.assertIn('"Gain" = -5.5', t)

    def test_conf_lisible_par_pipewire(self):
        for nom in profil_enceinte.humeurs:
            t = texte_conf(ENCEINTE, profil_enceinte, profil_enceinte.humeurs[nom])
            sans_chaines = re.sub(r'"(?:[^"\\]|\\.)*"', '""', t)
            for ouvrant, fermant in ("{}", "[]"):
                self.assertEqual(sans_chaines.count(ouvrant), sans_chaines.count(fermant))
            self.verifier_structure(t)
            for interdit in ("None", "True", "False", "inf", "nan"):
                self.assertNotRegex(sans_chaines, rf"\b{interdit}\b")

    def test_nom_avec_guillemet_echappe(self):
        s = Sortie("alsa_output.x", 'Salon "TV"\\n\nbis', "x", "haut-parleurs-pc", 2, None)
        t = texte_conf(s, profil_enceinte, profil_enceinte.humeurs["neutre"])
        self.assertIn('node.description = "Salon \\"TV\\"\\\\n bis · Diapason"', t)

    def test_parametres_cocon(self):
        p = parametres(profil_enceinte, profil_enceinte.humeurs["cocon"])
        self.assertEqual((p["grave:Gain"], p["air:Freq"], len(p)), (5.0, 10000.0, 18))
        self.assertTrue(all(type(v) is float for v in p.values()))

    def test_valeur_non_finie_refusee(self):
        h = profil_enceinte.humeurs["cocon"]
        mauvais = type(h)(h.id, h.titre, h.description, {**h.reglages, "air": {"Freq": 1.0, "Q": 1.0, "Gain": float("inf")}})
        with self.assertRaises(ValueError):
            texte_conf(ENCEINTE, profil_enceinte, mauvais)
        with self.assertRaises(ValueError):
            parametres(profil_enceinte, mauvais)


if __name__ == "__main__":
    unittest.main()
