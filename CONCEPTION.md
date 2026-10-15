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

**Pas de binaires.** Le cahier des charges exige C **et** N **et** O dans la
même structure : `require_ternary` vaut `True` par défaut, et les binaires
sont écartés à l'énumération, pas filtrés après. Cela comprend `C3N4` de la
lacune isolée et les `CxOy` des paires de lacunes. Ils restent des **témoins
de validation** de la méthode (§14), jamais des candidats. L'option
`--binaires` existe pour reproduire la comparaison avec la campagne 1 du
jumeau, qui ne l'exigeait pas.

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

Le couplage est testé sur un **revêtement 2×2×2** du graphe quotient et non
sur le quotient : dans le quotient un atome peut être apparié à sa propre
image, c'est-à-dire porter une double liaison avec lui-même, ce qui ne
correspond à aucun appariement réel dans le cristal. Même convention que
`cno_csp.validator.pi_matching`, mais menée au niveau du graphe — assez rapide
pour être appelée sur chaque décoration candidate.

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

**Domaine atteignable, mesuré** (`scripts/carte_composition.py`). Avec la
seule décoration canonique, `k ≤ 4` lacunes et des supermailles de 8 à 32
sites : **37 compositions ternaires C+N+O distinctes**, de `x = 0.083`
(C1N10O1) à `x = 0.714` (C20N6O2). Le bilan de liaisons pendantes
ci-dessus est vérifié comme contrôle interne sur chaque ensemble de lacunes
énuméré : **0 écart**. Le domaine est donc déjà large avant même d'activer
`sp2`, `nbent` et `oterm`, qui l'élargiront encore en découplant partiellement
la composition de la topologie.

Les compositions les plus riches en carbone — celles qui intéressent la
densité — sont aussi les moins nombreuses : à faible concentration de lacunes
il y a peu de façons non équivalentes de les placer. L'exploration est donc
*bon marché là où elle est intéressante*, et c'est l'inverse de la plupart des
recherches de structure.

## 5. Les bords périodiques : deux effets distincts

La supermaille est périodique, et deux choses très différentes en découlent.
La première est un problème de code, réparé ; la seconde est dans la physique
de la maille et ne se répare pas, elle se mesure et se déclare.

**(a) Multiplicité des liaisons — corrigé.** Sous conditions périodiques deux
sites peuvent être liés par *plusieurs* images, et un site peut être lié à sa
*propre* image. Une liste d'adjacence par ensembles d'indices perd cette
multiplicité, et `z_i = 4 − |V ∩ voisins(i)|` sous-compte alors les liaisons
détruites par une lacune : le bilan de composition se décale sans prévenir. Le
graphe est donc stocké en **demi-liaisons `(voisin, vecteur d'image)`**, et
chaque site en a exactement 4. `lattice.verifie_reseau()` contrôle les trois
choses à ne pas supposer — degré 4 partout, multiplicité maximale,
auto-liaisons — et `gen_templates.py` l'exécute sur chaque supermaille avant
d'énumérer. Mesuré :

| maille | sites | multiplicité de liaison | auto-liaisons |
|---|---|---|---|
| primitive | 2 | **4** | 0 |
| conventionnelle 1×1×1 → 3×3×3 | 8 → 216 | 1 | 0 |

Les supermailles de la maille conventionnelle sont donc saines, et l'ancienne
version du code n'était juste que par accident : la maille primitive, elle,
l'aurait cassée. C'est aussi la raison pour laquelle le projet part de la
maille conventionnelle à 8 sites et non de la primitive à 2.

**(b) Interaction d'une lacune avec ses propres images — irréductible.** Dans
la limite diluée, deux lacunes secondes voisines partagent **exactement un**
voisin commun : le site qui devient oxygène (§4). En petite maille elles en
partagent plusieurs, par des images différentes, et le compte d'oxygène est
gonflé par la périodicité. Mesuré, voisins communs maximaux entre deux sites :

| maille | sites | recouvrement max | limite diluée atteinte |
|---|---|---|---|
| 1×1×1 | 8 | 4 | non |
| 2×1×1 | 16 | 4 | non |
| 2×2×1 | 32 | 2 | non |
| 2×2×2 | 64 | **1** | **oui** |
| 3×3×3 | 216 | 1 | oui |

**Il faut 64 sites pour qu'une lacune cesse de se voir elle-même.** En dessous,
une structure n'est pas « quelques lacunes dans du diamant » mais un **réseau
ordonné de lacunes** à forte concentration. Les deux sont des cristaux
légitimes, relaxables, et dignes d'intérêt — mais on ne doit pas lire le motif
local de l'un dans l'autre, et c'est pourquoi chaque template porte le
diagnostic `recouvrement_images` et `images_en_interaction` dans son manifeste.

