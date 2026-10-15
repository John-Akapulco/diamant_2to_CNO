#!/bin/bash
# Relais Yargla -> vm1. Ce script s'exécute SUR YARGLA, pas sur le Mac.
#
#   bash ~/relais_dia/relais_vm1.sh <clé_privée> <nom_du_lot> <E_diamant_du_Mac>
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

CLE=${1:?chemin de la clé privée à utiliser pour vm1}
LOT=${2:?nom du lot de templates}
E_MAC=${3:-}
CIBLE=${VM1_CIBLE:-gfrapper@vm1-ic2mp.labo.univ-poitiers.fr}
RELAIS=${RELAIS:-$HOME/relais_dia}
DISTANT=${DISTANT:-diamant_to_CNO}
JUMEAU=${JUMEAU:-C_N_O_under_Pressure/code}
ENV_GPU=${ENV_GPU:-$HOME/miniforge3/envs/mace_gpu}

[ -f "$CLE" ] || { echo "clé introuvable sur Yargla : $CLE"; exit 1; }
SSH=(ssh -i "$CLE" -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new "$CIBLE")

echo "== vm1 joignable depuis Yargla ?"
"${SSH[@]}" 'hostname; echo "   $(nproc) coeurs"' || {
    echo "échec de la connexion à $CIBLE avec $CLE"; exit 1; }

echo "== arborescence sur vm1"
"${SSH[@]}" "mkdir -p ~/$DISTANT/code ~/$DISTANT/templates/$LOT ~/$DISTANT/runs ~/$DISTANT/logs ~/$DISTANT/cache"

echo "== transfert du code et des templates"
"${SSH[@]}" "tar xzf - -C ~/$DISTANT/code" < "$RELAIS/code.tgz"
"${SSH[@]}" "rm -rf ~/$DISTANT/templates/$LOT/cif"
"${SSH[@]}" "tar xzf - -C ~/$DISTANT/templates/$LOT" < "$RELAIS/templates.tgz"

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
cd \$HOME/$DISTANT/code
python -c 'import mace, torch_dftd, ase, phonopy; print(\"   environnement ok\")'
python -c 'import torch; print(\"   cuda:\", torch.cuda.is_available(), torch.cuda.device_count(), \"GPU\")'
[ -d \"\$CNO_UNDER_PRESSURE/cno_csp\" ] || { echo \"   projet jumeau ABSENT: \$CNO_UNDER_PRESSURE\"; exit 1; }
echo '   projet jumeau présent'
echo \"   E(diamant) sur vm1 = \$(python hpc/e_diamant.py 2>/dev/null) eV\"
echo \"   templates: \$(ls \$HOME/$DISTANT/templates/$LOT/cif | wc -l)\"
"

cat <<FIN

E(diamant) sur le Mac : ${E_MAC:-non transmis}
Elle doit être IDENTIQUE à celle de vm1 ci-dessus, à la 6e décimale.

Soumission, depuis vm1 :
  ssh -i $CLE $CIBLE
  cd ~/$DISTANT
  sbatch --export=ALL,TEMPLATES=templates/$LOT,N_SHARDS=8,OUT=runs/lot1_gpu.json \\
         code/hpc/vm1_lot.slurm
FIN
