"""
diamant_to_CNO : creuser le diamant pour y réaliser les six environnements C-N-O.

Projet jumeau : C_N_O_under_pressure, qui part de templates de Materials
Project. Ici le template est unique -- le diamant -- et c'est la LACUNE qui
engendre la diversité. Tout l'outillage aval (relaxation MACE, phonons,
entrées VASP, enthalpies de formation, rapport) est réutilisé tel quel depuis
ce projet jumeau, via jumeau() qui l'ajoute au sys.path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

JUMEAU_DEFAUT = Path.home() / "C_N_O_under_pressure"


def jumeau() -> Path:
    """Rend le chemin du projet jumeau et le rend importable (cno_csp, scripts...)."""
    p = Path(os.environ.get("CNO_UNDER_PRESSURE", JUMEAU_DEFAUT))
    if not (p / "cno_csp").is_dir():
        raise RuntimeError(
            f"projet jumeau introuvable en {p} ; définir CNO_UNDER_PRESSURE")
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
    return p
