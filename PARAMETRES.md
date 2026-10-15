# Tous les paramètres de génération

Référence exhaustive des grandeurs à renseigner pour engendrer les structures.
Chaque ligne indique **où** se règle le paramètre : option de ligne de commande
(`--opt`), variable d'environnement (`ENV`), ou constante de code (`code`) —
ces dernières ne sont pas exposées aujourd'hui, et le signaler fait partie de
la réponse.

La colonne « lot 2 » donne la valeur effectivement utilisée pour la campagne en
cours (job 382 sur vm1).

## A. Le réseau parent

| paramètre | où | défaut | lot 2 | effet |
|---|---|---|---|---|
| `a` du diamant | `code` : `lattice.A_DIAMANT` | 3.567 Å | 3.567 | paramètre de maille du parent. Valeur expérimentale ; la relaxation la corrige ensuite, donc elle ne fixe que le point de départ |
| rayon de liaison | `code` : `lattice.CUTOFF_LIAISON` | 1.9 Å | 1.9 | sépare 1ᵉʳ voisin (1.545 Å) et 2ᵈ (2.52 Å). **Ne pas toucher sans refaire l'audit** `verifie_reseau()` : c'est lui qui garantit 4 liaisons par site |
| supermailles | `--mailles` | `1x1x1 2x1x1 2x2x1` | `1x1x1 2x1x1 2x2x1` + `2x2x2` | répétitions de la maille **conventionnelle** (8 sites). Multiples de 8 sites. En dessous de 64 sites les lacunes interagissent avec leurs images (§5 de CONCEPTION.md) |

La maille **primitive** (2 sites) est volontairement écartée comme point de
départ : sa multiplicité de liaison vaut 4 (deux atomes liés par quatre
images), ce qui casse tout comptage naïf de voisins.

## B. Les lacunes

| paramètre | où | défaut | lot 2 | effet |
|---|---|---|---|---|
| nombre max de lacunes | `--kmax` | 3 | 6 (≤32 sites) / 4 (64 sites) | borne l'énumération. **Le coût explose avec k**, et la composition en dépend directement : `n_N + 2·n_O = 4k − 2b` |
| coordinence minimale | `--zmin` | 2 | 2 | 2 = pas de site monocoordiné. 1 n'a de sens qu'avec le motif `oterm`. 0 est toujours exclu (atome isolé) |
| précision de symétrie | `code` : `permutations_symetrie(symprec)` | 1e-4 | 1e-4 | tolérance pour identifier les opérations du groupe d'espace du parent, donc pour dédoublonner les ensembles de lacunes à symétrie près |

Un `kmax` différent par taille de maille demande **deux appels** à
`gen_templates.py` puis `scripts/fusionne.py` — une valeur unique serait soit
trop pauvre en petite maille, soit intraitable en grande.

## C. La décoration

| paramètre | où | défaut | lot 2 | effet |
|---|---|---|---|---|
| motifs autorisés | `--motifs` | `canonique` | `canonique` | `canonique` : z=4→C, z=3→N, z=2→O, **déficit nul partout, toujours valide au sens de Lewis**. `sp2` ajoute z=3→C. `nbent` ajoute z=2→N. `oterm` ajoute z=1→O (exige `--zmin 1`, et n'a de sens qu'avec `sp2`, le carbonyle demandant un carbone trigonal) |
| binaires | `--binaires` | exclus | exclus | sans ce drapeau, C **et** N **et** O sont exigés, à l'énumération et non en filtre aval |
| décorations max par ensemble | `code` : `decorations(max_par_lacune)` | 8 | 8 | plafonne l'énumération quand plusieurs motifs sont actifs. Sans effet en `canonique` seul, où la décoration est unique |
| revêtement du couplage de Lewis | `code` : `_couplage_parfait(cover)` | 2 | 2 | taille du revêtement (2×2×2) sur lequel on cherche le couplage parfait. Évite qu'un atome soit apparié à sa propre image, c'est-à-dire porte une double liaison avec lui-même |

## D. La maille produite

