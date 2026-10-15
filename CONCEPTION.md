# Creuser le diamant : conception de l'étape lacunaire

Document de conception de l'étape demandée — *remplacer un carbone
tétraédrique par un azote pyramidal ou coudé, ou par un oxygène coudé, en
créant des lacunes dans son environnement*. Projet jumeau :
[`C_N_O_under_pressure`](../C_N_O_under_pressure), dont tout l'outillage aval
(relaxation MACE, phonons, entrées VASP, enthalpies, rapport) est réutilisé
tel quel.

## 1. Le principe : la lacune fabrique la géométrie gratuitement

Dans le diamant, chaque site a exactement 4 voisins à 1.545 Å et des angles
de 109.47°. Retirer un atome voisin ne déplace personne : cela retire une
branche au site, et le laisse dans la géométrie que le cahier des charges
demande.

| voisins restants | géométrie obtenue | angles | référence chimique |
|---|---|---|---|
| 4 | tétraédrique | 109.47° | diamant |
| 3 | **pyramidal trigonal** | somme 328.4° | NH3 (320°) |
| 2 | **coudé** | 109.47° | H2O (104.5°) |
| 1 | terminal | — | >C=O |

C'est le point de départ de toute la conception : **aucune pré-distorsion
n'est nécessaire**. Un azote pyramidal décoré sur un site à 3 voisins du
diamant est déjà à 9° de l'ammoniac, un oxygène coudé à 5° de l'eau. Le
template est dans le bon bassin avant même la relaxation — contrairement à la
voie « template Materials Project » du projet jumeau, où la décoration doit
d'abord retrouver une géométrie qui n'était pas la sienne.

Seule correction appliquée au template : une **remise à l'échelle isotrope**
de la maille, parce que C–N (1.47 Å) et C–O (1.43 Å) sont plus courtes que
C–C (1.545 Å). Même convention que `cno_csp.site_classes.decorate_and_rescale`,
pour que les deux projets restent comparables.

## 2. Réduction du problème : la coordinence détermine l'élément

Soit `V` l'ensemble des sites retirés d'une supermaille de diamant. Pour tout
site survivant `i` :

    z_i = 4 − |voisins(i) ∩ V|

et le cahier des charges associe à chaque coordinence un jeu d'éléments
admissibles, sans aucune liberté supplémentaire :

