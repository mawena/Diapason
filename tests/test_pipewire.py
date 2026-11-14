import json
import subprocess
import unittest
from unittest import mock

from diapason.pipewire import ErreurPipeWire, Flux, PipeWire


class Enregistreur:
    """Faux executer : garde les commandes, renvoie des sorties préparées."""

    def __init__(self, sorties=None):
        self.commandes = []
        self.sorties = sorties or {}

    def __call__(self, args):
        self.commandes.append(list(args))
        return self.sorties.get(tuple(args), "")


DUMP = json.dumps([
    {"id": 40, "type": "PipeWire:Interface:Node",
     "info": {"props": {"node.name": "autre"}}},
    {"id": 96, "type": "PipeWire:Interface:Node",
     "info": {"props": {"node.name": "diapason"}}},
    {"id": 97, "type": "PipeWire:Interface:Client", "info": {"props": {}}},
])


class TestPipeWire(unittest.TestCase):
    def test_volume_lu(self):
        sortie = ("Volume: front-left: 26214 /  40% / -23.88 dB,   "
                  "front-right: 26214 /  40% / -23.88 dB\n"
                  "        balance 0.00\n")
        ex = Enregistreur({("pactl", "get-sink-volume", "x"): sortie})
        self.assertAlmostEqual(PipeWire(ex).volume("x"), 0.40)

    def test_volume_mono_et_moyenne(self):
        mono = "Volume: mono: 32768 /  50% / -18.06 dB\n        balance 0.00\n"
        ex = Enregistreur({("pactl", "get-sink-volume", "m"): mono})
        self.assertAlmostEqual(PipeWire(ex).volume("m"), 0.50)
        deux = "Volume: front-left: 1 /  30% / -1 dB,   front-right: 1 /  50% / -1 dB\n"
        ex = Enregistreur({("pactl", "get-sink-volume", "d"): deux})
        self.assertAlmostEqual(PipeWire(ex).volume("d"), 0.40)

    def test_volume_illisible(self):
        ex = Enregistreur({("pactl", "get-sink-volume", "x"): "n'importe quoi"})
        with self.assertRaises(ErreurPipeWire):
            PipeWire(ex).volume("x")

    def test_definir_volume(self):
        ex = Enregistreur()
        PipeWire(ex).definir_volume("x", 0.4)
        self.assertEqual(ex.commandes[-1], ["pactl", "set-sink-volume", "x", "40%"])

    def test_definir_defaut_deplacer_profil(self):
        ex = Enregistreur()
        pw = PipeWire(ex)
        pw.definir_defaut("s")
        pw.deplacer_flux(7, "s")
        pw.definir_profil("carte", "a2dp")
        self.assertEqual(ex.commandes, [
            ["pactl", "set-default-sink", "s"],
            ["pactl", "move-sink-input", "7", "s"],
            ["pactl", "set-card-profile", "carte", "a2dp"],
        ])

    def test_appliquer(self):
        ex = Enregistreur({("pw-dump",): DUMP})
        PipeWire(ex).appliquer("diapason", {"grave:Gain": 5.0, "air:Freq": 10000.0})
        self.assertEqual(ex.commandes[-1], [
            "pw-cli", "s", "96", "Props",
            '{ params = [ "grave:Gain" 5.0 "air:Freq" 10000.0 ] }'])

    def test_appliquer_noeud_absent(self):
        ex = Enregistreur({("pw-dump",): DUMP})
        with self.assertRaises(ErreurPipeWire):
            PipeWire(ex).appliquer("absent", {"a": 1.0})

    def test_noeud_present(self):
        pw = PipeWire(Enregistreur({("pw-dump",): DUMP}))
        self.assertTrue(pw.noeud_present("diapason"))
        self.assertFalse(pw.noeud_present("absent"))

    def test_etat(self):
        pw = PipeWire(Enregistreur({("pw-dump",): DUMP}))
        self.assertEqual(len(pw.etat()), 3)

    def test_flux_resolus(self):
        entrees = json.dumps([
            {"index": 7, "sink": 790, "properties": {"node.name": "Firefox"}},
            {"index": 8, "sink": 999, "properties": {}},
        ])
        courts = "790\tbluez_output.AA\tPipeWire\ts16le 2ch 48000Hz\tRUNNING\n"
        ex = Enregistreur({
            ("pactl", "-f", "json", "list", "sink-inputs"): entrees,
            ("pactl", "list", "sinks", "short"): courts,
        })
        self.assertEqual(PipeWire(ex).flux(), [
            Flux(7, "Firefox", "bluez_output.AA"),
            Flux(8, None, None),
        ])

    def test_lc_all_c(self):
        vu = {}

        def faux_run(args, **kw):
            vu.update(kw)
            return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

        with mock.patch("diapason.pipewire.subprocess.run", faux_run):
            PipeWire()._executer(["pactl", "info"])
        self.assertEqual(vu["env"]["LC_ALL"], "C")
        self.assertEqual(vu["timeout"], 5)

    def test_code_non_nul(self):
        def faux_run(args, **kw):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="raté")

        with mock.patch("diapason.pipewire.subprocess.run", faux_run):
            with self.assertRaises(ErreurPipeWire):
                PipeWire().etat()


if __name__ == "__main__":
    unittest.main()
