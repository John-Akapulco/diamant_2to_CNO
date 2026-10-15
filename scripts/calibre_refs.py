#!/usr/bin/env python3
"""
Mesure l'erreur de MACE sur l'enthalpie de formation de solides de référence.

    python scripts/calibre_refs.py --refs cache/refs_mp.json

But : chiffrer l'erreur des potentiels chimiques tirés de N2 et O2 ISOLÉS, en
s'appuyant sur des composés CRISTALLINS à liaisons simples dont l'enthalpie de
formation expérimentale est connue, puis en déduire les corrections δ_N et δ_O.

N2 et O2 sont les deux pires cas possibles pour ce genre de potentiel :
triple liaison pour l'un, état fondamental triplet pour l'autre, et tous deux
hors du domaine d'entraînement de MACE-MP (solides périodiques). Voir
REFERENCES.md pour le raisonnement complet et les références proposées.

ATTENTION aux enthalpies expérimentales ci-dessous : elles sont par FORMULE,
et une maille de Materials Project en contient souvent plusieurs. L'erreur est
facile à faire et change tout -- elle a été faite ici une première fois.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from math import gcd
from pathlib import Path

EV_PAR_KJMOL = 1.0 / 96.485

# Enthalpies de formation standard, kJ/mol de FORMULE (CODATA/NIST).
# À recontrôler sur table avant toute publication.
EXP_KJ_MOL = {
    "Si3N4": -744.8,    # beta-Si3N4
    "SiO2": -910.7,     # alpha-quartz
    "AlN": -318.0,      # wurtzite
    "Al2O3": -1675.7,   # corindon
    "MgO": -601.6,      # periclase
    "BN": -254.4,       # hexagonal
}
LAMELLAIRE = {"BN"}
ELEMENTS = {"Si", "Al", "Mg", "B"}


def par_formule(symbols: list[str]) -> tuple[Counter, int]:
    """Composition par formule réduite, et nombre de formules dans la maille."""
    n = Counter(symbols)
    d = 0
    for v in n.values():
        d = gcd(d, v)
    return Counter({k: v // d for k, v in n.items()}), d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refs", default="cache/refs_mp.json")
    ap.add_argument("--out", default="cache/calibration.json")
    args = ap.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from dia_cno import jumeau
    jumeau()

    from ase import Atoms
    from ase.build import bulk
    from ase.optimize import LBFGS
    from pymatgen.core import Structure
    from pymatgen.io.ase import AseAtomsAdaptor
    from cno_csp.relax import get_calculator, relax

    refs = json.loads(Path(args.refs).read_text())
    resultat = {}

    for disp in (False, True):
        niveau = f"D3{int(disp)}"
        print(f"\n{'='*86}\nMACE {'+ D3' if disp else 'seul'}")
        E, NAT = {}, {}
        for cle, sdict in refs.items():
            nom = cle.split("_")[0]
            if nom not in EXP_KJ_MOL and nom not in ELEMENTS:
                continue
            if nom in E:
                continue
            at = AseAtomsAdaptor.get_atoms(Structure.from_dict(sdict))
            r = relax(at, pressure_gpa=0.0, fmax=1e-3, dispersion=disp)
            E[nom] = r.energy / len(r.atoms)
            NAT[nom] = r.atoms.get_chemical_symbols()

        g = Atoms("C4", scaled_positions=[[0, 0, 0], [1/3, 2/3, 0],
                                          [0, 0, .5], [2/3, 1/3, .5]],
                  cell=[[2.46, 0, 0], [-1.23, 2.1304, 0], [0, 0, 6.7]], pbc=True)
        E["C_graphite"] = relax(g, dispersion=disp).energy / 4
        E["C_diamant"] = relax(bulk("C", "diamond", a=3.567), dispersion=disp).energy / 2
        for sym, d0 in (("N", 1.10), ("O", 1.21)):
            m = Atoms(f"{sym}2", positions=[[0, 0, 0], [0, 0, d0]],
                      cell=[12.0] * 3, pbc=True)
            m.calc = get_calculator("mace", dispersion=disp)
            LBFGS(m, logfile=None).run(fmax=1e-3, steps=400)
            E[sym] = float(m.get_potential_energy()) / 2

        mu = {e: E[e] for e in ELEMENTS if e in E}
        mu.update({"C": E["C_graphite"], "N": E["N"], "O": E["O"]})

        print(f"μ_C graphite {mu['C']:+.4f}   diamant {E['C_diamant']:+.4f}   "
              f"écart calculé {E['C_diamant']-mu['C']:+.4f} (expérimental +0.0196)")
        print(f"\n{'composé':9s} {'form.':7s} {'H_f MACE':>9s} {'H_f exp':>9s} "
              f"{'écart':>7s} {'x_N':>5s} {'x_O':>5s} {'δ implicite':>12s}")
        lignes = []
        for nom, hkj in EXP_KJ_MOL.items():
            if nom not in E:
                continue
            form, nf = par_formule(NAT[nom])
            nat_f = sum(form.values())
            hf_mace = E[nom] - sum(form[s] * mu[s] for s in form) / nat_f
            hf_exp = hkj * EV_PAR_KJMOL / nat_f
            ecart = hf_mace - hf_exp
            xn, xo = form["N"] / nat_f, form["O"] / nat_f
            delta = ecart / (xn + xo) if (xn + xo) else float("nan")
            flag = "  [lamellaire]" if nom in LAMELLAIRE else ""
            print(f"{nom:9s} {''.join(f'{k}{v}' for k, v in sorted(form.items())):7s} "
                  f"{hf_mace:+9.3f} {hf_exp:+9.3f} {ecart:+7.3f} {xn:5.3f} {xo:5.3f} "
                  f"{delta:+12.3f}{flag}")
            lignes.append({"compose": nom, "hf_mace": hf_mace, "hf_exp": hf_exp,
                           "ecart": ecart, "x_N": xn, "x_O": xo, "delta": delta})

        # Potentiel chimique de l'élément léger EN ÉQUILIBRE avec le composé.
        # ATTENTION : ce n'est PAS un meilleur μ_N ou μ_O, c'est une condition
        # thermodynamique différente -- l'écart avec le brut vaut exactement
        # l'enthalpie de formation du composé rapportée à l'élément. Imprimé
        # pour le montrer, pas pour être utilisé comme référence. Cf.
        # REFERENCES.md §1(b).
        extraits = {}
        if "Si3N4" in E and "Si" in E:
            f, _ = par_formule(NAT["Si3N4"])
            extraits["N via Si3N4"] = (E["Si3N4"] * sum(f.values()) - f["Si"] * mu["Si"]) / f["N"]
        if "AlN" in E and "Al" in E:
            f, _ = par_formule(NAT["AlN"])
            extraits["N via AlN"] = (E["AlN"] * sum(f.values()) - f["Al"] * mu["Al"]) / f["N"]
        if "SiO2" in E and "Si" in E:
            f, _ = par_formule(NAT["SiO2"])
            extraits["O via SiO2"] = (E["SiO2"] * sum(f.values()) - f["Si"] * mu["Si"]) / f["O"]
        if "MgO" in E and "Mg" in E:
            f, _ = par_formule(NAT["MgO"])
            extraits["O via MgO"] = (E["MgO"] * sum(f.values()) - f["Mg"] * mu["Mg"]) / f["O"]
        print(f"\nμ en équilibre avec le composé — PAS un substitut de μ(N2)/μ(O2),")
        print(f"l'écart vaut l'enthalpie de formation rapportée à l'élément :")
        for k, v in extraits.items():
            brut = mu["N"] if k.startswith("N") else mu["O"]
            print(f"   {k:14s} {v:+9.4f}   brut {brut:+9.4f}   écart {v-brut:+.3f}")

        resultat[niveau] = {"mu": mu, "E": {k: v for k, v in E.items()},
                            "composes": lignes, "mu_extraits": extraits}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(resultat, indent=2))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
