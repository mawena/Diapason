#!/usr/bin/env python3
"""Enregistre l'état audio du poste (pw-dump filtré et anonymisé) comme exemple de test.

Usage : python3 -I tests/outils/capturer_exemple.py <nom>   → tests/exemples/<nom>.json
Garde seulement les sorties (nœuds Audio/Sink), les appareils audio et la métadonnée
« default ». Les adresses Bluetooth et numéros de série sont remplacés."""
import json, re, subprocess, sys
from pathlib import Path

GARDER_CLASSES = {"Audio/Sink", "Audio/Device"}


def garder(o):
    t = o.get("type", "")
    props = (o.get("info") or {}).get("props") or o.get("props") or {}
    if t.endswith(":Metadata"):
        return props.get("metadata.name") == "default"
    return t.endswith((":Node", ":Device")) and props.get("media.class") in GARDER_CLASSES


def anonymiser(texte):
    trouves = re.findall(r"(?:[0-9A-F]{2}[:_]){5}[0-9A-F]{2}", texte)
    numeros = {}
    for mac in trouves:
        numeros.setdefault(mac.replace("_", ":"), len(numeros) + 1)
    for mac in set(trouves):
        sep = mac[2]
        faux = sep.join(["AA", "BB", "CC", "DD", "EE", f"{numeros[mac.replace('_', ':')]:02X}"])
        texte = texte.replace(mac, faux)
    texte = re.sub(r"(D6000_)\d{6,}", r"\g<1>0000000000", texte)
    return re.sub(r"(?i)(\"[^\"]*(host|user|machine)[^\"]*\":\s*)\"[^\"]*\"", r'\1"anonyme"', texte)


def main():
    nom = sys.argv[1]
    objets = [o for o in json.loads(subprocess.check_output(["pw-dump"])) if garder(o)]
    sortie = Path(__file__).resolve().parent.parent / "exemples" / f"{nom}.json"
    sortie.write_text(anonymiser(json.dumps(objets, ensure_ascii=False, indent=1)) + "\n")
    print(sortie, len(objets), "objets")


if __name__ == "__main__":
    main()
