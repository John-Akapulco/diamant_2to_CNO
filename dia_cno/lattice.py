"""
Le réseau diamant comme graphe : sites, liaisons, symétrie.

Tout le projet repose sur un fait de structure : dans le diamant chaque site
a exactement 4 voisins à 1.545 Å et des angles de 109.47°. Retirer un atome
("lacune") fait donc tomber la coordinence de ses 4 voisins de 4 à 3, sans
déplacer personne. La géométrie des environnements visés est obtenue
GRATUITEMENT, par simple comptage de voisins manquants :

    4 voisins  -> tétraédrique        (angles 109.47°)
    3 voisins  -> pyramidal trigonal  (somme des angles 328.4°, NH3 : 320°)
    2 voisins  -> coudé               (angle 109.47°, H2O : 104.5°)
    1 voisin   -> terminal

C'est pourquoi aucune pré-distorsion n'est nécessaire avant relaxation : le
template est déjà dans le bon bassin géométrique, à la longueur de liaison
près. Seule la maille est remise à l'échelle (C-N 1.47 Å et C-O 1.43 Å sont
plus courtes que C-C 1.545 Å).

Le groupe d'espace du diamant est Fd-3m (227) : 192 opérations en maille
conventionnelle, multipliées par les translations de la supermaille. Ces
opérations agissent sur les sites comme des permutations, et c'est sous ce
groupe qu'on énumère les ensembles de lacunes à symétrie près.
"""

from __future__ import annotations

import numpy as np
from ase import Atoms
from ase.build import bulk
from ase.neighborlist import neighbor_list

A_DIAMANT = 3.567          # paramètre de maille expérimental (Å)
CUTOFF_LIAISON = 1.9       # entre 1.545 (1er voisin) et 2.52 (2e voisin)


def supermaille(n: tuple[int, int, int], a: float = A_DIAMANT) -> Atoms:
    """Supermaille du diamant, maille cubique conventionnelle (8 sites) répétée."""
    return bulk("C", "diamond", a=a, cubic=True).repeat(n)


def voisins(atoms: Atoms, cutoff: float = CUTOFF_LIAISON) -> list[list[int]]:
    """Liste d'adjacence du graphe de liaisons, images périodiques comprises."""
    i, j = neighbor_list("ij", atoms, cutoff)
    adj: list[set[int]] = [set() for _ in range(len(atoms))]
    for a, b in zip(i, j):
        adj[int(a)].add(int(b))
    return [sorted(s) for s in adj]


def liaisons(atoms: Atoms, cutoff: float = CUTOFF_LIAISON) -> list[tuple[int, int]]:
    """Liaisons (i<j) du graphe quotient ; une paire liée par deux images compte une fois."""
    i, j = neighbor_list("ij", atoms, cutoff)
    return sorted({(int(a), int(b)) for a, b in zip(i, j) if int(a) < int(b)})


def permutations_symetrie(atoms: Atoms, symprec: float = 1e-4) -> np.ndarray:
    """
    Les opérations de symétrie de la supermaille, vues comme permutations de sites.

    Nécessaire pour énumérer les ensembles de lacunes à symétrie près : deux
    ensembles conjugués donnent la même structure, et les énumérer tous les
    deux fait payer deux fois la relaxation puis la déduplication.
    """
    import spglib

    cellule = (atoms.get_cell().array, atoms.get_scaled_positions(), atoms.numbers)
    sym = spglib.get_symmetry(cellule, symprec=symprec)
    sp = atoms.get_scaled_positions()
    out = []
    for R, t in zip(sym["rotations"], sym["translations"]):
        image = sp @ np.asarray(R).T + t
        d = image[:, None, :] - sp[None, :, :]
        d -= np.round(d)                      # distance au tore
        dist = np.abs(d).max(axis=2)
        perm = np.argmin(dist, axis=1)
        if (dist[np.arange(len(sp)), perm] < 1e-3).all() and len(set(perm.tolist())) == len(sp):
            out.append(perm)
    return np.asarray(out, dtype=np.int32)
