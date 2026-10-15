"""
Énumération des lacunes, puis des décorations C/N/O qu'elles autorisent.

LE POINT CENTRAL. Dans une supermaille de diamant privée d'un ensemble V de
sites, la coordinence d'un site survivant est entièrement déterminée par V :

    z_i = 4 - |voisins(i) inter V|

et la coordinence détermine à son tour les éléments admissibles, parce que le
cahier des charges associe un intervalle de coordinence à chaque élément :

    z = 4 -> C seulement        (tétraédrique)
    z = 3 -> N (pyramidal) ou C (sp2, mais il devra s'aplanir)
    z = 2 -> O (coudé) ou N (coudé, motif -N=)
    z = 1 -> O terminal (motif >C=O)
    z = 0 -> interdit (atome isolé)

La recherche n'a donc QU'UN degré de liberté combinatoire : le choix de V.
Les éléments suivent. C'est ce qui rend le problème fini et énumérable là où
une CSP générale ne l'est pas.

LA RÈGLE DE LEWIS DEVIENT UN COUPLAGE. Le déficit de valence d'un atome vaut
valence - z (C:4, N:3, O:2). Un atome de déficit 1 doit porter exactement une
double liaison, donc être apparié à un voisin lui aussi de déficit 1. Avoir
une structure de Lewis neutre à couches fermées, c'est exactement avoir un
couplage parfait entre les atomes de déficit 1 (cf. cno_csp.validator.pi_matching).

D'où un résultat qui structure toute la campagne : la décoration

    z=4 -> C,  z=3 -> N,  z=2 -> O

est de déficit nul PARTOUT. Elle est donc TOUJOURS valide au sens de Lewis,
sans aucune condition sur la topologie de V. On l'appelle ici décoration
canonique : chaque liaison pendante créée par une lacune est passivée par une
paire libre d'azote ou d'oxygène, pas par un radical. C'est la raison
chimique pour laquelle on peut creuser le diamant sans le déstabiliser par
des électrons célibataires.

Les autres décorations (z=3 -> C sp2, z=2 -> N coudé, z=1 -> O terminal)
introduisent des déficits et ne passent que si le couplage parfait existe.
Elles ne sont donc pas gratuites, mais elles déplacent la composition, ce qui
est précisément le levier qu'on veut pour explorer (x, y, z).

BILAN DE COMPOSITION, exact et utile. En notant k = |V| et b le nombre de
liaisons lacune-lacune, le nombre total de liaisons pendantes est 4k - 2b, et
chaque N en consomme 1, chaque O coudé 2, chaque O terminal 3 :

    n_N + 2 n_O(coudé) + 3 n_O(terminal) = 4k - 2b        (décoration canonique)

La composition n'est donc PAS un paramètre libre : elle est fixée par le
nombre de lacunes et par leur agrégation. Optimiser (x, y, z) revient à
chercher dans l'espace des topologies de V, pas dans un simplexe continu.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

VALENCE = {"C": 4, "N": 3, "O": 2}

# Éléments admissibles par coordinence. L'ordre compte : le premier est
# l'option de déficit nul (décoration canonique), énumérée d'abord.
OPTIONS_Z = {4: ("C",), 3: ("N", "C"), 2: ("O", "N"), 1: ("O",)}

# Classe d'environnement, dans le vocabulaire de cno_csp.site_classes, pour
# que le manifeste et le validateur du projet C_N_O_under_pressure soient
# directement réutilisables.
CLASSE = {("C", 4): "C_tet", ("C", 3): "C_trig", ("N", 3): "N_pyr",
          ("N", 2): "N_bent", ("O", 2): "O_bent", ("O", 1): "O_term"}


def coordinences(adj: list[list[int]], vac: frozenset[int]) -> dict[int, int]:
    """z_i pour chaque site survivant."""
    return {i: 4 - len(vac.intersection(adj[i]))
            for i in range(len(adj)) if i not in vac}


def _canonique(P: np.ndarray, S: tuple[int, ...]) -> tuple[int, ...]:
    """Représentant canonique de l'orbite de S : le plus petit conjugué."""
    im = np.sort(P[:, list(S)], axis=1)
    ordre = np.lexsort(im.T[::-1])
    return tuple(int(x) for x in im[ordre[0]])


def classes_de_lacunes(P: np.ndarray, n_sites: int, adj: list[list[int]],
                       k_max: int, z_min: int = 2) -> dict[int, list[tuple[int, ...]]]:
    """
    Tous les ensembles de lacunes de taille <= k_max, à symétrie près.

    Génération par extension : tout k-ensemble contient un (k-1)-ensemble,
    donc canonicaliser toutes les extensions des représentants de niveau k-1
    produit tous les représentants de niveau k. Complet, et sans jamais
    matérialiser les C(n, k) sous-ensembles.

    Élagage. z_i ne peut que décroître quand on ajoute des lacunes, mais un
    site qui viole z_min peut encore être sauvé en devenant lacune lui-même.
    La borne sûre est donc : si le nombre de sites en violation dépasse le
    budget de lacunes restant, aucun sur-ensemble admissible n'existe, on
    coupe la branche. Sans cet élagage la génération explose en 32-64 sites.
    """
    niveaux: dict[int, list[tuple[int, ...]]] = {0: [()]}
    for k in range(1, k_max + 1):
        vus: set[tuple[int, ...]] = set()
        for S in niveaux[k - 1]:
            for s in range(n_sites):
                if s in S:
                    continue
                T = tuple(sorted(S + (s,)))
                c = _canonique(P, T)
                if c in vus:
                    continue
                vac = frozenset(c)
                viol = sum(1 for z in coordinences(adj, vac).values() if z < z_min)
                if viol > k_max - k:
                    continue
                vus.add(c)
        niveaux[k] = sorted(vus)
    return niveaux


