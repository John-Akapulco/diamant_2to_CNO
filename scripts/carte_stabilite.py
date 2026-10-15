#!/usr/bin/env python3
"""
Où, dans le simplexe C-N-O, la famille lacunaire peut-elle être stable ?

    python scripts/carte_stabilite.py runs/vm1_lot2

La question n'est pas « à quelle distance de l'enveloppe est telle
composition » mais « quelle RÉGION de composition est favorable ». Et elle a
une réponse qui ne dépend d'AUCUN potentiel chimique, ce qui règle du même
coup le problème des références (cf. REFERENCES.md) :

    on construit l'enveloppe convexe inférieure des énergies de nos propres
    structures, dans l'espace (x_N, x_O, E/atome), en y ajoutant le diamant
    comme sommet x_C = 1.

Une composition SUR cette enveloppe ne se décompose pas en d'autres membres de
la famille : elle est stable vis-à-vis de la dismutation. Une composition
au-dessus s'y décompose, et aucun choix de référence ne peut l'en sauver --
décaler les μ décale toutes les énergies d'une fonction affine de la
composition, ce qui laisse l'enveloppe et les distances inchangées.

C'est donc la carte reference-free de la métastabilité à travers le simplexe.
Le ΔE_dec contre {graphite, N2, CO2, O2} reste reporté à côté, parce que c'est
lui qui dit si la structure survit face aux GAZ -- mais c'est lui qui porte
l'erreur sur μ_N et μ_O, pas celui-ci.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from math import gcd
from pathlib import Path

import numpy as np


def reduite(formule: str) -> tuple[int, int, int]:
    """(C, N, O) de la formule réduite, à partir d'une formule ASE."""
    import re
    n = {"C": 0, "N": 0, "O": 0}
    for sym, cnt in re.findall(r"([A-Z][a-z]?)(\d*)", formule):
        if sym in n:
            n[sym] += int(cnt) if cnt else 1
    d = 0
    for v in n.values():
        d = gcd(d, v)
    d = d or 1
    return (n["C"] // d, n["N"] // d, n["O"] // d)


def enveloppe_inferieure(pts: np.ndarray):
    """
    Facettes de l'enveloppe convexe INFÉRIEURE de points (u, v, e).

    Rend une fonction (u, v) -> e_enveloppe. L'enveloppe inférieure convexe
    est le supremum des fonctions affines qui passent sous tous les points,
    donc le max des plans porteurs des facettes basses.
    """
    from scipy.spatial import ConvexHull

    h = ConvexHull(pts)
    plans = []
    for eq in h.equations:                 # a*u + b*v + c*e + d = 0
        a, b, c, d = eq
        if c < -1e-10:                     # normale vers le bas : facette basse
            plans.append((-a / c, -b / c, -d / c))   # e = alpha*u + beta*v + gamma
    if not plans:
        raise RuntimeError("aucune facette inférieure")

    def valeur(u, v):
        return max(al * u + be * v + ga for al, be, ga in plans)

    return valeur, len(plans)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier")
    ap.add_argument("--e-diamant", type=float, default=-9.0746,
                    help="énergie/atome du diamant au même niveau (MACE sans D3)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    src = Path(args.dossier)
    vus, res = set(), []
    for f in sorted(src.glob("*.json")):
        for r in json.loads(f.read_text()).get("resultats", []):
            cle = (r["source_id"], r["decoration"])
            if cle in vus:
                continue
            vus.add(cle)
            if not r["converged"] or not r["valide"] or r.get("anomalies"):
                continue
            res.append(r)

    # meilleure structure par composition réduite
    par_comp: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    for r in res:
        par_comp[reduite(r["formula"])].append(r)

    lignes = []
    for comp, rs in par_comp.items():
        best = min(rs, key=lambda r: r["e_per_atom"])
        t = sum(comp)
        lignes.append({
            "comp": comp, "x_C": comp[0] / t, "x_N": comp[1] / t, "x_O": comp[2] / t,
            "n_polymorphes": len(rs),
            "e_per_atom": best["e_per_atom"],
            "e_dec": min(r["e_decomposition"] for r in rs),
            "v_per_atom": min(r["v_per_atom"] for r in rs),
            "n_atoms": best["n_atoms"],
            "formule": best["formula"],
        })

    # enveloppe interne : nos points + le diamant comme sommet x_C = 1
    pts = np.array([[l["x_N"], l["x_O"], l["e_per_atom"]] for l in lignes]
                   + [[0.0, 0.0, args.e_diamant]])
    val, n_facettes = enveloppe_inferieure(pts)
    for l in lignes:
        l["d_hull"] = l["e_per_atom"] - val(l["x_N"], l["x_O"])

    lignes.sort(key=lambda l: (l["d_hull"], -l["x_C"]))
    sommets = [l for l in lignes if l["d_hull"] < 1e-6]

    txt = []
    txt.append(f"# Carte de stabilité dans le simplexe C-N-O — lot {src.name}\n")
    txt.append(f"- structures retenues : **{len(res)}**, sur "
               f"**{len(par_comp)} compositions réduites** distinctes")
    txt.append(f"- enveloppe convexe interne : {n_facettes} facettes inférieures, "
               f"diamant inclus comme sommet x_C = 1")
    txt.append(f"- **compositions SUR l'enveloppe : {len(sommets)}**\n")
    txt.append("`d_hull` = distance au-dessus de l'enveloppe convexe de **nos "
               "propres** structures + diamant. **Aucun potentiel chimique "
               "n'intervient**, donc aucun choix de référence ne peut changer "
               "cette colonne. Une composition à d_hull > 0 se décompose en "
               "d'autres membres de la famille.\n")
    txt.append("`ΔE_dec` = distance au-dessus de {graphite, N2, CO2, O2}, "
               "reportée pour mémoire : c'est elle qui dit la survie face aux "
               "gaz, et c'est elle qui porte l'erreur sur μ_N et μ_O.\n")
    txt.append("| composition | x_C | x_N | x_O | polym. | V/at | **d_hull** | ΔE_dec | sur l'enveloppe |")
    txt.append("|---|---|---|---|---|---|---|---|---|")
    for l in lignes:
        c = l["comp"]
        txt.append(f"| C{c[0]}N{c[1]}O{c[2]} | {l['x_C']:.3f} | {l['x_N']:.3f} | "
                   f"{l['x_O']:.3f} | {l['n_polymorphes']} | {l['v_per_atom']:.2f} | "
                   f"**{l['d_hull']:+.3f}** | {l['e_dec']:+.3f} | "
                   f"{'**oui**' if l['d_hull'] < 1e-6 else ''} |")

    # tendances : régression de d_hull et de e_dec sur la composition
    A = np.array([[l["x_N"], l["x_O"], 1.0] for l in lignes])
    for nom, col in (("d_hull", "d_hull"), ("ΔE_dec", "e_dec")):
        b = np.array([l[col] for l in lignes])
        coef, *_ = np.linalg.lstsq(A, b, rcond=None)
        pred = A @ coef
        r2 = 1 - ((b - pred) ** 2).sum() / ((b - b.mean()) ** 2).sum()
        txt.append(f"\nTendance linéaire de **{nom}** : "
                   f"{coef[0]:+.3f}·x_N {coef[1]:+.3f}·x_O {coef[2]:+.3f}  (R² = {r2:.2f})")

    sortie = "\n".join(txt) + "\n"
    print(sortie)
    if args.out:
        Path(args.out).write_text(sortie)
        json_out = Path(args.out).with_suffix(".json")
        json_out.write_text(json.dumps(lignes, indent=2))
        print(f"-> {args.out} et {json_out}")


if __name__ == "__main__":
    main()
