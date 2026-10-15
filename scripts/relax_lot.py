#!/usr/bin/env python3
"""
Relaxe un lot de templates au MACE, valide, et calcule les enthalpies de formation.

    PYTHONPATH=. python scripts/relax_lot.py templates_dia --out runs/lot1.json

Relaxation : positions + volume + forme de maille (FrechetCellFilter), à 0 GPa,
fmax = 1e-3 eV/Å -- le seuil serré du projet jumeau, nécessaire parce qu'on
tranche "N pyramidal vs N plan" sur quelques degrés de somme d'angles.

Dispersion : D3 pour les pools 0D/1D/2D, MACE seul pour les charpentes 3D.
C'est la doctrine du projet jumeau, et elle n'est pas cosmétique : sans
dispersion rien ne retient feuillets et chaînes, la maille gonfle sans limite
physique. Les potentiels chimiques sont pris AU MÊME niveau que la structure
qu'ils servent à évaluer, jamais mélangés.

Sorties par structure : E/atome, V/atome, E_f (contre graphite + N2 + O2),
DeltaE_dec (au-dessus de l'enveloppe graphite + N2 + CO2 + O2), verdict du
validateur, et conservation site par site de la coordinence décorée.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ase.io import read as ase_read

from dia_cno import jumeau


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("templates")
    ap.add_argument("--out", default="runs/lot.json")
    ap.add_argument("--fmax", type=float, default=1e-3)
    ap.add_argument("--limite", type=int, default=0, help="0 = tout le lot")
    args = ap.parse_args()

    racine = jumeau()
    sys.path.insert(0, str(racine / "scripts"))
    from cno_csp.config import GeometryThresholds
    from cno_csp.relax import relax
    from cno_csp.validator import validate
    from funnel_table import e_decomposition, mu_elements

    th = GeometryThresholds(allow_planar_n=True, allow_bent_n=True,
                            allow_terminal_o=True)
    src = Path(args.templates)
    man = json.loads((src / "templates_manifest.json").read_text())
    if args.limite:
        man = man[:args.limite]

    mu_cache: dict[bool, dict] = {}

    def mu(disp: bool) -> dict:
        if disp not in mu_cache:
            print(f"  potentiels chimiques (D3={disp})...", flush=True)
            mu_cache[disp] = mu_elements(disp)
        return mu_cache[disp]

    resultats = []
    for e in man:
        nom = f"{e['source_id']}_{e['decoration']}_{e['child_formula']}.cif"
        atoms = ase_read(src / "cif" / nom)
        disp = (e.get("dimensionality") or 3) < 3
        r = relax(atoms, pressure_gpa=0.0, fmax=args.fmax, dispersion=disp)
        n = Counter(r.atoms.get_chemical_symbols())
        m = mu(disp)
        ef = (r.energy - sum(n[s] * m[s] for s in n)) / len(r.atoms)
        dec = e_decomposition(n, r.energy, m, disp)
        rep = validate(r.atoms, th)
        res = {
            "source_id": e["source_id"], "decoration": e["decoration"],
            "formula": r.atoms.get_chemical_formula(),
            "n_atoms": len(r.atoms), "dimensionality": e.get("dimensionality"),
            "dispersion": disp, "converged": r.converged, "n_steps": r.n_steps,
            "e_per_atom": r.energy / len(r.atoms),
            "v_per_atom": r.volume / len(r.atoms),
            "v_per_atom_template": e.get("v_per_atom"),
            "e_formation": ef,
            "e_decomposition": dec if isinstance(dec, float) else None,
            "valide": bool(rep.ok),
            "raison": "" if rep.ok else "; ".join(
                f"{v.symbol}{v.index}:{v.message}" for v in rep.violations[:4]),
        }
        resultats.append(res)
        print(f"{res['formula']:12s} {e['decoration'][:34]:34s} "
              f"V/at={res['v_per_atom']:5.2f} E_f={ef:+.3f} "
              f"dec={res['e_decomposition'] if res['e_decomposition'] is None else round(res['e_decomposition'], 3)} "
              f"{'OK ' if rep.ok else 'KO '}{'conv' if r.converged else 'NC'}", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"mu": {k: v for d in mu_cache.values() for k, v in d.items()},
                               "resultats": resultats}, indent=2, ensure_ascii=False))
    print(f"\n{len(resultats)} structures -> {out}")


if __name__ == "__main__":
    main()