| paramètre | où | défaut | lot 2 | effet |
|---|---|---|---|---|
| remise à l'échelle | `code` : `construit(rescale)` | `True` | `True` | facteur **isotrope**, moyenne sur les liaisons du rapport des sommes de rayons covalents. C-N 1.47 Å et C-O 1.43 Å étant plus courtes que C-C 1.545 Å, sans lui la maille part trop grande |
| précision de symétrisation | `code` : `primitive(symprec)` | 1e-3 | 1e-3 | tolérance de `spglib.standardize_cell(to_primitive=True)`. **Plus elle est lâche, plus on réduit** — et plus on risque de fusionner deux structures distinctes |
| précision de signature | `code` : `signature(symprec)` | 1e-3 | 1e-3 | même tolérance pour la clé (groupe d'espace, orbites de Wyckoff décorées) qui dédoublonne avant relaxation |
| plafond d'atomes | `--max-atomes` | 24 | 64 | écarte les mailles primitives trop grosses. 24 est le plafond DFT du jumeau ; 64 convient à MACE |

## E. La relaxation — elle fixe la maille finale

| paramètre | où | défaut | lot 2 | effet |
|---|---|---|---|---|
| pression | `code` : `relax(pressure_gpa)` | 0.0 GPa | 0.0 | pression hydrostatique. **Non exposé en ligne de commande dans ce projet**, alors que c'est le paramètre du jumeau |
| critère de force | `--fmax` | 1e-3 eV/Å | 1e-3 | serré à dessein : on tranche « N pyramidal vs N plan » sur quelques degrés, et 1e-2 laisse des résidus de cet ordre |
| pas maximum | `code` : `relax(max_steps)` | 800 | 800 | après FIRE (200 pas, fmax 0.05) puis LBFGS |
| degrés de liberté | fixé | positions + **volume + forme** | idem | `FrechetCellFilter` : relaxation complète de la maille |
| symétrie | `code` : `relax(fix_symmetry)` | `False` | `False` | `False` laisse la symétrie se briser — une brisure spontanée est une information physique |
| dispersion D3 | automatique | selon dimensionnalité | 3D sans, 0D/1D/2D avec | sans D3 rien ne retient feuillets et chaînes, leur maille gonfle sans limite physique |
| modèle | `ENV` : `MACE_MODEL` | `medium` | `5yyxdm76` sur vm1 | **à épingler sur un calculateur** : sans lui `mace_mp()` tente un téléchargement, impossible sur un nœud de production |
| précision | fixé | float64 | float64 | nécessaire pour l'optimisation de géométrie |
| matériel | `ENV` : `CNO_DEVICE` | `cpu` | `cuda` | sur vm1, plus `CUDA_VISIBLE_DEVICES` réparti par shard |

## F. La validation — elle décide ce qui compte comme réussi

Seuils de `cno_csp.config.GeometryThresholds` (projet jumeau). Ils ne changent
aucune structure ; ils changent le **verdict** porté sur elle.

| paramètre | défaut | effet |
|---|---|---|
| `neighbor_scale` | 1.25 | détection des voisins : `d_ij < scale·(rcov_i + rcov_j)` |
| `gap_ratio_warn` | 1.15 | signale une coordinence douteuse (saut de distance trop faible) |
| `c_tet_q_min` | 0.80 | tétraédricité minimale d'un carbone CN=4 |
| `c_trig_angle_sum_min` | 352° | au-delà : carbone trigonal plan |
| `n_pyr_angle_sum_max` | 350° | en dessous : azote pyramidal |
| `o_bent_angle_min` / `max` | 85° / 165° | fenêtre de l'oxygène coudé |
| `allow_planar_n` | `True` | accepte l'azote trigonal plan |
| `allow_bent_n` | `True` ici | azote dicoordiné coudé, motif −N= |
| `allow_terminal_o` | `True` ici | oxygène terminal, motif >C=O |
| `allow_terminal_n` | `False` | nitrile −C#N : déficit 2, hors du cadre d'un simple couplage |

**La zone 350–352° n'est pas classée**, délibérément : forcer « plan » ou
« pyramidal » sur un écart de 1° injecterait du bruit. C'est exactement ce qui
a produit les 2 structures « KO » du lot 1, à 350.9° et 350.1°.

## G. L'évaluation énergétique

| paramètre | où | valeur | effet |
|---|---|---|---|
| μ_C | calculé | **graphite** relaxé | allotrope de référence de l'enthalpie de formation, et le plus bas des deux pour MACE |
| μ_N, μ_O | calculé | N2, O2 isolés en boîte de 12 Å | **les grandeurs les moins fiables du calcul** : hors domaine d'entraînement de MACE-MP |
| E(CO2) | calculé | molécule en boîte de 14 Å | sert l'enveloppe de décomposition {graphite, N2, CO2, O2} |
| niveau des références | automatique | apparié à la structure (avec/sans D3) | jamais mélangé : une structure relaxée avec D3 est évaluée contre des références avec D3 |
| cache | `--cache` | `cache/mu_D3{0,1}.json` | six relaxations par niveau de théorie, partagées par tous les shards |

Barre d'erreur mesurée par `controle_mu`, à garder devant les yeux sur tout
E_f de ce dépôt : **+0.067** (CO2) et **−0.229** (N2O) eV/atome sans D3,
**+0.110** et **−0.233** avec.

## Ce qui n'est pas exposé en ligne de commande

Par ordre d'intérêt à l'être : la **pression** (`pressure_gpa`, le paramètre
central du projet jumeau), le paramètre de maille du parent et le rayon de
liaison, les trois `symprec`, `max_par_lacune`, et `cover`. Tout se règle
aujourd'hui dans le code.
