#!/usr/bin/env python3
"""
Engendre les templates : lacunes dans une supermaille de diamant, décoration C/N/O.

    PYTHONPATH=. python scripts/gen_templates.py --mailles 1x1x1 2x1x1 2x2x1 \
        --kmax 3 --motifs canonique --out templates_dia

Écrit <out>/cif/*.cif et <out>/templates_manifest.json, au format du projet
jumeau, donc directement consommable par ses pools_dim.py / relaxation /
phonons / lot_dft.py.

Le pipeline, dans l'ordre : énumération des ensembles de lacunes à symétrie
près -> décorations admissibles au sens de Lewis -> construction et remise à
l'échelle -> réduction à la maille primitive -> déduplication par signature
de prototype -> écriture.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ase.io import write as ase_write

from dia_cno import jumeau
from dia_cno.lattice import permutations_symetrie, supermaille, voisins
from dia_cno.templates import (Template, construit, homonucleaire, primitive,
                               signature)
from dia_cno.vacancies import classes_de_lacunes, decorations


def parse_maille(s: str) -> tuple[int, int, int]:
    a, b, c = (int(x) for x in s.lower().split("x"))
    return (a, b, c)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mailles", nargs="+", default=["1x1x1", "2x1x1", "2x2x1"])
    ap.add_argument("--kmax", type=int, default=3, help="nombre maximal de lacunes")
    ap.add_argument("--motifs", nargs="+", default=["canonique"],
                    choices=["canonique", "sp2", "nbent", "oterm"])
    ap.add_argument("--zmin", type=int, default=2,
                    help="coordinence minimale tolérée (1 n'a de sens qu'avec oterm)")
    ap.add_argument("--max-atomes", type=int, default=24,
                    help="plafond d'atomes par maille primitive (coût DFT)")
    ap.add_argument("--ternaire", action="store_true",
                    help="n'accepter que les structures contenant C et N et O")
    ap.add_argument("--out", default="templates_dia")
    args = ap.parse_args()

    jumeau()
    from cno_csp.geometry import dimensionality

    motifs = tuple(args.motifs)
    out = Path(args.out)
    (out / "cif").mkdir(parents=True, exist_ok=True)

    vus: dict = {}
    retenus: list[Template] = []
    stats = Counter()

    for m in args.mailles:
        n = parse_maille(m)
        parent = supermaille(n)
        adj = voisins(parent)
        P = permutations_symetrie(parent)
        niveaux = classes_de_lacunes(P, len(parent), adj, args.kmax, z_min=args.zmin)
        sid = f"dia{n[0]}{n[1]}{n[2]}"
        print(f"[{sid}] {len(parent)} sites, {len(P)} opérations de symétrie")

        for k in range(1, args.kmax + 1):
            for V in niveaux[k]:
                stats["lacunes"] += 1
                decs = decorations(adj, V, z_min=args.zmin, motifs=motifs,
                                   require_ternary=args.ternaire)
                if not decs:
                    stats["sans_decoration"] += 1
                for dec in decs:
                    stats["decorations"] += 1
                    enfant = primitive(construit(parent, dec))
                    if len(enfant) > args.max_atomes:
                        stats["trop_gros"] += 1
                        continue
                    sig = signature(enfant)
                    if sig is None:
                        stats["sans_symetrie"] += 1
                        continue
                    if sig in vus:
                        stats["doublons"] += 1
                        continue
                    vus[sig] = dec.label
                    sym = Counter(enfant.get_chemical_symbols())
                    t = Template(
                        atoms=enfant, source_id=sid, decoration=dec.label,
                        formula=enfant.get_chemical_formula(),
                        spacegroup=sig[0], n_atoms=len(enfant),
                        v_per_atom=enfant.get_volume() / len(enfant),
                        composition=(sym["C"], sym["N"], sym["O"]),
                        classes=dec.classes,
                        dimensionality=dimensionality(enfant),
                        flags=homonucleaire(enfant))
                    retenus.append(t)
                    stats["retenus"] += 1

    for t in retenus:
        nom = f"{t.source_id}_{t.decoration}_{t.formula}.cif"
        ase_write(out / "cif" / nom, t.atoms)
    (out / "templates_manifest.json").write_text(
        json.dumps([t.manifest_entry() for t in retenus], indent=2, ensure_ascii=False))

    print("\n" + "-" * 72)
    for cle, v in sorted(stats.items()):
        print(f"  {cle:18s} {v}")
    par_dim = Counter(t.dimensionality for t in retenus)
    print(f"  dimensionnalité    {dict(sorted(par_dim.items(), reverse=True))}")
    print(f"\n{len(retenus)} templates -> {out}/")


if __name__ == "__main__":
    main()