**La tension pratique, à trancher explicitement.** La limite diluée (≥ 64
sites) et le budget DFT (≈ 24–30 atomes par maille dans le projet jumeau) sont
incompatibles. Sur le lot ternaire courant : 22 templates sur 41 sont exempts
d'interaction d'images, et ils font tous 61–62 atomes. Le partage retenu :

- **MACE** relaxe tout, y compris les 61–62 atomes — c'est bon marché ;
- **DFT** se limite aux mailles de 13 à 30 atomes, en déclarant que ce sont des
  superstructures lacunaires ordonnées et non des motifs dilués ;
- la comparaison dilué / concentré se fait **au sein de MACE**, où les deux
  régimes sont accessibles au même niveau de théorie.

## 6. Dimensionnalité : ce que la méthode produit vraiment

Le cahier des charges espérait « des composés 3D, 2D ou 1D voire 0D
(moléculaires) ». Mesuré plutôt qu'espéré (`scripts/dimensionnalite.py`,
maille 2×1×1, templates distincts après réduction primitive) :

| k | % lacunes | ternaires, canonique | ternaires, tous motifs |
|---|---|---|---|
| 2 | 12.5 % | 3D:1 | 3D:1 |
| 3 | 18.8 % | 3D:5 2D:3 | 3D:11 2D:6 |
| 4 | 25.0 % | 3D:10 2D:7 | 3D:23 2D:22 |
| 5 | 31.2 % | 3D:7 2D:12 | 3D:6 2D:38 |
| 6 | 37.5 % | 3D:1 2D:7 | 3D:5 2D:41 **1D:2** |
| 7 | 43.8 % | 2D:3 | 2D:24 |

Même balayage sur la maille **2×2×1 (32 sites)**, décoration canonique,
ternaires :

| k | % lacunes | atomes | ternaires | dimensionnalité |
|---|---|---|---|---|
| 2 | 6.2 % | 30 | 2 | 3D:2 |
| 3 | 9.4 % | 29 | 17 | 3D:17 |
| 4 | 12.5 % | 28 | 69 | 3D:69 |
| 5 | 15.6 % | 27 | 128 | 3D:124 2D:4 |
| 6 | 18.8 % | 26 | 303 | 3D:280 2D:23 |

**La comparaison des deux mailles à concentration ÉGALE est le résultat
important**, et elle corrige la lecture naïve du premier tableau :

| % lacunes | 16 sites | 32 sites |
|---|---|---|
| 12.5 % | 17 % de 2D | **1 %** de 2D |
| 18.8 % | 37 % de 2D | **7.6 %** de 2D |

À taux de lacunes identique, la part de 2D s'effondre quand la maille grandit.
La raison est celle du §5 : dans une petite maille, quelques lacunes **plus
leurs images périodiques** forment un *plan* continu qui tranche le cristal.
La basse dimensionnalité des petites mailles est donc, pour une bonne part, un
**artefact d'interaction d'images** et non une propriété du motif local.

**C'est donc un générateur de charpentes 3D, et davantage encore qu'il n'y
paraît.** Le 2D n'est abondant qu'à forte concentration de lacunes et en
petite maille ; le 1D n'apparaît qu'à 37 % de lacunes et seulement avec les
motifs π ; le **0D n'apparaît jamais** — et ce dernier point n'est pas un
manque d'exploration, c'est structural.

**Pourquoi le 0D est fermé dès qu'on exige du carbone.** Le carbone demande
z ≥ 3 ; dans un fragment fini du réseau diamant, seuls les atomes *intérieurs*
atteignent z ≥ 3, et les petits diamantoïdes n'ont pas d'intérieur : tous
leurs atomes sont en surface. Les trois cas calculés :

| cluster | atomes | coordinences | décoration canonique | Lewis |
|---|---|---|---|---|
| cycle à 6 (chaise) | 6 | 6×z=2 | **O6** | ok |
| cage adamantane | 10 | 4×z=3, 6×z=2 | **N4O6** | ok |
| boule de rayon 3 | 41 | 17×z=4, 12×z=2, 12×z=1 | 17 C, 12 O, 12 O terminal | **impossible** |

Le cycle à 6 est un anneau d'oxygènes, la cage adamantane est **N4O6** — une
molécule neutre à couches fermées réalisant exactement les environnements
visés, mais **sans un seul carbone**. Et dès qu'on prend un cluster assez gros
pour avoir des carbones intérieurs (boule de rayon 3 : 17 carbones
tétraédriques), la surface est faite d'oxygènes terminaux dont le partenaire π
obligatoire n'existe pas — leur unique voisin est un carbone z=4, de déficit
nul. La règle de Lewis refuse le cluster.

