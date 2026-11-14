"""Calcul des biquads, identique à PipeWire 1.0.5.

Traduction de `src/modules/module-filter-chain/biquad.c` (filtres `bq_highpass`,
`bq_lowshelf`, `bq_highshelf` et `bq_peaking`). La fréquence normalisée vaut
`Freq * 2 / taux`, comme dans `builtin_plugin.c`.
"""

import cmath
import math

Coefficients = tuple[float, float, float, float, float]

TAUX_REFERENCE = 48000.0
NB_FREQUENCES = 800
FREQ_MIN = 20.0
FREQ_MAX = 20000.0


def _normaliser(b0, b1, b2, a0, a1, a2) -> Coefficients:
    """Divise tous les coefficients par a0."""
    inverse = 1 / a0
    return (b0 * inverse, b1 * inverse, b2 * inverse, a1 * inverse, a2 * inverse)


def _passe_haut(coupure: float, resonance: float) -> Coefficients:
    coupure = max(0.0, min(coupure, 1.0))
    if coupure in (0.0, 1.0):
        return _normaliser(1 - coupure, 0, 0, 1, 0, 0)
    resonance = max(0.0, resonance)
    g = 10.0 ** (0.05 * resonance)
    d = math.sqrt((4 - math.sqrt(16 - 16 / (g * g))) / 2)
    theta = math.pi * coupure
    sn = 0.5 * d * math.sin(theta)
    beta = 0.5 * (1 - sn) / (1 + sn)
    gamma = (0.5 + beta) * math.cos(theta)
    alpha = 0.25 * (0.5 + beta + gamma)
    return _normaliser(2 * alpha, 2 * -2 * alpha, 2 * alpha, 1, 2 * -gamma, 2 * beta)


def _etagere_basse(frequence: float, gain_db: float) -> Coefficients:
    frequence = max(0.0, min(frequence, 1.0))
    A = 10.0 ** (gain_db / 40)
    if frequence == 1:
        return _normaliser(A * A, 0, 0, 1, 0, 0)
    if frequence <= 0:
        return _normaliser(1, 0, 0, 1, 0, 0)
    w0 = math.pi * frequence
    S = 1.0
    alpha = 0.5 * math.sin(w0) * math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    k = math.cos(w0)
    k2 = 2 * math.sqrt(A) * alpha
    a_plus = A + 1
    a_moins = A - 1
    return _normaliser(
        A * (a_plus - a_moins * k + k2),
        2 * A * (a_moins - a_plus * k),
        A * (a_plus - a_moins * k - k2),
        a_plus + a_moins * k + k2,
        -2 * (a_moins + a_plus * k),
        a_plus + a_moins * k - k2,
    )


def _etagere_haute(frequence: float, gain_db: float) -> Coefficients:
    frequence = max(0.0, min(frequence, 1.0))
    A = 10.0 ** (gain_db / 40)
    if frequence == 1:
        return _normaliser(1, 0, 0, 1, 0, 0)
    if frequence <= 0:
        return _normaliser(A * A, 0, 0, 1, 0, 0)
    w0 = math.pi * frequence
    S = 1.0
    alpha = 0.5 * math.sin(w0) * math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    k = math.cos(w0)
    k2 = 2 * math.sqrt(A) * alpha
    a_plus = A + 1
    a_moins = A - 1
    return _normaliser(
        A * (a_plus + a_moins * k + k2),
        -2 * A * (a_moins + a_plus * k),
        A * (a_plus + a_moins * k - k2),
        a_plus - a_moins * k + k2,
        2 * (a_moins - a_plus * k),
        a_plus - a_moins * k - k2,
    )


def _pic(frequence: float, q: float, gain_db: float) -> Coefficients:
    frequence = max(0.0, min(frequence, 1.0))
    q = max(0.0, q)
    A = 10.0 ** (gain_db / 40)
    if frequence <= 0 or frequence >= 1:
        return _normaliser(1, 0, 0, 1, 0, 0)
    if q <= 0:
        return _normaliser(A * A, 0, 0, 1, 0, 0)
    w0 = math.pi * frequence
    alpha = math.sin(w0) / (2 * q)
    k = math.cos(w0)
    return _normaliser(
        1 + alpha * A, -2 * k, 1 - alpha * A,
        1 + alpha / A, -2 * k, 1 - alpha / A,
    )


def coefficients(filtre: str, freq: float, q: float, gain: float,
                 taux: float = TAUX_REFERENCE) -> Coefficients:
    """Renvoie (b0, b1, b2, a1, a2), normalisés par a0, comme PipeWire 1.0.5."""
    normalisee = freq * 2 / taux
    if filtre == "bq_highpass":
        return _passe_haut(normalisee, q)
    if filtre == "bq_lowshelf":
        return _etagere_basse(normalisee, gain)
    if filtre == "bq_highshelf":
        return _etagere_haute(normalisee, gain)
    if filtre == "bq_peaking":
        return _pic(normalisee, q, gain)
    raise ValueError(f"filtre inconnu : {filtre}")


def reponse_db(chaine: list[tuple[str, dict]], freq: float,
               taux: float = TAUX_REFERENCE) -> float:
    """Réponse en dB de la chaîne à la fréquence `freq` (somme des biquads)."""
    z1 = cmath.exp(-2j * math.pi * freq / taux)
    z2 = z1 * z1
    total = 0.0
    for filtre, p in chaine:
        b0, b1, b2, a1, a2 = coefficients(filtre, p["Freq"], p["Q"], p["Gain"], taux)
        h = (b0 + b1 * z1 + b2 * z2) / (1 + a1 * z1 + a2 * z2)
        total += 20 * math.log10(max(abs(h), 1e-12))
    return total


def gain_max_db(chaine: list[tuple[str, dict]], taux: float = TAUX_REFERENCE) -> float:
    """Gain maximal de la chaîne sur 800 fréquences logarithmiques, de 20 Hz à 20 kHz."""
    rapport = FREQ_MAX / FREQ_MIN
    return max(
        reponse_db(chaine, FREQ_MIN * rapport ** (i / (NB_FREQUENCES - 1)), taux)
        for i in range(NB_FREQUENCES)
    )
