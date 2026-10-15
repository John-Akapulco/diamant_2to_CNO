# diamant_to_CNO

Engendrer des structures C-N-O en **creusant le diamant** : on retire des
atomes de carbone ("lacunes") et on décore les sites survivants selon leur
coordinence résiduelle, de sorte que chaque atome réalise un des
environnements du cahier des charges.

    4 voisins -> C tétraédrique      2 voisins -> O coudé  (ou N coudé, -N=)
    3 voisins -> N pyramidal         1 voisin  -> O terminal (>C=O)
                 (ou C sp2)

La géométrie est obtenue gratuitement : dans le diamant les angles valent
déjà 109.47°, donc un site à 3 voisins est pyramidal (NH3 : 320° de somme
d'angles, ici 328°) et un site à 2 voisins est coudé. Aucune pré-distorsion,
seulement une remise à l'échelle isotrope de la maille.

**Tous les paramètres de génération sont listés dans
[`PARAMETRES.md`](PARAMETRES.md)** — réseau parent, lacunes, décoration, maille
produite, relaxation, seuils de validation et références énergétiques, avec
pour chacun où il se règle (option, variable d'environnement ou constante de
code) et la valeur de la campagne en cours.

**La conception complète est dans [`CONCEPTION.md`](CONCEPTION.md)** : pourquoi
la coordinence détermine l'élément, pourquoi la règle de Lewis se réduit à un
couplage parfait, pourquoi la décoration canonique (`z=4→C, 3→N, 2→O`) est
toujours valide, comment la composition est contrainte par la topologie des
lacunes, et comment optimiser (x, y, z).

**Contrainte du cahier des charges : pas de binaires.** C **et** N **et** O
dans la même structure, exigé à l'énumération et non filtré après. `C3N4` de la
lacune isolée est donc un témoin de validation, pas un candidat.

**Bords périodiques.** Le graphe est stocké en demi-liaisons avec vecteurs
d'image, jamais en ensembles de voisins : sous périodicité deux sites peuvent
être liés par plusieurs images. Et il faut **64 sites** pour qu'une lacune
cesse d'interagir avec ses propres images — en dessous, une structure est un
réseau ordonné de lacunes, ce que chaque template déclare dans son manifeste.

**Dimensionnalité, mesurée et non espérée.** C'est un générateur de
**charpentes 3D**. Le 2D n'est abondant qu'en petite maille et à forte
concentration de lacunes — à taux égal (18.8 %), la part de 2D tombe de 37 %
en maille 16 sites à 7.6 % en maille 32 sites, parce qu'en petite maille les
lacunes **et leurs images** forment un plan qui tranche le cristal. Le
1D est marginal (37 % de lacunes, motifs π seulement) et le **0D est fermé**
dès qu'on exige du carbone : le carbone demande z ≥ 3, donc une position
*intérieure*, alors qu'un petit diamantoïde n'a que de la surface — le cycle à
6 donne O6, la cage adamantane N4O6, sans un seul carbone. Détail au §6 de
`CONCEPTION.md`.

Trois résultats qui orientent tout le reste :

- **la décoration canonique est de déficit nul partout**, donc valide au sens
  de Lewis sans condition : chaque liaison pendante est passivée par une paire
  libre, jamais par un radical ;
- **l'oxygène a une signature topologique exacte** : seules deux lacunes
  secondes voisines (2.52 Å, ⟨110⟩) partagent un voisin, et exactement un.
  C'est ce voisin qui devient O. La composition se commande donc par
  l'agrégation des lacunes ;
- **la plus petite instance redonne `C3N4` sg 215 à 7 atomes**, c'est-à-dire
  `mp-570377`, le meilleur candidat de la campagne 1 du projet jumeau, trouvé
  là-bas par criblage de 1417 parents Materials Project.

## Utilisation

```bash
# 1. engendrer les templates (lacunes + décorations), ternaires seulement
python scripts/gen_templates.py --mailles 1x1x1 2x1x1 2x2x1 2x2x2 --kmax 3 \
    --motifs canonique --max-atomes 64 --out templates_dia

# domaine de composition atteignable, sans aucun calcul d'énergie
python scripts/carte_composition.py --kmax 4

# 2. relaxer au MACE (volume + forme + positions), valider, calculer E_f
python scripts/relax_lot.py templates_dia --out runs/lot1.json
```

Environnement : `conda run -n mlip python ...`, ou directement
`~/miniconda3/envs/mlip/bin/python -u` (mace 0.3.12, ase 3.29.0, phonopy 4.7.2,
torch 2.2.2, torch-dftd). `conda run` tamponne la sortie : pour suivre un lot
en direct, utiliser l'interpréteur directement.

## Où tournent les calculs

**Les règles d'exploitation des machines sont dans [`hpc/README.md`](hpc/README.md)**,
et il y en a deux qui ne se négocient pas : *aucun calcul sur le nœud de
connexion* — on soumet par SLURM, ça s'exécute sur les nœuds de production — et
*Internet n'existe que sur le nœud de connexion*, donc tout ce dont un job a
besoin (checkpoint MACE en tête) doit être sur disque avant la soumission.
`scripts/relax_lot.py` refuse de démarrer sur une machine qui a `sbatch` sans
`SLURM_JOB_ID`.


En local sur le Mac pour la mise au point, sur **Yargla** (CPU, 40 cœurs) ou
sur le **H100 de vm1** pour les campagnes. Le choix se fait sur les bancs du
jumeau — coût d'un appel énergie + forces MACE float64 sans D3 :

| atomes | Yargla 1 cœur | H100 vm1 | gain |
|---|---|---|---|
| 20 | 1391 ms | 62 ms | ×23 |
| 44 | 3407 ms | 37 ms | ×93 |
| 352 | 28474 ms | 89 ms | ×318 |

**Le gain croît avec la taille**, et ce projet travaille justement à 61–62
atomes dès qu'on veut éviter l'interaction d'images. En débit, le H100 partagé
entre 16 processus vaut ~150 cœurs Yargla. Deux réserves : D3 coûte cher sur
GPU (×4.7 à 352 atomes, alors que le pool 3D s'en passe), et la concurrence
sature vers 8 processus, d'où `N_SHARDS=8`.

    bash hpc/stage.sh yargla templates_dia_t1
    VM1_KEY=<clé sur yargla> bash hpc/stage.sh vm1 templates_dia_t1

**vm1 se joint par relais, pas directement.** Mesuré : vm1 résout
(195.220.223.24) mais son port 22 est injoignable depuis l'extérieur du
laboratoire, alors que Yargla l'est. ProxyJump ne conviendrait pas — avec lui
l'authentification auprès de vm1 se ferait depuis le Mac, avec une clé du Mac,
alors que la clé acceptée par vm1 est sur Yargla. C'est donc Yargla qui
s'authentifie (`hpc/relais_vm1.sh`, exécuté là-bas), et `VM1_KEY` est le chemin
de la clé **sur Yargla** : les identités par défaut de Yargla sont refusées par
vm1.

`stage.sh` transfère code et templates, puis vérifie **à distance**
l'environnement, la présence du projet jumeau et — surtout — que le checkpoint
MACE y donne la **même** énergie du diamant qu'ici : −18.149009 eV à 2 atomes.
Deux checkpoints cohabitent dans `~/.cache/mace` sur Yargla et ce ne sont pas
le même modèle (13 meV d'écart, aucune erreur levée, résultats silencieusement
incomparables).

`hpc/yargla_lot.slurm` (40 tâches CPU) et `hpc/vm1_lot.slurm` (8 processus sur
un GPU) lancent ensuite N_SHARDS processus d'un thread : MACE en float64 ne
sature pas les cœurs, c'est le nombre de *processus* qui occupe la machine. Les
shards sont entrelacés pour que chacun reçoive un mélange de petites et de
grandes mailles, et chacun réécrit son JSON après chaque structure — un lot
interrompu reste exploitable. Sur vm1 le checkpoint n'est pas codé en dur : le
script le **résout** en gardant celui qui reproduit l'énergie du diamant du Mac
(`hpc/e_diamant.py`).

Prérequis : `C_N_O_under_pressure` doit déjà être déployé sur la machine, ce
projet importe son outillage. `CNO_UNDER_PRESSURE` le localise.

## Projet jumeau

Tout l'outillage aval est réutilisé depuis
[`C_N_O_under_pressure`](https://github.com/John-Akapulco/C_N_O_under_pressure) :
relaxation (`cno_csp.relax`), phonons (`cno_csp.phonons`), entrées VASP
(`cno_csp.dft`), validateur (`cno_csp.validator`), dimensionnalité
(`cno_csp.geometry`), enthalpies de formation et décomposition
(`scripts/funnel_table.py`). `dia_cno.jumeau()` le localise (variable
d'environnement `CNO_UNDER_PRESSURE`, défaut `~/C_N_O_under_pressure`) et le
rend importable. Le manifeste produit ici est au format du jumeau, donc
consommable sans adaptation.