Autrement dit : dans cette famille, **le carbone est l'élément du volume et
l'azote/l'oxygène sont les éléments de la surface**. Un objet de basse
dimensionnalité est dominé par sa surface, donc pauvre en carbone, donc soit
binaire (écarté), soit non décorable. Les motifs π (C sp² + O terminal)
atténuent le problème — ils triplent le nombre de templates et font apparaître
le 1D — mais ne l'annulent pas : testé jusqu'à 44 % de lacunes, aucun 0D
ternaire.

**Dimensionnement de l'étage 1, au passage.** La maille 32 sites donne 519
templates ternaires jusqu'à k = 6, et le nombre croît vite (2, 17, 69, 128,
303). C'est ce nombre, et non celui des ensembles de lacunes, qui fixe le coût
en relaxations — et c'est lui qui justifie le GPU dès l'étage 1 étendu.

**Conséquence pour la suite.** Si des cristaux moléculaires C-N-O sont voulus,
cette méthode n'est pas la bonne porte : il faudrait soit relâcher la
contrainte ternaire (et alors N4O6 et les cages apparentées sont des sous-
produits gratuits, intéressants pour eux-mêmes), soit terminer les surfaces
autrement qu'avec les six environnements du cahier des charges — par de
l'hydrogène, qui en est absent par construction. Pour les charpentes 3D
denses, en revanche, la méthode est dans son domaine naturel.

## 7. Énumération des lacunes, à symétrie près

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

## 8. Symétrisation vers la maille primitive

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

## 9. Relaxation et validation

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

## 10. Sur quelle machine, et pourquoi

Trois machines, et le choix se fait sur des bancs **mesurés** par le projet
jumeau (`scripts/bench/bench_calls.py`, `runs_random/bench_calls/`) : coût d'un
appel énergie + forces MACE-MP en float64, sans dispersion.

| atomes | Yargla 1 cœur | Yargla 8 cœurs | H100 de vm1 | gain GPU / 1 cœur |
|---|---|---|---|---|
| 20 | 1391 ms | 362 ms | 62 ms | ×23 |
| 44 | 3407 ms | 846 ms | 37 ms | ×93 |
| 352 | 28474 ms | 6827 ms | 89 ms | ×318 |

**Le gain du GPU croît avec la taille** : en dessous de ~50 atomes le H100 est
sous-occupé et le transfert domine. C'est décisif ici, parce que la taille
n'est pas un paramètre libre — les templates exempts d'interaction d'images
(§5) font **61–62 atomes**, en plein régime où le GPU gagne deux ordres de
grandeur par appel.

En débit total plutôt que par appel, le H100 partagé entre 16 processus débite
35.8 appels/s sur 44 atomes avec D3, contre 1/4.256 = 0.235 appel/s par cœur
Yargla : **l'équivalent de ~150 cœurs, soit presque quatre nœuds Yargla**.

Deux réserves que les bancs rendent visibles :

- **D3 coûte cher sur GPU**, en relatif : à 352 atomes, 89 ms sans dispersion
  contre 417 ms avec. Le pool 3D — 38 des 41 templates du lot ternaire, qui se
  relaxent sans D3 — est donc le meilleur cas du GPU ; les pools 0D/1D/2D y
  gagnent moins ;
- **la concurrence sature vers 8 processus** (33.5 appels/s contre 35.8 à 16),
  pendant que la latence par appel double (233 ms contre 445). D'où
  `N_SHARDS=8` par défaut dans `hpc/vm1_lot.slurm` : 94 % du débit pour deux
  fois moins d'attente par structure.

**Répartition retenue.** Mise au point et petits lots sur le Mac ; étage 1
(quelques dizaines de structures) indifféremment sur Yargla ou vm1, les deux
suffisent ; étages 2 et 3 (milliers de configurations à 61+ atomes) sur le GPU
de vm1, où l'écart est de deux ordres de grandeur par appel.

**Topologie d'accès, mesurée.** vm1 ne se joint pas directement : son port 22
est filtré depuis l'extérieur du laboratoire (`195.220.223.24`), alors que
Yargla est joignable sans interaction. Et la clé acceptée par vm1 est sur
Yargla, pas sur le Mac — les identités par défaut de Yargla sont d'ailleurs
refusées, la clé doit être passée par `-i`. `stage.sh vm1` relaie donc par
Yargla (`hpc/relais_vm1.sh`, exécuté sur Yargla) au lieu d'un ProxyJump, qui
ferait porter l'authentification au Mac.

