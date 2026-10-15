"""
Énumération des lacunes, puis des décorations C/N/O qu'elles autorisent.

LE POINT CENTRAL. Dans une supermaille de diamant privée d'un ensemble V de
sites, la coordinence d'un site survivant est entièrement déterminée par V :

    z_i = 4 - (nombre de demi-liaisons de i aboutissant dans V)

et la coordinence détermine à son tour les éléments admissibles, parce que le
cahier des charges associe un intervalle de coordinence à chaque élément :

    z = 4 -> C seulement        (tétraédrique)
    z = 3 -> N (pyramidal) ou C (sp2, mais il devra s'aplanir)
    z = 2 -> O (coudé) ou N (coudé, motif -N=)
    z = 1 -> O terminal (motif >C=O)
    z = 0 -> interdit (atome isolé)

La recherche n'a donc QU'UN degré de liberté combinatoire : le choix de V.
Les éléments suivent. C'est ce qui rend le problème fini et énumérable là où
une recherche de structure générale ne l'est pas.

BORDS PÉRIODIQUES. On compte les DEMI-LIAISONS et jamais les voisins
distincts. Sous conditions périodiques deux sites peuvent être liés par
plusieurs images, et un site peut être lié à sa propre image : un ensemble
d'indices voisins perd cette multiplicité et sous-compte les liaisons
détruites par une lacune. La multiplicité vaut 1 dans les supermailles de la
maille conventionnelle (vérifié par lattice.verifie_reseau de 8 à 216 sites)
mais 4 dans la maille primitive, donc la liste d'adjacence par ensembles
n'était juste que par accident. Voir aussi diagnostic_images() : c'est l'autre
effet de bord, celui qui n'est pas réparable par du code.

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
liaisons lacune-lacune (multiplicité comprise), le nombre total de liaisons
pendantes est 4k - 2b, et chaque N en consomme 1, chaque O coudé 2, chaque O
terminal 3 :

    n_N + 2 n_O(coudé) + 3 n_O(terminal) = 4k - 2b        (décoration canonique)

La composition n'est donc PAS un paramètre libre : elle est fixée par le
nombre de lacunes et par leur agrégation. Optimiser (x, y, z) revient à
chercher dans l'espace des topologies de V, pas dans un simplexe continu.

PAS DE BINAIRES. Le cahier des charges exige C ET N ET O dans la même
structure ; require_ternary vaut donc True par défaut, et les binaires (C3N4
de la lacune isolée, CxOy des paires de lacunes) sont écartés. Ils restent
utiles comme témoins de validation -- la lacune isolée redonne C3N4 sg 215,
le meilleur candidat de la campagne 1 du projet jumeau -- mais ce ne sont pas
des candidats de cette campagne.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

Adjacence = list[list[tuple[int, tuple[int, int, int]]]]

VALENCE = {"C": 4, "N": 3, "O": 2}

# Classe d'environnement, dans le vocabulaire de cno_csp.site_classes, pour
# que le manifeste et le validateur du projet C_N_O_under_pressure soient
# directement réutilisables.
CLASSE = {("C", 4): "C_tet", ("C", 3): "C_trig", ("N", 3): "N_pyr",
          ("N", 2): "N_bent", ("O", 2): "O_bent", ("O", 1): "O_term"}


def coordinences(adj: Adjacence, vac: frozenset[int]) -> dict[int, int]:
    """
    z_i pour chaque site survivant, en comptant les demi-liaisons.

    4 - len(...) et non 4 - |voisins distincts dans V| : c'est toute la
    différence sous conditions périodiques (cf. docstring du module).
    """
    return {i: 4 - sum(1 for j, _S in adj[i] if j in vac)
            for i in range(len(adj)) if i not in vac}


def liaisons_internes(adj: Adjacence, vac: frozenset[int]) -> int:
    """b : nombre de liaisons dont les DEUX extrémités sont des lacunes."""
    demi = sum(1 for i in vac for j, _S in adj[i] if j in vac)
    return demi // 2


def diagnostic_images(adj: Adjacence, vac: frozenset[int]) -> dict:
    """
    Dans quelle mesure l'ensemble de lacunes interagit-il avec ses propres images ?

    C'est l'effet de bord que le code ne peut PAS réparer : il est dans la
    physique de la maille choisie, pas dans le comptage. Dans la limite diluée
    deux lacunes secondes voisines partagent exactement UN voisin commun -- le
    site qui devient oxygène. En petite maille elles en partagent plusieurs,
    par des images différentes, et le compte d'oxygène est gonflé par la
    périodicité. Mesuré : voisins communs maximaux entre deux sites = 4 en
    maille 1x1x1 et 2x1x1, 2 en 2x2x1, et enfin 1 en 2x2x2 et au-delà.

    Conséquence pratique : une structure issue d'une maille de 8 à 32 sites est
    un RÉSEAU ORDONNÉ DE LACUNES à forte concentration, pas « quelques lacunes
    dans du diamant ». Les deux sont des cristaux légitimes et relaxables, mais
    on ne doit pas lire le motif local de l'un dans l'autre. Pour étudier un
    motif isolé il faut au moins 64 sites.

    Renvoie le recouvrement maximal entre deux lacunes (nombre de voisins
    communs, multiplicité d'image comprise), le nombre de paires concernées, et
    la présence d'auto-liaisons.
    """
    vois = {i: Counter(j for j, _S in adj[i]) for i in vac}
    v = sorted(vac)
    recouvre = []
    for a in range(len(v)):
        for b in range(a + 1, len(v)):
            ca, cb = vois[v[a]], vois[v[b]]
            c = sum(min(ca[k], cb[k]) for k in set(ca) & set(cb))
            if c:
                recouvre.append(c)
    auto = sum(1 for i in vac for j, _S in adj[i] if j == i)
    return {"recouvrement_max": max(recouvre, default=0),
            "paires_recouvrantes": len(recouvre),
            "images_en_interaction": any(c > 1 for c in recouvre) or bool(auto),
            "auto_liaisons": auto}


def _canonique(P: np.ndarray, S: tuple[int, ...]) -> tuple[int, ...]:
    """Représentant canonique de l'orbite de S : le plus petit conjugué."""
    im = np.sort(P[:, list(S)], axis=1)
    ordre = np.lexsort(im.T[::-1])
    return tuple(int(x) for x in im[ordre[0]])


def classes_de_lacunes(P: np.ndarray, n_sites: int, adj: Adjacence,
                       k_max: int, z_min: int = 2) -> dict[int, list[tuple[int, ...]]]:
    """
    Tous les ensembles de lacunes de taille <= k_max, à symétrie près.

    Génération par extension : tout k-ensemble contient un (k-1)-ensemble,
    donc canonicaliser toutes les extensions des représentants de niveau k-1
    produit tous les représentants de niveau k. Complet, et sans jamais
    matérialiser les C(n, k) sous-ensembles.

    Élagage. z_i ne peut que décroître quand on ajoute des lacunes, mais un
    site qui viole z_min peut encore être sauvé en devenant lacune lui-même :
    la contrainte n'est pas monotone. La borne sûre est donc : si le nombre de
    sites en violation dépasse le budget de lacunes restant, aucun sur-ensemble
    admissible n'existe, on coupe la branche. Sans cet élagage la génération
    explose dès 32 sites.

    Les niveaux intermédiaires peuvent donc contenir des ensembles non
    admissibles (gardés parce qu'un sur-ensemble pourrait l'être) : c'est
    decorations() qui tranche, en renvoyant une liste vide.
    """
    niveaux: dict[int, list[tuple[int, ...]]] = {0: [()]}
    for k in range(1, k_max + 1):
        vus: set[tuple[int, ...]] = set()
        for S in niveaux[k - 1]:
            for s in range(n_sites):
                if s in S:
                    continue
                c = _canonique(P, tuple(sorted(S + (s,))))
                if c in vus:
                    continue
                viol = sum(1 for z in coordinences(adj, frozenset(c)).values() if z < z_min)
                if viol > k_max - k:
                    continue
                vus.add(c)
        niveaux[k] = sorted(vus)
    return niveaux


@dataclass
class Decoration:
    """Une attribution d'éléments aux sites survivants."""

    vac: tuple[int, ...]
    mapping: dict[int, str]            # index dans la supermaille -> élément
    z: dict[int, int]
    label: str
    composition: tuple[int, int, int]  # (n_C, n_N, n_O)
    b: int = 0                         # liaisons lacune-lacune
    deficits: dict[int, int] = field(default_factory=dict)
    diagnostic: dict = field(default_factory=dict)

    @property
    def classes(self) -> dict[int, str]:
        return {i: CLASSE[(e, self.z[i])] for i, e in self.mapping.items()}

    @property
    def n_pi(self) -> int:
        return sum(1 for d in self.deficits.values() if d == 1)


def _couplage_parfait(deficit: dict[int, int], adj: Adjacence,
                      vac: frozenset[int], cover: int = 2) -> bool:
    """
    Existe-t-il un couplage parfait entre les atomes de déficit 1 ?

    Testé sur un REVÊTEMENT 2x2x2 du graphe quotient, et non sur le quotient
    lui-même. La raison est celle que donne cno_csp.validator.pi_matching :
    dans le quotient un atome peut être apparié à sa propre image, et un
    couplage parfait du quotient ne correspond alors à aucun appariement réel
    dans le cristal -- une double liaison d'un atome avec lui-même n'existe
    pas. On relève donc chaque site en ses 8 copies (i, c), chaque demi-liaison
    (i, (j, S)) en l'arête (i, c) - (j, c+S mod 2), et on exige le couplage
    parfait là.

    C'est fait au niveau du GRAPHE et non de la géométrie : pas de liste de
    voisins à reconstruire sur une supermaille d'atomes, donc assez rapide pour
    être appelé sur chaque décoration candidate.
    """
    import itertools

    import networkx as nx

    if any(d >= 2 for d in deficit.values()):
        return False                   # hors du cadre d'un simple couplage
    besoin = {i for i, d in deficit.items() if d == 1}
    if not besoin:
        return True                    # décoration canonique : rien à apparier

    cellules = list(itertools.product(range(cover), repeat=3))
    G = nx.Graph()
    G.add_nodes_from((i, c) for i in besoin for c in cellules)
    for i in besoin:
        for j, S in adj[i]:
            if j not in besoin or j in vac:
                continue
            for c in cellules:
                d = tuple((c[a] + S[a]) % cover for a in range(3))
                G.add_edge((i, c), (j, d))
    if len(G) % 2:
        return False
    return nx.is_perfect_matching(G, nx.max_weight_matching(G, maxcardinality=True))


def decorations(adj: Adjacence, vac_t: tuple[int, ...], z_min: int = 2,
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

    require_ternary (défaut True) : le cahier des charges exige C ET N ET O
    dans la même structure. Les binaires sont donc écartés -- y compris C3N4
    de la lacune isolée, qui reste le témoin de validation de la méthode mais
    n'est pas un candidat.
    """
    from itertools import product

    vac = frozenset(vac_t)
    z = coordinences(adj, vac)
    if not z or min(z.values()) < max(z_min, 1):
        return []

    autorise: dict[int, list[str]] = {4: ["C"], 3: ["N"], 2: ["O"], 1: ["O"]}
    if "sp2" in motifs:
        autorise[3].append("C")
    if "nbent" in motifs:
        autorise[2].append("N")
    if "oterm" not in motifs:
        autorise[1] = []

    sites = sorted(z)
    choix = [autorise[z[i]] for i in sites]
    if any(not c for c in choix):
        return []

    b = liaisons_internes(adj, vac)
    diag = diagnostic_images(adj, vac)
    out: list[Decoration] = []
    for combo in product(*choix):
        comp = (combo.count("C"), combo.count("N"), combo.count("O"))
        if require_ternary and min(comp) == 0:
            continue
        if comp[0] == 0:
            continue                   # pas de carbone : hors sujet
        mapping = dict(zip(sites, combo))
        deficit = {i: VALENCE[e] - z[i] for i, e in mapping.items()}
        if not _couplage_parfait(deficit, adj, vac):
            continue
        n_pi = sum(1 for d in deficit.values() if d == 1)
        label = ("V" + "_".join(str(v) for v in vac_t)
                 + ("-can" if n_pi == 0 else f"-pi{n_pi}")
                 + f"-C{comp[0]}N{comp[1]}O{comp[2]}")
        out.append(Decoration(vac=vac_t, mapping=mapping, z=z, label=label,
                              composition=comp, b=b, deficits=deficit,
                              diagnostic=diag))
        if len(out) >= max_par_lacune:
            break
    return out
