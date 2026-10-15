#!/usr/bin/env python3
"""
Relaxe un lot de templates au MACE, valide, et calcule les enthalpies de formation.

    # local, un seul processus
    python scripts/relax_lot.py templates_dia --out runs/lot1.json

    # un shard parmi 20 (Yargla : parallélisation PAR PROCESSUS, cf. hpc/)
    python scripts/relax_lot.py templates_dia --out runs/lot1.json --shard 3/20

Sur un calculateur ce script ne se lance JAMAIS à la main : il se lance par
sbatch, depuis hpc/yargla_lot.slurm ou hpc/vm1_lot.slurm. Le nœud de connexion
sert à transférer, soumettre et consulter, pas à calculer, et garde_noeud_de_connexion()
le fait respecter. Règles complètes dans hpc/README.md.

Relaxation : positions + volume + forme de maille (FrechetCellFilter), à 0 GPa,
fmax = 1e-3 eV/Å -- le seuil serré du projet jumeau, nécessaire parce qu'on
tranche « N pyramidal vs N plan » sur quelques degrés de somme d'angles.

Dispersion : D3 pour les pools 0D/1D/2D, MACE seul pour les charpentes 3D.
C'est la doctrine du projet jumeau, et elle n'est pas cosmétique : sans
dispersion rien ne retient feuillets et chaînes, la maille gonfle sans limite
physique. Les potentiels chimiques sont pris AU MÊME niveau que la structure
qu'ils servent à évaluer, jamais mélangés -- d'où deux jeux (avec et sans D3),
mis en cache sur disque parce que chaque jeu coûte six relaxations de
référence et que tous les shards en ont besoin.

Sorties par structure : E/atome, V/atome, E_f (contre graphite + N2 + O2),
ΔE_dec (au-dessus de l'enveloppe graphite + N2 + CO2 + O2), verdict du
validateur. Le fichier porte aussi le contrôle controle_mu : l'enthalpie de
formation recalculée de CO2 et N2O, dont la valeur expérimentale est connue.
Sans ce contrôle, « E_f = +0.08 eV/atome » se lit comme une mesure alors que
c'est une estimation à une ou deux dixièmes d'eV près.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ase.io import read as ase_read

from dia_cno import jumeau


def garde_noeud_de_connexion(force: bool) -> None:
    """
    Refuse de calculer sur un nœud de connexion.

    Le nœud de connexion d'un calculateur sert à transférer, soumettre et
    consulter ; il est partagé par tous les utilisateurs et n'a ni les cœurs ni
    l'isolation d'un nœud de production. Une relaxation MACE y dégrade la
    machine pour tout le monde -- et les six relaxations de référence
    (graphite, diamant, N2, O2, CO2, N2O) sont des calculs à part entière.

    Critère : la machine a `sbatch` mais l'environnement n'a pas de
    SLURM_JOB_ID. C'est exactement « je suis sur un calculateur, hors job ».
    Sur le Mac il n'y a pas de sbatch, donc rien ne change.
    """
    import shutil

    if force or os.environ.get("SLURM_JOB_ID") or not shutil.which("sbatch"):
        return
    print("REFUS : ce script calcule, et cette machine a SLURM sans job en cours.\n"
          "        Un nœud de connexion sert à transférer, soumettre et consulter.\n"
          "        Soumettre plutôt :\n"
          "          sbatch --export=ALL,TEMPLATES=<lot>,N_SHARDS=20,OUT=runs/<nom>.json \\\n"
          "                 code/hpc/yargla_lot.slurm\n"
          "        Voir hpc/README.md. En dernier recours : --hors-slurm.",
          file=sys.stderr)
    raise SystemExit(2)


def charge_mu(disp: bool, cache: Path) -> dict:
    """
    Potentiels chimiques + contrôle, avec cache disque.

    Six relaxations de référence (graphite, diamant, N2, O2, CO2, N2O) par
    niveau de théorie. Les recalculer dans chaque shard est du temps perdu, et
    surtout un risque d'incohérence si deux shards n'obtenaient pas exactement
    la même valeur.
    """
    f = cache / f"mu_D3{int(disp)}.json"
    if f.exists():
        return json.loads(f.read_text())
    from funnel_table import controle_mu, mu_elements

    print(f"  références (D3={disp}) : graphite, diamant, N2, O2, CO2, N2O...", flush=True)
    mu = mu_elements(disp)
    ctrl, e_mol = controle_mu(mu, disp)
    data = {"mu": mu, "e_mol": e_mol,
            "controle": [{"espece": n, "ef_calc": e, "ef_exp": x} for n, e, x in ctrl]}
    cache.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2))
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("templates")
    ap.add_argument("--out", default="runs/lot.json")
    ap.add_argument("--fmax", type=float, default=1e-3)
    ap.add_argument("--limite", type=int, default=0, help="0 = tout le lot")
    ap.add_argument("--shard", default="", metavar="k/N",
                    help="ne traiter qu'un sous-ensemble (entrelacé, pour que "
                         "chaque shard reçoive un mélange de petites et grandes mailles)")
    ap.add_argument("--cache", default="cache")
    ap.add_argument("--hors-slurm", action="store_true",
                    help="forcer l'exécution sur un nœud de connexion (diagnostic "
                         "très court seulement, cf. hpc/README.md)")
    args = ap.parse_args()

    garde_noeud_de_connexion(args.hors_slurm)

    racine = jumeau()
    sys.path.insert(0, str(racine / "scripts"))
    from cno_csp.config import GeometryThresholds
    from cno_csp.relax import relax
    from cno_csp.validator import validate
    from funnel_table import e_decomposition

    th = GeometryThresholds(allow_planar_n=True, allow_bent_n=True,
                            allow_terminal_o=True)
    src = Path(args.templates)
    man = json.loads((src / "templates_manifest.json").read_text())
    # croissant en nombre d'atomes : les structures bon marché d'abord, pour
    # qu'un lot interrompu ait quand même couvert les petites mailles.
    man.sort(key=lambda e: e["n_atoms"])
    if args.limite:
        man = man[:args.limite]

    out = Path(args.out)
    if args.shard:
        k, n = (int(x) for x in args.shard.split("/"))
        man = man[k::n]          # entrelacé, et non par tranche : sinon un
                                 # shard hérite de toutes les grandes mailles
        out = out.with_name(f"{out.stem}_s{k}{out.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)

    cache = Path(args.cache)
    refs: dict[bool, dict] = {}

    resultats = []
    for e in man:
        nom = f"{e['source_id']}_{e['decoration']}_{e['child_formula']}.cif"
        atoms = ase_read(src / "cif" / nom)
        disp = (e.get("dimensionality") or 3) < 3
        if disp not in refs:
            refs[disp] = charge_mu(disp, cache)
        ref = refs[disp]
        mu, e_co2 = ref["mu"], ref["e_mol"]["CO2"]

        r = relax(atoms, pressure_gpa=0.0, fmax=args.fmax, dispersion=disp)
        n_at = Counter(r.atoms.get_chemical_symbols())
        ef = (r.energy - sum(n_at[s] * mu[s] for s in n_at)) / len(r.atoms)
        # e_co2 et NON le drapeau de dispersion : la signature de
        # e_decomposition attend l'énergie TOTALE d'une molécule de CO2.
        dec = e_decomposition(n_at, r.energy, mu, e_co2)
        rep = validate(r.atoms, th)
        res = {
            "source_id": e["source_id"], "decoration": e["decoration"],
            "formula": r.atoms.get_chemical_formula(),
            "n_atoms": len(r.atoms), "dimensionality": e.get("dimensionality"),
            "images_en_interaction": e.get("images_en_interaction"),
            "n_lacunes": e.get("n_lacunes"), "dispersion": disp,
            "converged": r.converged, "n_steps": r.n_steps,
            "e_per_atom": r.energy / len(r.atoms),
            "v_per_atom": r.volume / len(r.atoms),
            "v_per_atom_template": e.get("v_per_atom"),
            "e_formation": ef, "e_decomposition": dec,
            "valide": bool(rep.ok),
            "raison": "" if rep.ok else "; ".join(
                f"{v.symbol}{v.index}:{v.kind}:{v.detail}" for v in rep.violations[:4]),
        }
        resultats.append(res)
        # Écriture incrémentale : un lot à fmax=1e-3 dure des heures, et un
        # résultat perdu parce que le processus s'est arrêté est un résultat à
        # recalculer.
        out.write_text(json.dumps(
            {"references": {f"D3{int(k2)}": v for k2, v in refs.items()},
             "resultats": resultats}, indent=2, ensure_ascii=False))
        print(f"{res['formula']:12s} {e['decoration'][:30]:30s} "
              f"{len(r.atoms):3d}at {'D3' if disp else '  '} "
              f"V/at={res['v_per_atom']:5.2f} E_f={ef:+.3f} "
              f"dec={dec:+.3f} {'OK' if rep.ok else 'KO'} "
              f"{'conv' if r.converged else 'NC'}", flush=True)

    print(f"\n{len(resultats)} structures -> {out}")


if __name__ == "__main__":
    main()