**Comparabilité entre machines, vérifiée et non supposée.** Deux checkpoints
MACE cohabitent dans `~/.cache/mace` sur Yargla et ce ne sont pas le même
modèle : 13 meV d'écart sur l'énergie du diamant, aucune erreur levée, et des
résultats silencieusement incomparables. `hpc/e_diamant.py` imprime cette
énergie sur six décimales et sert de **signature du modèle** : `stage.sh` la
compare entre le Mac et la machine distante, `vm1_lot.slurm` s'en sert pour
**résoudre** le bon checkpoint au lieu de coder son nom en dur, et
`yargla_lot.slurm` en fait une assertion au démarrage. Mesuré sur ce Mac :
**−18.149009 eV** pour 2 atomes à a = 3.567 Å, identique à la valeur publiée
par le jumeau pour `5yyxdm76` sur Yargla.

## 11. L'objectif : pourquoi E_f brut ne suffit pas

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

## 12. Stratégie de recherche sur (x, y, z)

Trois étages, du certain au heuristique.

**Étage 1 — exhaustif.** Supermailles 8, 16, 32 sites, `k ≤ 4`, tous les
motifs. Produit la première carte E_f / ΔE_hull sur le simplexe de
composition, et elle est *complète* : aucune structure de cette taille
n'échappe à l'énumération. Le dimensionnement est connu d'avance :
`carte_composition.py` donne 52 compositions et 37 ternaires pour la seule
décoration canonique, et `gen_templates.py` donne le nombre de structures
distinctes après réduction primitive — c'est lui, et non le nombre d'ensembles
de lacunes, qui fixe le coût en relaxations.

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

## 13. Ce que la méthode garantit, et ce qu'elle ne garantit pas

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
- la méthode **ne produit pas de cristaux moléculaires** avec la contrainte
  ternaire, et le 1D y est marginal : c'est démontré au §6, pas constaté par
  manque d'exploration ;
- que « dynamiquement stable » signifie autre chose qu'un **minimum local du
  potentiel MACE** — c'est tout ce que disent les phonons du jumeau ;
- la **stabilité thermodynamique** : voir §8, l'attente raisonnable est
  +0.2 à +0.8 eV/atome au-dessus de l'enveloppe moléculaire.

## 14. Première validation : la méthode retrouve le meilleur candidat du jumeau

*(Témoin de validation, pas candidat : c'est un binaire, donc exclu des
campagnes par le cahier des charges — obtenu ici avec `--binaires`.)*

La plus petite instance possible — maille conventionnelle 1×1×1 (8 sites),
**une** lacune, décoration canonique — donne :

    7 atomes,  C3N4,  groupe d'espace 215 (P-43m),  5.86 Å³/atome

C'est **exactement** `mp-570377` sg 215, le meilleur candidat de la campagne 1
du projet jumeau : la blende lacunaire, C et N tous deux sp³, azote pyramidal.
Trouvée là-bas par criblage de 1417 parents Materials Project, elle est ici le
premier terme d'une famille, obtenu sans base de données. La conception est
cohérente avec un résultat déjà établi par une voie indépendante — et elle
place ce résultat dans une série, ce que la voie « template MP » ne faisait pas.

## 15. Arborescence et intégration

    dia_cno/lattice.py     réseau diamant : demi-liaisons périodiques, symétrie,
                           verifie_reseau() (audit des bords avant énumération)
    dia_cno/vacancies.py   énumération des lacunes, décorations, règle de Lewis,
                           diagnostic_images() (interaction avec les images)
    dia_cno/templates.py   construction, remise à l'échelle, primitive, signature
    scripts/gen_templates.py     CLI : lacunes -> cif/ + templates_manifest.json
    scripts/relax_lot.py         CLI : relaxation MACE + validation + E_f + ΔE_dec
    scripts/carte_composition.py CLI : domaine (x, y, z) atteignable, sans calcul d'énergie
    scripts/dimensionnalite.py   CLI : dimensionnalité en fonction du taux de lacunes
    hpc/e_diamant.py             signature du modèle MACE (énergie du diamant, 6 décimales)
    hpc/stage.sh                 transfert + vérifications distantes (yargla, vm1)
    hpc/relais_vm1.sh            relais Yargla -> vm1 (exécuté sur Yargla)
    hpc/yargla_lot.slurm         40 tâches CPU, shards entrelacés
    hpc/vm1_lot.slurm            8 processus sur un H100, checkpoint résolu au lancement

Le manifeste est écrit **au format du projet jumeau**
(`templates_manifest.json` : `source_id`, `decoration`, `child_formula`,
`spacegroup`, `classes`, ...), donc consommable sans adaptation par ses
`pools_dim.py`, sa relaxation, ses phonons, son `lot_dft.py` et son rapport.
`dia_cno.jumeau()` localise le projet jumeau (variable d'environnement
`CNO_UNDER_PRESSURE`) et le rend importable.

Environnement d'exécution : `conda run -n mlip python ...`
(mace 0.3.12, ase 3.29.0, phonopy 4.7.2, torch 2.2.2, torch-dftd).
