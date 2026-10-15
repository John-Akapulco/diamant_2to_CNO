#!/usr/bin/env python3
"""
Énergie MACE du diamant (2 atomes, a = 3.567 Å), sur six décimales.

Sert de signature du modèle. Sur Yargla deux checkpoints cohabitent dans
~/.cache/mace et ce ne sont pas le même modèle : 13 meV d'écart sur cette
valeur, aucune erreur levée, et des résultats silencieusement incomparables
d'une machine à l'autre. Les scripts de job appellent donc ce fichier pour
identifier le bon checkpoint au lieu de coder son nom en dur.

Valeur de référence du Mac et de 5yyxdm76 sur Yargla : -18.149009 eV.
"""

import os
import sys

sys.path.insert(0, os.environ.get("CNO_UNDER_PRESSURE",
                                  os.path.expanduser("~/C_N_O_under_pressure")))

from ase.build import bulk                                    # noqa: E402
from cno_csp.relax import get_calculator                      # noqa: E402

a = bulk("C", "diamond", a=3.567)
# device="cpu" explicitement : cette vérification doit marcher sur le noeud de
# connexion comme sur un noeud GPU, et CNO_DEVICE=cuda y serait un échec.
a.calc = get_calculator("mace", device="cpu")
print("%.6f" % a.get_potential_energy())
