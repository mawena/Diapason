import tempfile
import unittest
from pathlib import Path

from diapason.biquad import gain_max_db
from diapason.profils import Catalogue, normaliser_id

DATA = Path(__file__).resolve().parent.parent / "data" / "profils"

CHAINE = '[["marge", "bq_highshelf"], ["coupe", "bq_highpass"], ["grave", "bq_lowshelf"], ' \
         '["boite", "bq_peaking"], ["voix", "bq_peaking"], ["air", "bq_highshelf"]]'


def humeur_toml(identifiant, grave_gain=3.0, avec_air=True):
    texte = f"""
[humeurs."{identifiant}"]
titre = "Perso"
description = "Humeur de test"
marge = {{ Freq = 0.0, Q = 1.0, Gain = -5.0 }}
coupe = {{ Freq = 50.0, Q = 0.707, Gain = 0.0 }}
grave = {{ Freq = 100.0, Q = 0.6, Gain = {grave_gain} }}
boite = {{ Freq = 320.0, Q = 1.0, Gain = -2.0 }}
voix = {{ Freq = 2800.0, Q = 1.0, Gain = -0.5 }}
"""
    if avec_air:
        texte += "air = { Freq = 10000.0, Q = 0.7, Gain = 1.5 }\n"
    return texte


class TestProfils(unittest.TestCase):
    def dossier_utilisateur(self, contenu, entete=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        if entete is None:
            entete = f'type = "enceinte-bluetooth"\n'
        (Path(tmp.name) / "enceinte-bluetooth.toml").write_text(entete + contenu, encoding="utf-8")
        return Path(tmp.name)

    def test_enceinte_livree(self):
        p = Catalogue.charger([DATA]).profil("enceinte-bluetooth")
        self.assertEqual(p.humeur_par_defaut, "cocon")
        self.assertEqual(sorted(p.humeurs), ["cocon", "douceur", "eclat", "fete", "neutre", "voix"])
        self.assertEqual(p.humeurs["cocon"].reglages["grave"], {"Freq": 100.0, "Q": 0.6, "Gain": 5.0})
        self.assertEqual(p.humeurs["fete"].titre, "Fête")

    def test_neutre_est_a_plat(self):
        p = Catalogue.charger([DATA]).profil("enceinte-bluetooth")
        n = p.humeurs["neutre"]
        self.assertEqual((n.titre, n.description), ("Neutre", "Son d'origine, filtre à plat"))
        self.assertEqual(n.reglages["coupe"], {"Freq": 5.0, "Q": 0.0, "Gain": 0.0})
        self.assertEqual(n.reglages["grave"], {"Freq": 100.0, "Q": 0.6, "Gain": 0.0})
        self.assertTrue(all(r["Gain"] == 0.0 for r in n.reglages.values()))

    def test_chaine_calcul(self):
        p = Catalogue.charger([DATA]).profil("enceinte-bluetooth")
        chaine = p.humeurs["cocon"].chaine_calcul(p)
        self.assertEqual([f for f, _ in chaine],
                         ["bq_highshelf", "bq_highpass", "bq_lowshelf", "bq_peaking", "bq_peaking", "bq_highshelf"])
        self.assertEqual(chaine[2][1], {"Freq": 100.0, "Q": 0.6, "Gain": 5.0})

    def test_aucune_humeur_livree_ne_sature(self):
        cat = Catalogue.charger([DATA])
        for p in (cat.profil(t) for t in ("enceinte-bluetooth",)):   # tâche 12 ajoute "haut-parleurs-pc"
            for h in p.humeurs.values():
                self.assertLessEqual(gain_max_db(h.chaine_calcul(p)), 1e-6, f"{p.type}/{h.id}")

    def test_livre_sans_erreur(self):
        self.assertEqual(Catalogue.charger([DATA]).verifier(), [])

    def test_surcharge_utilisateur_remplace_une_humeur(self):
        user = self.dossier_utilisateur(humeur_toml("cocon", grave_gain=3.0))
        p = Catalogue.charger([DATA, user]).profil("enceinte-bluetooth")
        self.assertEqual(p.humeurs["cocon"].reglages["grave"]["Gain"], 3.0)
        self.assertEqual(p.humeurs["douceur"].reglages["marge"]["Gain"], -4.5)
        self.assertEqual(sorted(p.humeurs), ["cocon", "douceur", "eclat", "fete", "neutre", "voix"])

    def test_surcharge_ajoute_une_humeur(self):
        user = self.dossier_utilisateur(humeur_toml("Mon Soir"))
        p = Catalogue.charger([DATA, user]).profil("enceinte-bluetooth")
        self.assertIn("monsoir", p.humeurs)

    def test_surcharge_ne_change_pas_la_chaine(self):
        user = self.dossier_utilisateur(
            humeur_toml("cocon"), entete='type = "enceinte-bluetooth"\nchaine = [["marge", "bq_highshelf"]]\n')
        cat = Catalogue.charger([DATA, user])
        p = cat.profil("enceinte-bluetooth")
        self.assertEqual(len(p.chaine), 6)
        messages = cat.verifier()
        self.assertEqual(len(messages), 1)
        self.assertIn("chaine", messages[0])

    def test_humeur_incomplete_signalee(self):
        user = self.dossier_utilisateur(humeur_toml("cocon", avec_air=False))
        messages = Catalogue.charger([DATA, user]).verifier()
        self.assertEqual(len(messages), 1)
        self.assertIn("cocon", messages[0])
        self.assertIn("air", messages[0])

    def test_humeur_qui_sature_signalee(self):
        user = self.dossier_utilisateur(humeur_toml("cocon", grave_gain=12.0))
        messages = Catalogue.charger([DATA, user]).verifier()
        self.assertEqual(len(messages), 1)
        self.assertIn("cocon", messages[0])

    def test_type_sans_profil_est_neutre(self):
        p = Catalogue.charger([DATA]).profil("hdmi")
        self.assertEqual((list(p.humeurs), p.humeur_par_defaut, p.chaine),
                         (["neutre"], "neutre", [("marge", "bq_highshelf")]))

    def test_normaliser_id(self):
        self.assertEqual([normaliser_id(x) for x in ("Fête", " ÉCLAT ", "cocon")], ["fete", "eclat", "cocon"])

    def test_fichier_utilisateur_illisible_ignore(self):
        user = self.dossier_utilisateur("ceci n'est [pas du toml")
        cat = Catalogue.charger([DATA, user])
        p = cat.profil("enceinte-bluetooth")
        self.assertEqual(sorted(p.humeurs), ["cocon", "douceur", "eclat", "fete", "neutre", "voix"])
        self.assertEqual(p.humeurs["cocon"].reglages["grave"]["Gain"], 5.0)
        messages = cat.verifier()
        self.assertEqual(len(messages), 1)
        self.assertIn("enceinte-bluetooth.toml", messages[0])

    def test_dossier_absent_ignore(self):
        cat = Catalogue.charger([DATA, Path("/nexiste/pas")])
        self.assertEqual(cat.verifier(), [])


if __name__ == "__main__":
    unittest.main()