@dataclass
class Decoration:
    """Une attribution d'éléments aux sites survivants."""

    vac: tuple[int, ...]
    mapping: dict[int, str]           # index dans la supermaille -> élément
    z: dict[int, int]
    label: str
    composition: tuple[int, int, int]  # (n_C, n_N, n_O)
    deficits: dict[int, int] = field(default_factory=dict)

    @property
    def classes(self) -> dict[int, str]:
        return {i: CLASSE[(e, self.z[i])] for i, e in self.mapping.items()}


def _couplage_parfait(deficit: dict[int, int], adj: list[list[int]],
                      vac: frozenset[int]) -> bool:
    """
    Existe-t-il un couplage parfait entre les atomes de déficit 1 ?

    Testé sur le graphe quotient de la supermaille. Un couplage du quotient
    peut en principe apparier un atome à sa propre image (cf. l'avertissement
    de cno_csp.validator.pi_matching) ; ici les supermailles font au moins 8
    sites et les sites de déficit 1 sont rares, mais la validation finale
    repasse par pi_matching sur une 2x2x2, qui tranche sans cette réserve.
    """
    import networkx as nx

    besoin = [i for i, d in deficit.items() if d == 1]
    if any(d >= 2 for d in deficit.values()):
        return False                   # hors du cadre d'un simple couplage
    if not besoin:
        return True                    # décoration canonique : rien à apparier
    if len(besoin) % 2:
        return False
    G = nx.Graph()
    G.add_nodes_from(besoin)
    s = set(besoin)
    for i in besoin:
        for j in adj[i]:
            if j in s and j not in vac:
                G.add_edge(i, j)
    if len(G) % 2:
        return False
    return nx.is_perfect_matching(G, nx.max_weight_matching(G, maxcardinality=True))


def decorations(adj: list[list[int]], vac_t: tuple[int, ...], z_min: int = 2,
                motifs: tuple[str, ...] = ("canonique",),
                require_ternary: bool = True,
                max_par_lacune: int = 8) -> list[Decoration]:
    """
    Décorations admissibles d'un ensemble de lacunes donné.

    motifs :
      "canonique"  z=4->C, z=3->N, z=2->O : déficit nul, toujours valide.
      "sp2"        autorise z=3 -> C (carbone trigonal, il devra s'aplanir).
      "nbent"      autorise z=2 -> N (motif -N=).
      "oterm"      autorise z=1 -> O (carbonyle) ; demande aussi z_min=1.

    require_ternary : le cahier des charges exige C ET N ET O dans la même
    structure. Les binaires (C3N4 de la lacune isolée, par exemple) sont
    conservés quand on le désactive, et c'est utile : C3N4 pseudocubique est
    le meilleur candidat de la campagne 1 du projet jumeau.
    """
    from itertools import product

    vac = frozenset(vac_t)
    z = coordinences(adj, vac)
    if not z or min(z.values()) < max(z_min, 1):
        return []

    autorise = {4: ["C"], 3: ["N"], 2: ["O"], 1: ["O"]}
    if "sp2" in motifs:
        autorise[3].append("C")
    if "nbent" in motifs:
        autorise[2].append("N")
    if "oterm" not in motifs:
        autorise[1] = []

    sites = sorted(z)
    choix = [autorise[z[i]] for i in sites]
    if any(len(c) == 0 for c in choix):
        return []

    out: list[Decoration] = []
    for combo in product(*choix):
        mapping = dict(zip(sites, combo))
        deficit = {i: VALENCE[e] - z[i] for i, e in mapping.items()}
        comp = (combo.count("C"), combo.count("N"), combo.count("O"))
        if require_ternary and min(comp) == 0:
            continue
        if comp[0] == 0:
            continue                   # pas de carbone : hors sujet
        if not _couplage_parfait(deficit, adj, vac):
            continue
        n_pi = sum(1 for d in deficit.values() if d == 1)
        label = ("V" + "_".join(str(v) for v in vac_t)
                 + ("-can" if n_pi == 0 else f"-pi{n_pi}")
                 + f"-C{comp[0]}N{comp[1]}O{comp[2]}")
        out.append(Decoration(vac=vac_t, mapping=mapping, z=z, label=label,
                              composition=comp, deficits=deficit))
        if len(out) >= max_par_lacune:
            break
    return out
