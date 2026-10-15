# Règles d'exploitation des machines de calcul

À lire avant de lancer quoi que ce soit sur Yargla ou vm1. Les deux règles
ci-dessous ne sont pas des conventions de style : chacune, enfreinte, produit
soit une gêne pour les autres utilisateurs, soit un job qui échoue **après** la
file d'attente, c'est-à-dire au pire moment.

## Règle 1 — Aucun calcul sur le nœud de connexion

Le nœud de connexion (*login node*) sert à **transférer, soumettre et
consulter**. Il ne sert pas à calculer. Tout calcul passe par SLURM et
s'exécute sur les **nœuds de production** :

```bash
# CORRECT : on soumet depuis le nœud de connexion, ça s'exécute ailleurs
ssh yargla
cd ~/diamant_to_CNO
sbatch --export=ALL,TEMPLATES=templates/templates_dia_t1,N_SHARDS=20,OUT=runs/lot1.json \
       code/hpc/yargla_lot.slurm

# INTERDIT : ceci calcule sur le nœud de connexion
ssh yargla 'cd ~/diamant_to_CNO && python code/scripts/relax_lot.py ...'
```

Le nœud de connexion est partagé par tous les utilisateurs et n'a ni les cœurs
ni l'isolation d'un nœud de production. Y lancer une relaxation MACE, même
d'une seule structure, le dégrade pour tout le monde — et les six relaxations
de référence (graphite, diamant, N2, O2, CO2, N2O) sont des calculs à part
entière.

**Garde-fou dans le code.** `scripts/relax_lot.py` refuse de démarrer sur une
machine qui a `sbatch` mais pas de `SLURM_JOB_ID` — autrement dit, sur un nœud
de connexion hors job. Le message indique quoi faire. L'option
`--hors-slurm` force le passage, et n'a de raison d'être que pour un
diagnostic très court et délibéré.

**Ce qui reste légitime sur le nœud de connexion**, et rien d'autre :

| opération | pourquoi c'est admis |
|---|---|
| `hpc/stage.sh` (transfert, `tar`/`ssh`) | entrées-sorties, pas de calcul |
| `python hpc/e_diamant.py` | un point d'énergie sur **2 atomes**, quelques secondes — c'est la signature du modèle, et elle doit être vérifiée avant de soumettre |
| `import mace, ase, phonopy` | contrôle d'environnement |
| `sbatch`, `squeue`, `scancel`, `tail` sur les logs | exploitation |
| `pip install`, téléchargement d'un checkpoint | **voir règle 2** : c'est le seul endroit où c'est possible |

## Règle 2 — Internet n'existe que sur le nœud de connexion

Les nœuds de production **n'ont aucun accès réseau sortant**. Tout ce dont un
job a besoin doit être présent sur disque avant la soumission. Conséquences
concrètes, toutes déjà câblées dans les scripts de ce dépôt :

- **Checkpoint MACE.** `mace_mp()` tente un téléchargement s'il ne trouve pas
  de modèle local, et échoue donc sur un nœud de production — après la file
  d'attente. D'où `MACE_MODEL`, qui pointe un checkpoint local, dans
  `yargla_lot.slurm` et `vm1_lot.slurm`. Le jumeau a constaté la panne
  (job 63857 : « Model download failed and no local model found »).
- **Materials Project, Alexandria.** Toute requête à une base en ligne se fait
  sur le Mac ou sur le nœud de connexion, jamais dans un job. Dans ce projet
  la question ne se pose pas — le template est le diamant, engendré
  localement — mais elle se pose pour le jumeau.
- **`pip install`, `conda install`.** Sur le nœud de connexion uniquement, et
  avant de soumettre.
- **Potentiels chimiques.** Ils sont calculés *dans* le job et mis en cache
  dans `cache/mu_D3*.json` : six relaxations de molécules et de solides, aucun
  téléchargement. `yargla_lot.slurm` les calcule une fois avant de lancer les
  shards, pour que deux shards n'écrivent pas le même fichier de cache en
  concurrence.

## Topologie d'accès

| machine | accès | remarque |
|---|---|---|
| **yargla** | `ssh yargla` depuis le Mac, sans interaction | alias dans `~/.ssh/config`, 40 cœurs, partition `defq` |
| **vm1** | **par relais depuis Yargla** | `vm1-ic2mp.labo.univ-poitiers.fr` (195.220.223.24) résout, mais son port 22 est filtré depuis l'extérieur du laboratoire |

Pour vm1, `ProxyJump` ne convient pas : avec lui l'authentification se ferait
depuis le Mac avec une clé du Mac, alors que la clé acceptée par vm1 est sur
Yargla — et les identités par défaut de Yargla sont refusées par vm1, la clé
doit être passée par `-i`. D'où `hpc/relais_vm1.sh`, qui s'exécute **sur
Yargla**, et `VM1_KEY` qui est le chemin de la clé **sur Yargla** :

```bash
VM1_KEY=/home/gilles/.ssh/<nom_de_la_cle> bash hpc/stage.sh vm1 templates_dia_t1
```

Les GPU de vm1 ne sont accessibles que par SLURM (`-p gpu --gres=gpu:1`) : la
règle 1 y vaut donc aussi, et même plus strictement.

## Comparabilité entre machines

Deux checkpoints MACE cohabitent dans `~/.cache/mace` sur Yargla et **ce ne
sont pas le même modèle** : 13 meV d'écart sur l'énergie du diamant, aucune
erreur levée, et des résultats silencieusement incomparables. La signature est
donc vérifiée systématiquement :

```
E(diamant, 2 atomes, a = 3.567 Å, sans D3) = -18.149009 eV
```

`hpc/e_diamant.py` imprime cette valeur, et **stdout ne porte que le nombre** :
MACE n'écrit pas ses messages de chargement au même endroit selon les versions
(stderr avec mace 0.3.12 sur le Mac, stdout avec 0.3.16 sur Yargla), et un
appelant qui comparait la chaîne récupérait une variable polluée. `stage.sh`
compare les deux machines, `yargla_lot.slurm` en fait une assertion au
démarrage, `vm1_lot.slurm` s'en sert pour **résoudre** le bon checkpoint au
lieu de coder son nom en dur.
