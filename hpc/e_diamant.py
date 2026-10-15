#!/usr/bin/env python3
"""
Énergie MACE du diamant (2 atomes, a = 3.567 Å), sur six décimales.

Sert de signature du modèle. Sur Yargla deux checkpoints cohabitent dans
~/.cache/mace et ce ne sont pas le même modèle : 13 meV d'écart sur cette
valeur, aucune erreur levée, et des résultats silencieusement incomparables
d'une machine à l'autre. Les scripts de job appellent donc ce fichier pour
identifier le bon checkpoint au lieu de coder son nom en dur.

Valeur de référence du Mac et de 5yyxdm76 sur Yargla : -18.149009 eV.

STDOUT NE PORTE QUE LE NOMBRE, et c'est le point délicat. MACE n'écrit pas ses
messages de chargement au même endroit selon les versions : sur le Mac (mace
0.3.12) ils partent sur stderr, sur Yargla (mace 0.3.16) sur stdout. Un
appelant qui fait E=$(... 2>/dev/null) récupérait donc une variable polluée sur
Yargla, la comparaison de chaîne échouait, et le job s'arrêtait sur une
assertion fausse APRÈS la file d'attente -- alors que l'énergie était la bonne.
Constaté le 2026-10-15 sur le nœud de connexion de Yargla.

On redirige donc tout stdout de la bibliothèque vers stderr pendant le calcul,
et on n'imprime le nombre qu'à la fin. Les messages restent visibles pour le
diagnostic, mais hors du canal que l'appelant lit.
"""

import contextlib
import os
import sys

sys.path.insert(0, os.environ.get("CNO_UNDER_PRESSURE",
                                  os.path.expanduser("~/C_N_O_under_pressure")))

with contextlib.redirect_stdout(sys.stderr):
    from ase.build import bulk
    from cno_csp.relax import get_calculator

    atoms = bulk("C", "diamond", a=3.567)
    # device="cpu" explicitement : cette vérification doit marcher sur le nœud
    # de connexion comme sur un nœud GPU, et CNO_DEVICE=cuda y échouerait.
    atoms.calc = get_calculator("mace", device="cpu")
    energie = float(atoms.get_potential_energy())

print("%.6f" % energie)