| z | éléments admissibles | motif |
|---|---|---|
| 4 | **C** | tétraédrique |
| 3 | **N** (pyramidal) ou C (sp², devra s'aplanir) | g-C3N4, amide |
| 2 | **O** (coudé) ou N (coudé, −N=) | H2O, HN=NH |
| 1 | **O** terminal | >C=O |
| 0 | *interdit* | atome isolé |

**La recherche n'a donc qu'un seul degré de liberté combinatoire : le choix de
`V`.** Les éléments suivent. C'est ce qui rend le problème fini, énumérable, et
exhaustivement traitable à petite maille — là où une recherche de structure
générale ne l'est pas.

Les deux ambiguïtés du cahier des charges (z=3 → C ou N ; z=2 → O ou N) sont
conservées telles quelles : on énumère, on ne devine pas. C'est la doctrine du
projet jumeau.

## 3. La règle de Lewis devient un couplage parfait

Déficit de valence d'un atome : `d_i = valence(élément) − z_i`, avec
C:4, N:3, O:2. Un atome de déficit 1 doit porter exactement une double
liaison, donc être apparié à un voisin lui aussi de déficit 1. **Avoir une
structure de Lewis neutre à couches fermées, c'est exactement avoir un
couplage parfait entre les atomes de déficit 1** (c'est déjà la règle de
`cno_csp.validator.pi_matching`).

D'où le résultat qui structure toute la campagne. La décoration

    z=4 → C,   z=3 → N,   z=2 → O

est **de déficit nul partout**, donc **valide au sens de Lewis quelle que soit
la topologie de `V`**, sans aucune condition à vérifier. On l'appelle
*décoration canonique*.

La lecture chimique est la clé de la faisabilité : chaque liaison pendante
créée par une lacune est passivée par **une paire libre** d'azote ou
d'oxygène, pas par un radical. On ne crée jamais d'électron célibataire. C'est
pour cela qu'on peut creuser le diamant sans le déstabiliser électroniquement
— à la différence de la lacune neutre du diamant pur, qui laisse quatre
liaisons pendantes et se reconstruit.

Les trois autres motifs (z=3 → C sp², z=2 → N coudé, z=1 → O terminal)
introduisent des déficits et ne passent que si le couplage parfait existe. Ils
ne sont pas gratuits, mais ils déplacent la composition — c'est le levier
qu'on veut pour explorer (x, y, z).

Conséquence notable : un **oxygène terminal** (z=1, déficit 1) exige que son
unique voisin soit lui aussi de déficit 1, donc un **C sp²** (carbonyle >C=O,
le motif visé) ou un **N coudé** (nitroso −N=O). Le carbonyle ne peut pas
exister sans carbone trigonal : les motifs `oterm` et `sp2` s'activent
ensemble ou pas du tout.

## 4. Bilan de composition : (x, y, z) n'est pas un paramètre libre

Avec `k = |V|` lacunes et `b` liaisons lacune–lacune, le nombre de liaisons
pendantes créées est `4k − 2b`. Chaque N en consomme 1, chaque O coudé 2,
chaque O terminal 3 :

    n_N + 2·n_O(coudé) + 3·n_O(terminal) = 4k − 2b          (décoration canonique)

Et dans le réseau diamant la topologie se lit encore plus finement, parce que
le graphe est sans triangle ni carré (maille de longueur 6) :

- deux lacunes **premières voisines** (1.545 Å) ne partagent **aucun** voisin :
  elles détruisent une liaison (`b += 1`) et produisent 6 azotes au lieu de 8 ;
- deux lacunes **secondes voisines** (2.52 Å, direction ⟨110⟩) partagent
  **exactement un** voisin : ce voisin passe à z=2 et devient un **oxygène** ;
- deux lacunes **plus éloignées** ne se voient pas : 4 azotes chacune.

Vérifié numériquement sur un réseau 3×3×3 : parmi toutes les distances
jusqu'à 4.4 Å, **seule** 2.52 Å donne un voisin commun, et il est unique.
L'oxygène coudé a donc une signature topologique exacte dans cette famille :
c'est le sommet partagé par deux lacunes en ⟨110⟩.

**Recette de composition, donc :** l'oxygène se commande par le nombre de
paires de lacunes secondes voisines, l'azote par le nombre de lacunes isolées.
En petite maille une même paire de sites peut être seconde voisine *par
plusieurs images périodiques*, et compte alors autant de fois — c'est ainsi
que `dia211` avec deux lacunes produit `C10O4`, sans aucun azote.

En fractions (`x+y+z = 1`, `c = k/N` concentration de lacunes) :

    y + 2z = (4k − 2b)/(N − k)  ≤  4c/(1 − c)

Deux conséquences utiles à la planification :

- une composition **sans carbone** (`x = 0`) exige `4c/(1−c) ≥ 1`, soit
  **c ≥ 20 %** de lacunes. En dessous, il reste forcément du carbone
  tétraédrique : la famille est intrinsèquement riche en carbone, donc dense ;
- à `c` fixé, (y, z) parcourt un **segment**, pas une région : on échange
  2 azotes contre 1 oxygène. Optimiser la composition, c'est choisir `c`, puis
  l'agrégation des lacunes sur ce segment.

## 5. Énumération des lacunes, à symétrie près

Le groupe d'espace du diamant est Fd-3m (227) : 192 opérations en maille
conventionnelle, multipliées par les translations de la supermaille (1536
opérations pour une 2×2×2). Deux ensembles `V` conjugués donnent la même
structure ; les énumérer tous les deux fait payer deux fois la relaxation.

**Algorithme** (`dia_cno/vacancies.py`) : génération par extension. Tout
k-ensemble contient un (k−1)-ensemble ; canonicaliser toutes les extensions
des représentants de niveau k−1 produit donc tous les représentants de niveau
k, sans jamais matérialiser les C(N, k) sous-ensembles. Le représentant
canonique est le plus petit conjugué dans l'ordre lexicographique.

**Élagage.** `z_i` ne peut que décroître quand on ajoute des lacunes, mais un
site qui viole `z_min` peut encore être sauvé en devenant lacune lui-même : la
contrainte n'est pas monotone. La borne sûre retenue est donc *si le nombre de
sites en violation dépasse le budget de lacunes restant, aucun sur-ensemble
admissible n'existe*. Sans elle la génération explose dès 32 sites.

**Coût mesuré** (`z_min = 2`) :

| supermaille | sites | opérations | k=1 | k=2 | k=3 | k=4 |
|---|---|---|---|---|---|---|
| 1×1×1 | 8 | 192 | 1 | 2 | 1 | 2 |
| 2×1×1 | 16 | 128 | 1 | 6 | 10 | 28 |
| 2×2×1 | 32 | 256 | 1 | 8 | 30 | 182 |
| 2×2×2 | 64 | 1536 | 1 | 9 | 48 | *non calculé* |

(ensembles de lacunes distincts à symétrie près et admissibles, `z_min = 2`.)

C'est dérisoire : l'exhaustivité est atteignable jusqu'à k≈4–6, et le facteur
limitant n'est pas l'énumération mais la relaxation.

## 6. Symétrisation vers la maille primitive

Chaque structure construite est passée à `spglib.standardize_cell(to_primitive=True)`.
Deux rôles **distincts**, et c'est pour cela que l'étape est à cet endroit du
pipeline :

1. **le coût** : la relaxation, et surtout le DFT, paient le nombre d'atomes ;
2. **la déduplication** : un ensemble de lacunes énuméré dans une 2×2×1 peut
   avoir une périodicité plus petite que la supermaille. La réduction primitive
   est le mécanisme qui fusionne les solutions redondantes *entre supermailles
   de tailles différentes* — la lacune isolée de `dia111` et sa version
   périodique dans `dia211` se réduisent à la même primitive à 7 atomes.

La structure réduite reçoit ensuite une **signature de prototype** — (groupe
d'espace, {lettre de Wyckoff, élément, multiplicité}) — qui écarte les
doublons **avant** toute relaxation, là où le projet jumeau ne les écartait
qu'après (132 structures validées pour 45 polymorphes seulement, en
campagne 1). C'est le filtre le moins cher du pipeline.

## 7. Relaxation et validation

Réutilisées sans modification depuis le projet jumeau :

- `cno_csp.relax.relax` : positions **+ volume + forme de maille**
  (`FrechetCellFilter`), 0 GPa, `fmax = 1e-3 eV/Å`. Le seuil serré est
  nécessaire : on tranche « N pyramidal vs N plan » sur quelques degrés de
  somme d'angles, et un seuil de screening à 1e-2 laisse des résidus de cet
  ordre ;
- **dispersion D3** pour les pools 0D/1D/2D, MACE seul pour les charpentes 3D
  (doctrine mesurée du jumeau : sans dispersion, rien ne retient feuillets et
  chaînes, la maille gonfle sans limite physique). Le tri par dimensionnalité
  se fait **avant** la relaxation, par `cno_csp.geometry.dimensionality` ;
- `cno_csp.validator.validate` après relaxation, puis le contrôle
  **site par site** de conservation de la coordinence décorée
  (`scripts/funnel_table.py`, trois degrés : composition, coordinence,
  squelette). La leçon de la campagne 2 du jumeau est explicite : une
  structure peut être *valide* sans être *celle qu'on avait décorée* — des
  azotes tricoordonnés qui s'aplanissent. Ici le risque est concentré sur les
  motifs `sp2` et `oterm`, par construction.

## 8. L'objectif : pourquoi E_f brut ne suffit pas

L'enthalpie de formation, au même niveau de théorie que la campagne
(`funnel_table.mu_elements`) :

    E_f = [E(C_x N_y O_z) − x·μ_C − y·μ_N − z·μ_O] / n

avec graphite pour μ_C, N2 pour μ_N, O2 pour μ_O.

**Minimiser E_f seul dégénère.** E_f(diamant) ≈ +0.03 eV/atome contre
graphite : toute structure plus riche en carbone a mécaniquement un E_f plus
bas, et l'optimum de la minimisation brute est « ne mettre ni azote ni
oxygène », c'est-à-dire le diamant lui-même. La quantité à minimiser est donc
la **distance au-dessus de l'enveloppe convexe** du ternaire C-N-O :

    ΔE_hull(x, y, z) = E_f − E_f(enveloppe au point (x, y, z))

construite sur les références élémentaires **et moléculaires** (graphite,
diamant, N2, O2, CO2, et les composés C-N-O connus). Une structure est
intéressante si `ΔE_hull ≈ 0`, pas si `E_f` est petit. Le jumeau fournit déjà
`funnel_table.e_decomposition`, qui mesure la décomposition vers
{graphite, N2, CO2, O2} — verdict de la campagne 1 : **aucun** des 45
polymorphes ne passe sous cette enveloppe, tous à +0.20 à +0.80 eV/atome. Il
faut s'attendre au même ordre de grandeur ici, et le dire d'avance.

**Barre d'erreur, obligatoire.** MACE-MP est entraîné sur des solides
périodiques ; N2 et O2 isolés sont hors domaine, et leur énergie de liaison
entre directement dans μ_N et μ_O. `funnel_table.controle_mu` chiffre l'écart
sur deux molécules d'enthalpie connue : +0.07 à +0.11 eV/atome sur CO2,
−0.23 sur N2O. Ce qui reste solide : **l'ordre entre structures de même
composition**. Ce qui ne l'est pas : le classement absolu entre compositions
différentes. C'est le DFT qui arbitre, et les entrées sont préparées par
`cno_csp.dft`.

## 9. Stratégie de recherche sur (x, y, z)

Trois étages, du certain au heuristique.

**Étage 1 — exhaustif.** Supermailles 8, 16, 32 sites, `k ≤ 4`, tous les
motifs. Quelques centaines de structures, toutes relaxées. Produit la première
carte E_f / ΔE_hull sur le simplexe de composition, et elle est *complète* :
aucune structure de cette taille n'échappe à l'énumération.

**Étage 2 — ciblé par composition.** Les compositions qui se révèlent proches
de l'enveloppe à l'étage 1 déterminent, par la recette du §4, les topologies
de lacunes à construire : nombre de lacunes, nombre de paires secondes
voisines. On énumère alors en 48–64 sites *sous contrainte de composition*,
au lieu d'énumérer à l'aveugle.

**Étage 3 — expansion en amas, puis Monte-Carlo.** La composition et, en bonne
part, l'énergie ne dépendent que de **corrélations de paires sur le
sous-réseau des lacunes** (nombre de paires 1ᵉʳ, 2ᵉ, 3ᵉ voisines) — c'est
exactement ce que montre le bilan du §4. On ajuste donc une **expansion en
amas** sur les données de l'étage 1, on l'utilise pour pré-cribler des
millions de configurations en grande maille, et on ne relaxe au MACE que les
meilleures. Au-delà, recuit de Metropolis dans l'espace des ensembles de
lacunes (déplacer une lacune vers un site voisin ; ajouter/retirer une paire,
ce qui change la composition), avec ΔE_hull comme énergie.

L'étage 1 est à écrire et à lancer ; les étages 2 et 3 ne se conçoivent
correctement qu'avec la carte de l'étage 1 sous les yeux, et leurs paramètres
(quelles compositions, quels amas) en dépendent.

## 10. Ce que la méthode garantit, et ce qu'elle ne garantit pas

Garanti :

- **tout site réalise un environnement du cahier des charges**, par
  construction et non par filtrage a posteriori ;
- **structure de Lewis neutre à couches fermées**, par le couplage parfait
  (trivialement satisfaite pour la décoration canonique) ;
- **exhaustivité** à taille de maille et nombre de lacunes bornés, à symétrie
  près ;
- des structures **denses** : la famille est riche en carbone par force (§4),
  et part de 5.76–5.86 Å³/atome avant relaxation, contre 5.67 pour le diamant
  et 5.93–6.01 pour les meilleurs candidats du jumeau. C'est la voie la plus
  dense explorée dans les deux projets.

Non garanti, et à vérifier calcul par calcul :

- que la relaxation **conserve** l'environnement décoré. Le risque est réel
  pour `sp2` (aplanissement) et pour les cavités à plusieurs paires libres
  voisines, qui se repoussent ;
- que la structure reste **connexe comme prévue** : la dimensionnalité est
  relue après relaxation, une charpente peut se fragmenter ;
- que « dynamiquement stable » signifie autre chose qu'un **minimum local du
  potentiel MACE** — c'est tout ce que disent les phonons du jumeau ;
- la **stabilité thermodynamique** : voir §8, l'attente raisonnable est
  +0.2 à +0.8 eV/atome au-dessus de l'enveloppe moléculaire.

## 11. Première validation : la méthode retrouve le meilleur candidat du jumeau

La plus petite instance possible — maille conventionnelle 1×1×1 (8 sites),
**une** lacune, décoration canonique — donne :

    7 atomes,  C3N4,  groupe d'espace 215 (P-43m),  5.86 Å³/atome

C'est **exactement** `mp-570377` sg 215, le meilleur candidat de la campagne 1
du projet jumeau : la blende lacunaire, C et N tous deux sp³, azote pyramidal.
Trouvée là-bas par criblage de 1417 parents Materials Project, elle est ici le
premier terme d'une famille, obtenu sans base de données. La conception est
cohérente avec un résultat déjà établi par une voie indépendante — et elle
place ce résultat dans une série, ce que la voie « template MP » ne faisait pas.

## 12. Arborescence et intégration

    dia_cno/lattice.py     réseau diamant : sites, liaisons, permutations de symétrie
    dia_cno/vacancies.py   énumération des lacunes, décorations, règle de Lewis
    dia_cno/templates.py   construction, remise à l'échelle, primitive, signature
    scripts/gen_templates.py  CLI : lacunes -> cif/ + templates_manifest.json
    scripts/relax_lot.py      CLI : relaxation MACE + validation + E_f + ΔE_dec

Le manifeste est écrit **au format du projet jumeau**
(`templates_manifest.json` : `source_id`, `decoration`, `child_formula`,
`spacegroup`, `classes`, ...), donc consommable sans adaptation par ses
`pools_dim.py`, sa relaxation, ses phonons, son `lot_dft.py` et son rapport.
`dia_cno.jumeau()` localise le projet jumeau (variable d'environnement
`CNO_UNDER_PRESSURE`) et le rend importable.

Environnement d'exécution : `conda run -n mlip python ...`
(mace 0.3.12, ase 3.29.0, phonopy 4.7.2, torch 2.2.2, torch-dftd).
