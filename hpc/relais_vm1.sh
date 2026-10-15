#!/bin/bash
# Relais Yargla -> vm1. Ce script s'exécute SUR YARGLA, pas sur le Mac.
#
#   bash ~/relais_dia/relais_vm1.sh <clé_privée|-> <nom_du_lot> <E_diamant_du_Mac>
#
# La clé peut valoir "-" ou être vide : on laisse alors la configuration ssh de
# Yargla résoudre l'hôte, l'utilisateur et l'identité. C'est le cas normal,
# parce que `ssh vm1` y est déjà configuré et fonctionne sans interaction.
# Passer un chemin de clé n'est utile que pour contourner cette configuration.
#
# POURQUOI UN RELAIS. Mesuré : vm1-ic2mp.labo.univ-poitiers.fr résout bien
# (195.220.223.24) mais son port 22 est injoignable depuis l'extérieur du
# laboratoire, alors que Yargla l'est. La seule route Mac -> vm1 passe donc par
# Yargla. Et ProxyJump ne convient pas : avec lui l'authentification auprès de
# vm1 se ferait depuis le Mac, avec une clé du Mac, alors que la clé acceptée
# par vm1 est sur Yargla. On relaie donc en deux temps, et c'est Yargla qui
# s'authentifie.
#
# Mesuré aussi : Yargla -> vm1 échoue avec les identités par défaut
# (« Permission denied (publickey) »). La clé doit être donnée explicitement
# par -i, d'où le premier argument. Ce script ne cherche aucune clé et n'en lit
# aucune : il passe le chemin qu'on lui donne à ssh.

set -euo pipefail

CLE=${1:-}
[ "$CLE" = "-" ] && CLE=""
LOT=${2:?nom du lot de templates}
E_MAC=${3:-}
# Alias de la configuration ssh de Yargla, qui porte déjà l'hôte, l'utilisateur
# et l'identité. Le nom complet reste utilisable via VM1_CIBLE.
CIBLE=${VM1_CIBLE:-vm1}
RELAIS=${RELAIS:-$HOME/relais_dia}
DISTANT=${DISTANT:-diamant_to_CNO}
# Le jumeau est livré AVEC ce projet, dans son propre sous-répertoire. Le
# déploiement préexistant de vm1 (~/cno_run) est plus ancien -- pas de
# scripts/funnel_table.py -- et porte les données de l'utilisateur : on ne
# l'écrase pas, on ne s'en sert pas.
JUMEAU=${JUMEAU:-$DISTANT/jumeau}
# $HOME entre apostrophes À DESSEIN : ce chemin doit être résolu sur VM1
# (/home/gfrapper), pas sur Yargla (/home/gilles). Sans les apostrophes, Yargla
# l'expanse en envoyant la commande et vm1 reçoit un chemin inexistant --
# symptôme observé : « bash: python: command not found ».
ENV_GPU=${ENV_GPU:-'$HOME/miniforge3/envs/mace_gpu'}

SSH=(ssh -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new)
if [ -n "$CLE" ]; then
    [ -f "$CLE" ] || { echo "clé introuvable sur Yargla : $CLE"; exit 1; }
    SSH+=(-i "$CLE")
fi
SSH+=("$CIBLE")

echo "== vm1 joignable depuis Yargla ?"
"${SSH[@]}" 'hostname; echo "   $(nproc) coeurs"' || {
    echo "échec de la connexion à $CIBLE${CLE:+ avec $CLE}"; exit 1; }

echo "== arborescence sur vm1"
"${SSH[@]}" "mkdir -p ~/$DISTANT/code ~/$DISTANT/templates/$LOT ~/$DISTANT/runs ~/$DISTANT/logs ~/$DISTANT/cache"

echo "== transfert du code, du jumeau et des templates"
"${SSH[@]}" "tar xzf - -C ~/$DISTANT/code" < "$RELAIS/code.tgz"
"${SSH[@]}" "rm -rf ~/$DISTANT/templates/$LOT/cif"
"${SSH[@]}" "tar xzf - -C ~/$DISTANT/templates/$LOT" < "$RELAIS/templates.tgz"
"${SSH[@]}" "mkdir -p ~/$DISTANT/jumeau && tar xzf - -C ~/$DISTANT/jumeau" < "$RELAIS/jumeau.tgz"

echo "== vérifications sur vm1"
# Les mêmes que pour Yargla, plus le GPU. L'énergie du diamant est la
# signature du modèle : si elle diffère de celle du Mac, les deux machines
# n'utilisent pas le même checkpoint et aucun résultat n'est comparable.
"${SSH[@]}" "
set -e
export PATH=$ENV_GPU/bin:\$PATH
export CNO_UNDER_PRESSURE=\$HOME/$JUMEAU
export PYTHONPATH=\$HOME/$DISTANT/code:\$CNO_UNDER_PRESSURE
export KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1
# Épingler un checkpoint du cache : sans MACE_MODEL, mace_mp() TÉLÉCHARGE
# 44 Mo sur le nœud de tête (constaté). On prend le premier candidat du cache ;
# si sa signature est fausse la ligne E(diamant) le dira, et vm1_lot.slurm
# résout proprement le bon au lancement du job.
export MACE_MODEL=\${MACE_MODEL:-\$(ls \$HOME/.cache/mace/* 2>/dev/null | head -1)}
cd \$HOME/$DISTANT/code
python -c 'import mace, torch_dftd, ase, phonopy; print(\"   environnement ok\")'
# CUDA est NORMALEMENT indisponible ici : sur vm1 les GPU ne sont visibles
# que dans un job Slurm (nvidia-smi répond « Insufficient Permissions » sur le
# nœud de tête). C'est vm1_lot.slurm qui le vérifie là où ça compte.
python -c 'import torch; print(\"   torch ok, cuda sur le nœud de tête :\", torch.cuda.is_available(), \"(normal, le GPU est derrière Slurm)\")' 2>/dev/null
[ -d \"\$CNO_UNDER_PRESSURE/cno_csp\" ] || { echo \"   projet jumeau ABSENT: \$CNO_UNDER_PRESSURE\"; exit 1; }
echo '   projet jumeau présent'
echo \"   E(diamant) sur vm1 = \$(python hpc/e_diamant.py 2>/dev/null) eV\"
echo \"   templates: \$(ls \$HOME/$DISTANT/templates/$LOT/cif | wc -l)\"
"

cat <<FIN

E(diamant) sur le Mac : ${E_MAC:-non transmis}
Elle doit être IDENTIQUE à celle de vm1 ci-dessus, à la 6e décimale.

Soumission, depuis vm1 (le GPU n'est pas visible du nœud de tête : il faut
passer par Slurm, cf. hpc/README.md règle 1) :
  ssh yargla
  ssh $CIBLE
  cd ~/$DISTANT
  sbatch --export=ALL,TEMPLATES=templates/$LOT,N_SHARDS=8,OUT=runs/lot1_gpu.json \\
         code/hpc/vm1_lot.slurm
FIN
