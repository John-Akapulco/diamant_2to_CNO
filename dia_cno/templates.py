"""
Du couple (lacunes, décoration) à une structure cristalline prête à relaxer.

Trois opérations, dans cet ordre, et l'ordre a des raisons.

1. REMISE À L'ÉCHELLE. Les liaisons visées sont plus courtes que C-C du
   diamant (1.545 Å) : C-N 1.47, C-O 1.43. On applique un facteur isotrope,
   moyenne sur les liaisons du rapport des sommes de rayons covalents --
   exactement la convention de cno_csp.site_classes.decorate_and_rescale, pour
   que les deux projets restent comparables. Isotrope seulement : la
   relaxation sous FrechetCellFilter corrige ensuite l'anisotropie.

2. SYMÉTRISATION VERS LA PRIMITIVE. Un ensemble de lacunes énuméré dans une
   supermaille 2x2x2 peut avoir une périodicité plus petite que la
   supermaille. spglib.standardize_cell(to_primitive=True) rend alors la vraie
   maille primitive. Deux bénéfices distincts :
     - le coût : la relaxation et surtout le DFT paient le nombre d'atomes ;
     - la déduplication : c'est le MÊME mécanisme qui fusionne les solutions
       redondantes entre supermailles de tailles différentes. La lacune isolée
       de la maille 1x1x1 et celle, périodique, de la 2x1x1 se réduisent à la
       même primitive C3N4 à 7 atomes.
   La symétrisation idéalise aussi les positions, ce qui est souhaitable ici :
   le template est un prototype idéal, pas une mesure.

3. SIGNATURE DE PROTOTYPE. (groupe d'espace, {lettre de Wyckoff, élément,
   multiplicité}) identifie la structure avant tout calcul. C'est le filtre
   le moins cher du pipeline : il écarte les doublons avant la relaxation, là
   où le StructureMatcher du projet jumeau ne les écarte qu'après.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ase import Atoms
from ase.data import atomic_numbers, covalent_radii

from .lattice import (CUTOFF_LIAISON, demi_liaisons, liaisons,
                      liaisons_uniques)
from .vacancies import Decoration


def facteur_echelle(parent: Atoms, dec: Decoration) -> float:
    """Facteur isotrope, moyenne sur les liaisons conservées des rapports de rayons."""
    vac = set(dec.vac)
    syms = parent.get_chemical_symbols()
    ratios = []
    # liaisons_uniques et non un ensemble de paires : une paire liée par
    # plusieurs images compte autant de fois qu'elle a d'images, sinon la
    # moyenne est faussée par les bords périodiques.
    for a, b, _S in liaisons_uniques(demi_liaisons(parent, CUTOFF_LIAISON)):
        if a in vac or b in vac:
            continue
        r_cible = (covalent_radii[atomic_numbers[dec.mapping[a]]]
                   + covalent_radii[atomic_numbers[dec.mapping[b]]])
        r_parent = (covalent_radii[atomic_numbers[syms[a]]]
                    + covalent_radii[atomic_numbers[syms[b]]])
        ratios.append(r_cible / r_parent)
    return float(np.mean(ratios)) if ratios else 1.0


def construit(parent: Atoms, dec: Decoration, rescale: bool = True) -> Atoms:
    """Supprime les lacunes, applique la décoration, remet à l'échelle."""
    garde = sorted(dec.mapping)
    enfant = parent[garde]
    enfant.set_chemical_symbols([dec.mapping[i] for i in garde])
    if rescale:
        f = facteur_echelle(parent, dec)
        enfant.set_cell(enfant.get_cell() * f, scale_atoms=True)
    return enfant


def primitive(atoms: Atoms, symprec: float = 1e-3) -> Atoms:
    """Maille primitive idéalisée (spglib). Renvoie l'entrée si spglib échoue."""
    import spglib

    cellule = (atoms.get_cell().array, atoms.get_scaled_positions(), atoms.numbers)
    res = spglib.standardize_cell(cellule, to_primitive=True, no_idealize=False,
                                  symprec=symprec)
    if res is None:
        return atoms
    maille, positions, numeros = res
    return Atoms(numbers=numeros, scaled_positions=positions, cell=maille, pbc=True)


def signature(atoms: Atoms, symprec: float = 1e-3):
    """(groupe d'espace, orbites de Wyckoff décorées) : identité du prototype."""
    import spglib
    from ase.data import chemical_symbols

    cellule = (atoms.get_cell().array, atoms.get_scaled_positions(), atoms.numbers)
    try:
        ds = spglib.get_symmetry_dataset(cellule, symprec=symprec)
        num = int(ds.number if hasattr(ds, "number") else ds["number"])
        wy = list(ds.wyckoffs if hasattr(ds, "wyckoffs") else ds["wyckoffs"])
        eq = list(ds.equivalent_atoms if hasattr(ds, "equivalent_atoms")
                  else ds["equivalent_atoms"])
    except Exception:
        return None
    mult: dict[int, int] = {}
    for r in eq:
        mult[int(r)] = mult.get(int(r), 0) + 1
    sym = atoms.get_chemical_symbols()
    return (num, tuple(sorted((wy[r], sym[r], n) for r, n in mult.items())))


@dataclass
class Template:
    atoms: Atoms
    source_id: str              # ex. "dia211"
    decoration: str             # label de la décoration
    formula: str
    spacegroup: int
    n_atoms: int
    v_per_atom: float
    composition: tuple[int, int, int]
    classes: dict[int, str]
    dimensionality: int | None = None
    flags: tuple[str, ...] = ()
    n_lacunes: int = 0
    b_lacunes: int = 0                 # liaisons lacune-lacune
    recouvrement_images: int = 0       # voisins communs max entre deux lacunes
    images_en_interaction: bool = False

    def manifest_entry(self) -> dict:
        """Entrée compatible templates_manifest.json de C_N_O_under_pressure."""
        return {"source_id": self.source_id, "decoration": self.decoration,
                "parent_formula": "C (diamant)", "child_formula": self.formula,
                "spacegroup": self.spacegroup, "n_atoms": self.n_atoms,
                "e_above_hull": 0.0,
                "classes": {str(k): v for k, v in self.classes.items()},
                "flags": list(self.flags), "kappa": 0.0,
                "composition": {"C": self.composition[0], "N": self.composition[1],
                                "O": self.composition[2]},
                "v_per_atom": round(self.v_per_atom, 4),
                "dimensionality": self.dimensionality,
                "n_lacunes": self.n_lacunes, "b_lacunes": self.b_lacunes,
                "recouvrement_images": self.recouvrement_images,
                "images_en_interaction": self.images_en_interaction}


def homonucleaire(atoms: Atoms) -> tuple[str, ...]:
    """Signale les liaisons N-N et O-O : permises, mais coûteuses et rares."""
    sym = atoms.get_chemical_symbols()
    paires = {tuple(sorted((sym[a], sym[b]))) for a, b in liaisons(atoms, 1.8)}
    return tuple(f"liaison {p[0]}-{p[1]}" for p in (("N", "N"), ("O", "O")) if p in paires)
