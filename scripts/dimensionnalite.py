#!/usr/bin/env python3
"""
Quelle dimensionnalité la famille lacunaire produit-elle, et à quelle concentration ?

    python scripts/dimensionnalite.py --mailles 2x1x1 2x2x1 --kmax 6

Question posée par le cahier des charges lui-même : on voulait « des composés
3D, 2D ou 1D voire 0D (moléculaires) ». Ce script mesure ce que la méthode
donne vraiment, concentration de lacunes par concentration de lacunes, au lieu
de l'espérer.

Deux lectures, et il faut les deux :
  - avec contrainte ternaire (le cahier des charges) ;
  - sans (pour voir ce que la contrainte ternaire interdit, ce qui est
    informatif : les clusters 0D de ce réseau sont pauvres en carbone pour une
    raison structurale, cf. l'analyse du carbone de la maille d'anneau).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dia_cno import jumeau
from dia_cno.lattice import demi_liaisons, permutations_symetrie, supermaille
from dia_cno.templates import construit, primitive, signature
from dia_cno.vacancies import classes_de_lacunes, coordinences, decorations


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mailles", nargs="+", default=["2x1x1", "2x2x1"])
    ap.add_argument("--kmax", type=int, default=6)
    ap.add_argument("--motifs", nargs="+", default=["canonique"])
    ap.add_argument("--zmin", type=int, default=2)
    args = ap.parse_args()

    jumeau()
    from cno_csp.geometry import dimensionality

    for m in args.mailles:
        n = tuple(int(x) for x in m.lower().split("x"))
        parent = supermaille(n)
        adj = demi_liaisons(parent)
        P = permutations_symetrie(parent)
        niveaux = classes_de_lacunes(P, len(parent), adj, args.kmax, z_min=args.zmin)
        print(f"\n=== dia{n[0]}{n[1]}{n[2]} : {len(parent)} sites, motifs {args.motifs}")
        print(f"{'k':>2} {'% lac.':>7} {'atomes':>7} {'ternaires':>10} {'tous':>6}   "
              f"dimensionnalité (ternaires)      dimensionnalité (tous)")
        for k in range(1, args.kmax + 1):
            par_dim: dict[bool, Counter] = {True: Counter(), False: Counter()}
            vus: dict[bool, set] = {True: set(), False: set()}
            for V in niveaux[k]:
                z = coordinences(adj, frozenset(V))
                if not z or min(z.values()) < args.zmin:
                    continue
                for tern in (True, False):
                    for dec in decorations(adj, V, z_min=args.zmin,
                                           motifs=tuple(args.motifs),
                                           require_ternary=tern):
                        enfant = primitive(construit(parent, dec))
                        sig = signature(enfant)
                        if sig is None or sig in vus[tern]:
                            continue
                        vus[tern].add(sig)
                        par_dim[tern][dimensionality(enfant)] += 1
            fmt = lambda c: " ".join(f"{d}D:{v}" for d, v in sorted(c.items(), reverse=True)) or "-"
            print(f"{k:>2} {k/len(parent):>6.1%} {len(parent)-k:>7} "
                  f"{sum(par_dim[True].values()):>10} {sum(par_dim[False].values()):>6}   "
                  f"{fmt(par_dim[True]):<32} {fmt(par_dim[False])}")


if __name__ == "__main__":
    main()
