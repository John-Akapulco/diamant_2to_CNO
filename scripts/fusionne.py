#!/usr/bin/env python3
"""
Fusionne plusieurs jeux de templates en dédoublonnant par signature de prototype.

    python scripts/fusionne.py templates_dia_t2 templates_dia_t2a templates_dia_t2b

gen_templates.py dédoublonne À L'INTÉRIEUR d'un appel, mais pas entre deux
appels -- et il faut bien deux appels dès qu'on veut un k_max différent par
taille de maille (k=6 en 32 sites, k=4 en 64 : la même valeur partout serait
soit trop pauvre, soit intraitable). La signature (groupe d'espace, orbites de
Wyckoff décorées) est recalculée ici, donc la fusion est exacte et pas
approchée par le nom de fichier.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ase.io import read as ase_read

from dia_cno.templates import signature


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sortie")
    ap.add_argument("sources", nargs="+")
    args = ap.parse_args()

    out = Path(args.sortie)
    if out.exists():
        shutil.rmtree(out)
    (out / "cif").mkdir(parents=True)

    vus, garde, stats = set(), [], Counter()
    for s in args.sources:
        src = Path(s)
        man = json.loads((src / "templates_manifest.json").read_text())
        for e in man:
            nom = f"{e['source_id']}_{e['decoration']}_{e['child_formula']}.cif"
            sig = signature(ase_read(src / "cif" / nom))
            stats[src.name] += 1
            if sig is None or sig in vus:
                stats["doublons"] += 1
                continue
            vus.add(sig)
            shutil.copy(src / "cif" / nom, out / "cif" / nom)
            garde.append(e)
    (out / "templates_manifest.json").write_text(
        json.dumps(garde, indent=2, ensure_ascii=False))

    print(f"sources : {dict(stats)}")
    print(f"dimensionnalité : {dict(sorted(Counter(e['dimensionality'] for e in garde).items(), reverse=True))}")
    print(f"sans interaction d'images : {sum(1 for e in garde if not e['images_en_interaction'])}/{len(garde)}")
    print(f"tailles : {dict(sorted(Counter(e['n_atoms'] for e in garde).items()))}")
    print(f"\n{len(garde)} templates -> {out}/")


if __name__ == "__main__":
    main()
