#!/usr/bin/env python3
"""
Rassemble les JSON de shards d'un lot et en fait un classement.

    python scripts/bilan.py runs/vm1 --out runs/vm1/CLASSEMENT.md

Trie par DeltaE_dec croissant -- la distance au-dessus de l'enveloppe
{graphite, N2, CO2, O2} -- et non par E_f, qui dégénère vers le diamant dès
qu'on la minimise seule (cf. CONCEPTION.md §11).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    src = Path(args.dossier)
    res, refs = [], {}
    vus = set()
    for f in sorted(src.glob("*.json")):
        d = json.loads(f.read_text())
        refs.update(d.get("references", {}))
        for r in d.get("resultats", []):
            cle = (r["source_id"], r["decoration"])
            if cle in vus:          # le calcul des références traite 1 structure
                continue            # qui réapparaît dans un shard
            vus.add(cle)
            res.append(r)
    res.sort(key=lambda r: r["e_decomposition"])

    lignes = []
    lignes.append(f"# Lot {src.name} : {len(res)} structures\n")
    ok = sum(1 for r in res if r["valide"])
    conv = sum(1 for r in res if r["converged"])
    dim = Counter(r["dimensionality"] for r in res)
    img = sum(1 for r in res if r.get("images_en_interaction"))
    lignes.append(f"- convergées à f_max : **{conv}/{len(res)}**")
    lignes.append(f"- validées (tous les sites dans un environnement visé) : **{ok}/{len(res)}**")
    lignes.append(f"- dimensionnalité des templates : {dict(sorted(dim.items(), reverse=True))}")
    lignes.append(f"- sans interaction d'images (maille assez grande) : {len(res)-img}/{len(res)}\n")
    lignes.append("Trié par ΔE_dec, distance au-dessus de l'enveloppe "
                  "{graphite, N2, CO2, O2}. E_f est donné pour mémoire : le "
                  "minimiser seul dégénère vers le diamant.\n")
    lignes.append("| # | structure | at. | dim | D3 | V/at (Å³) | E_f | ΔE_dec | valide | conv |")
    lignes.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(res, 1):
        lignes.append(
            f"| {i} | {r['formula']} | {r['n_atoms']} | {r['dimensionality']}D | "
            f"{'D3' if r['dispersion'] else '—'} | {r['v_per_atom']:.2f} | "
            f"{r['e_formation']:+.3f} | **{r['e_decomposition']:+.3f}** | "
            f"{'ok' if r['valide'] else '**KO**'} | {'oui' if r['converged'] else 'NON'} |")
    if refs:
        lignes.append("\n## Contrôle des potentiels chimiques\n")
        lignes.append("| niveau | espèce | E_f calculé | E_f expérimental | écart |")
        lignes.append("|---|---|---|---|---|")
        for niv, d in sorted(refs.items()):
            for c in d.get("controle", []):
                lignes.append(f"| {niv} | {c['espece']} | {c['ef_calc']:+.3f} | "
                              f"{c['ef_exp']:+.3f} | {c['ef_calc']-c['ef_exp']:+.3f} |")
        lignes.append("\nC'est la barre d'erreur à garder en tête sur toute cette "
                      "table : N2 et O2 isolés sont hors du domaine d'entraînement "
                      "de MACE-MP et entrent dans μ_N et μ_O.")

    texte = "\n".join(lignes) + "\n"
    print(texte)
    if args.out:
        Path(args.out).write_text(texte)
        print(f"-> {args.out}")


if __name__ == "__main__":
    main()
