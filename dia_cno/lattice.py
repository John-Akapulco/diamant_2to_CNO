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


# ---------------------------------------------------------------------------
# Graphe périodique exact : multigraphe à vecteurs d'image
# ---------------------------------------------------------------------------
#
# POURQUOI UN MULTIGRAPHE. Une liste d'adjacence par ensembles d'indices est
# FAUSSE sous conditions périodiques : dans une petite supermaille, deux sites
# peuvent être liés par PLUSIEURS images, et un site peut être lié à sa propre
# image. Compter z_i = 4 - |V inter adj_i| sous-compte alors les liaisons
# détruites par une lacune, et le bilan de composition se décale sans prévenir.
# Mesuré ici : la multiplicité vaut 1 dans toutes les supermailles de la maille
# conventionnelle (8 à 216 sites), mais 4 dans la maille primitive, où les deux
# atomes sont liés par quatre images. La version par ensembles n'était donc
# juste que par accident -- et c'est aussi la raison de partir de la maille
# conventionnelle à 8 sites et non de la primitive à 2.
#
# À ne pas confondre avec l'autre effet de bord, celui des VOISINS COMMUNS
# (vacancies.diagnostic_images) : deux lacunes secondes voisines partagent un
# voisin commun dans la limite diluée, mais 4 en maille 2x1x1 et 2 en 2x2x1,
# par des images différentes. Celui-là n'est pas un défaut de comptage, il est
# dans la physique de la maille choisie.
#
# La bonne structure est donc la liste des DEMI-LIAISONS (j, S), avec S le
# vecteur d'image entier. Elle a exactement 4 entrées par site -- d'où le
# contrôle verifie_reseau() -- et une liaison d'un site à sa propre image y
# figure deux fois, ce qui est le compte correct de liaisons pendantes.


def demi_liaisons(atoms: Atoms, cutoff: float = CUTOFF_LIAISON
                  ) -> list[list[tuple[int, tuple[int, int, int]]]]:
    """Demi-liaisons (voisin, vecteur d'image) par site. Exactement 4 par site."""
    i, j, S = neighbor_list("ijS", atoms, cutoff)
    adj: list[list[tuple[int, tuple[int, int, int]]]] = [[] for _ in range(len(atoms))]
    for a, b, s in zip(i, j, S):
        adj[int(a)].append((int(b), (int(s[0]), int(s[1]), int(s[2]))))
    return adj


def liaisons_uniques(adj: list[list[tuple[int, tuple[int, int, int]]]]
                     ) -> list[tuple[int, int, tuple[int, int, int]]]:
    """Chaque liaison une seule fois, sous la forme (a, b, S) avec a <= b."""
    out = []
    for a, voisinage in enumerate(adj):
        for b, S in voisinage:
            if a < b or (a == b and S > (0, 0, 0)):
                out.append((a, b, S))
    return out


def verifie_reseau(atoms: Atoms, cutoff: float = CUTOFF_LIAISON) -> dict:
    """
    Contrôle les bords périodiques AVANT toute énumération.

    Trois choses qu'il faut savoir et non supposer, parce qu'elles changent le
    comptage des liaisons pendantes :
      - chaque site a-t-il bien exactement 4 liaisons (sinon le cutoff ou la
        maille est faux) ;
      - des paires de sites sont-elles liées par plusieurs images (multiplicité
        > 1 : le cas normal en petite maille, mais il interdit la liste
        d'adjacence par ensembles) ;
      - un site est-il lié à sa propre image (arrive dès la maille primitive).
    """
    from collections import Counter

    adj = demi_liaisons(atoms, cutoff)
    degres = Counter(len(v) for v in adj)
    mult = Counter()
    for a, voisinage in enumerate(adj):
        for b, _S in voisinage:
            mult[(a, b)] += 1
    return {"degres": dict(degres),
            "degre_correct": set(degres) == {4},
            "multiplicite_max": max(mult.values()) if mult else 0,
            "paires_multiples": sum(1 for k, v in mult.items() if v > 1 and k[0] < k[1]),
            "auto_liaisons": sum(1 for k, v in mult.items() if k[0] == k[1])}
