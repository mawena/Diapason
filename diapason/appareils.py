"""Lecture des sorties audio, des cartes et de la sortie par défaut depuis un `pw-dump`."""
from dataclasses import dataclass

TYPES = ("enceinte-bluetooth", "haut-parleurs-pc", "casque", "hdmi", "autre")


@dataclass(frozen=True)
class Sortie:
    noeud: str
    nom: str
    identite: str
    type: str
    canaux: int
    carte: str | None


@dataclass(frozen=True)
class Carte:
    nom: str
    bluetooth: bool
    identite: str | None
    profils: tuple[str, ...]
    actif: str | None


def _dict(valeur) -> dict:
    return valeur if isinstance(valeur, dict) else {}


def _liste(valeur) -> list:
    return [v for v in valeur if isinstance(v, dict)] if isinstance(valeur, list) else []


def _objets(dump, type_: str) -> list[dict]:
    return [o for o in _liste(dump) if o.get("type") == type_]


def _info(objet: dict) -> dict:
    return _dict(objet.get("info"))


def _props(objet: dict) -> dict:
    return _dict(_info(objet).get("props"))


def _params(objet: dict) -> dict:
    return _dict(_info(objet).get("params"))


def _est_bluetooth(props: dict) -> bool:
    return props.get("device.api") == "bluez5"


def _canaux(props: dict) -> int:
    try:
        canaux = int(props.get("audio.channels"))
    except (TypeError, ValueError):
        canaux = 0
    if canaux > 0:
        return canaux
    position = str(props.get("audio.position", "")).strip("[] ").replace(",", " ").split()
    return len(position) or 2


def _route_active(appareil: dict | None, props_noeud: dict) -> str | None:
    """Nom de la route de sortie de l'appareil (carte) qui porte ce nœud."""
    if appareil is None:
        return None
    for route in _liste(_params(appareil).get("Route")):
        if (route.get("direction") == "Output"
                and route.get("device") == props_noeud.get("card.profile.device")):
            return route.get("name")
    return None


def _type_alsa(route: str | None, noeud: str) -> str:
    route = route or ""
    if "Speaker" in route:
        return "haut-parleurs-pc"
    if "Headphone" in route:
        return "casque"
    textes = (route.lower(), noeud.lower())
    if "HDMI" in route or any("hdmi" in t or "iec958" in t for t in textes):
        return "hdmi"
    return "autre"


def lire_sorties(dump: list[dict]) -> dict[str, Sortie]:
    appareils = {o["id"]: o for o in _objets(dump, "PipeWire:Interface:Device") if "id" in o}
    sorties = {}
    for objet in _objets(dump, "PipeWire:Interface:Node"):
        props = _props(objet)
        nom_noeud = str(props.get("node.name") or "")
        if (props.get("media.class") != "Audio/Sink" or "device.id" not in props
                or nom_noeud.startswith("diapason")):
            continue
        appareil = appareils.get(props["device.id"])
        props_carte = _props(appareil) if appareil else {}
        carte = props_carte.get("device.name")
        description_carte = props_carte.get("device.description")
        if _est_bluetooth(props_carte):
            type_ = "casque" if props_carte.get("device.form-factor") == "headphone" else "enceinte-bluetooth"
            adresse = props_carte.get("api.bluez5.address")
            if adresse:
                identite = f"bluez:{adresse}"
            else:
                identite = f"{carte}:{nom_noeud}" if carte else nom_noeud
        else:
            route = _route_active(appareil, props)
            type_ = _type_alsa(route, nom_noeud)
            identite = f"{carte}:{route or nom_noeud}"
        if type_ == "haut-parleurs-pc":
            nom = "Haut-parleurs du PC"
        elif type_ == "casque" and not _est_bluetooth(props_carte):
            nom = "Prise casque"
        else:
            nom = description_carte or props.get("node.description", nom_noeud)
        sorties[nom_noeud] = Sortie(nom_noeud, nom, identite, type_, _canaux(props), carte)
    return sorties


def lire_cartes(dump: list[dict]) -> dict[str, Carte]:
    cartes = {}
    for objet in _objets(dump, "PipeWire:Interface:Device"):
        props = _props(objet)
        nom = props.get("device.name")
        if not nom:
            continue
        params = _params(objet)
        bluetooth = _est_bluetooth(props)
        actifs = [p for p in _liste(params.get("Profile")) if p.get("name")]
        cartes[nom] = Carte(
            nom=nom,
            bluetooth=bluetooth,
            identite=(f"bluez:{props['api.bluez5.address']}"
                      if bluetooth and props.get("api.bluez5.address") else None),
            profils=tuple(p["name"] for p in _liste(params.get("EnumProfile")) if p.get("name")),
            actif=actifs[0]["name"] if actifs else None,
        )
    return cartes


def sortie_par_defaut(dump: list[dict]) -> str | None:
    for objet in _objets(dump, "PipeWire:Interface:Metadata"):
        if _dict(objet.get("props")).get("metadata.name") != "default":
            continue
        for entree in _liste(objet.get("metadata")):
            if entree.get("key") == "default.audio.sink":
                valeur = entree.get("value")
                return valeur.get("name") if isinstance(valeur, dict) else None
    return None
