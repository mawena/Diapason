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


def _props(objet: dict) -> dict:
    return objet.get("info", {}).get("props", {})


def _est_bluetooth(props: dict) -> bool:
    return props.get("device.api") == "bluez5"


def _canaux(props: dict) -> int:
    if props.get("audio.channels"):
        return int(props["audio.channels"])
    position = str(props.get("audio.position", "")).strip("[] ").replace(",", " ").split()
    return len(position) or 2


def _route_active(appareil: dict | None, props_noeud: dict) -> str | None:
    """Nom de la route de sortie de l'appareil (carte) qui porte ce nœud."""
    if appareil is None:
        return None
    for route in appareil.get("info", {}).get("params", {}).get("Route", []):
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
    appareils = {o["id"]: o for o in dump if o.get("type") == "PipeWire:Interface:Device"}
    sorties = {}
    for objet in dump:
        if objet.get("type") != "PipeWire:Interface:Node":
            continue
        props = _props(objet)
        nom_noeud = props.get("node.name", "")
        if (props.get("media.class") != "Audio/Sink" or "device.id" not in props
                or nom_noeud.startswith("diapason")):
            continue
        appareil = appareils.get(props["device.id"])
        props_carte = _props(appareil) if appareil else {}
        carte = props_carte.get("device.name")
        description_carte = props_carte.get("device.description")
        if _est_bluetooth(props_carte):
            type_ = "casque" if props_carte.get("device.form-factor") == "headphone" else "enceinte-bluetooth"
            identite = f"bluez:{props_carte.get('api.bluez5.address')}"
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
    for objet in dump:
        if objet.get("type") != "PipeWire:Interface:Device":
            continue
        props = _props(objet)
        nom = props.get("device.name")
        if not nom:
            continue
        params = objet.get("info", {}).get("params", {})
        bluetooth = _est_bluetooth(props)
        actifs = params.get("Profile", [])
        cartes[nom] = Carte(
            nom=nom,
            bluetooth=bluetooth,
            identite=f"bluez:{props.get('api.bluez5.address')}" if bluetooth else None,
            profils=tuple(p["name"] for p in params.get("EnumProfile", [])),
            actif=actifs[0]["name"] if actifs else None,
        )
    return cartes


def sortie_par_defaut(dump: list[dict]) -> str | None:
    for objet in dump:
        if (objet.get("type") == "PipeWire:Interface:Metadata"
                and objet.get("props", {}).get("metadata.name") == "default"):
            for entree in objet.get("metadata", []):
                if entree.get("key") == "default.audio.sink":
                    valeur = entree.get("value")
                    return valeur.get("name") if isinstance(valeur, dict) else None
    return None
