#!/usr/bin/env python3
"""
Domaine de composition atteignable par la famille lacunaire, sans aucun calcul d'énergie.

    python scripts/carte_composition.py --kmax 4

Répond à la question « quels (x, y, z) cette famille peut-elle atteindre ? »,
qui précède toute optimisation de l'enthalpie de formation : inutile de
chercher un optimum dans une région que la combinatoire du réseau interdit.

Vérifie aussi, à chaque ensemble de lacunes, le bilan de liaisons pendantes
    n_N + 2·n_O = 4k − 2b
(b = liaisons lacune-lacune). Un écart signalerait une erreur de comptage
dans l'énumération ; c'est un contrôle interne, pas une mesure.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dia_cno.lattice import demi_liaisons, permutations_symetrie, supermaille
from dia_cno.vacancies import (classes_de_lacunes, coordinences, decorations,
                               liaisons_internes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mailles", nargs="+", default=["1x1x1", "2x1x1", "2x2x1", "2x2x2"])
    ap.add_argument("--kmax", type=int, default=4)
    ap.add_argument("--motifs", nargs="+", default=["canonique"])
    ap.add_argument("--binaires", action="store_true",
                    help="compter aussi les binaires ; exclus par défaut")
    args = ap.parse_args()

    atteint: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    ecarts = 0
    for m in args.mailles:
        n = tuple(int(x) for x in m.lower().split("x"))
        parent = supermaille(n)
        adj = demi_liaisons(parent)
        P = permutations_symetrie(parent)
        niveaux = classes_de_lacunes(P, len(parent), adj, args.kmax, z_min=2)
        print(f"\n[dia{n[0]}{n[1]}{n[2]}] {len(parent)} sites")
        for k in range(1, args.kmax + 1):
            lignes = Counter()
            for V in niveaux[k]:
                vac = frozenset(V)
                z = coordinences(adj, vac)
                if not z or min(z.values()) < 2:
                    continue
                b = liaisons_internes(adj, vac)
                n_N = sum(1 for v in z.values() if v == 3)
                n_O = sum(1 for v in z.values() if v == 2)
                if n_N + 2 * n_O != 4 * k - 2 * b:
                    ecarts += 1
                for dec in decorations(adj, V, motifs=tuple(args.motifs),
                                       require_ternary=not args.binaires):
                    c = dec.composition
                    lignes[c] += 1
                    atteint[c].append(f"dia{n[0]}{n[1]}{n[2]}/k{k}")
            if lignes:
                tot = len(parent) - k
                print(f"  k={k} ({k/len(parent):4.1%} de lacunes, {tot} atomes) : "
                      + ", ".join(f"C{a}N{b_}O{c_}" for (a, b_, c_) in sorted(lignes)))

    print("\n" + "=" * 78)
    print("compositions réduites atteintes (x, y, z en fractions) :")
    vus = {}
    for (a, b_, c_), src in sorted(atteint.items()):
        t = a + b_ + c_
        cle = (round(a / t, 4), round(b_ / t, 4), round(c_ / t, 4))
        vus.setdefault(cle, (f"C{a}N{b_}O{c_}", len(src)))
    for (x, y, zz), (f, nsrc) in sorted(vus.items(), key=lambda kv: (-kv[0][0], kv[0][1])):
        tern = "ternaire" if min(x, y, zz) > 0 else ""
        print(f"  x={x:.3f} y={y:.3f} z={zz:.3f}   ex. {f:10s} ({nsrc} ensembles) {tern}")
    print(f"\n{len(vus)} compositions distinctes ; "
          f"{sum(1 for k2 in vus if min(k2) > 0)} ternaires C+N+O")
    print(f"contrôle du bilan de liaisons pendantes : {ecarts} écart(s)")


if __name__ == "__main__":
    main()
