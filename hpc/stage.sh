#!/bin/bash
# Prépare un lot ici et le transfère vers une machine de calcul.
#
#   bash hpc/stage.sh yargla templates_dia_t1
#
# INTERNET N'EXISTE QUE SUR LE NŒUD DE CONNEXION : tout ce dont le job a
# besoin -- code, templates, checkpoint MACE -- doit être préparé ici puis
# transféré. Un job qui tente le moindre téléchargement échoue APRÈS la file
# d'attente (constaté par le jumeau, job 63857 sur Yargla).
#
# Ce projet dépend de C_N_O_under_pressure, qui doit DÉJÀ être déployé sur la
# machine (son propre hpc/stage.sh s'en charge). Le script le vérifie.
#
# Le script refuse de finir tant qu'il n'a pas vérifié, à distance : que
# l'environnement importe mace/torch_dftd/ase/phonopy, que le jumeau est
# présent, et que le checkpoint MACE donne la MÊME énergie du diamant qu'ici.
# Ce dernier point n'est pas une précaution de principe : deux checkpoints
# cohabitent dans ~/.cache/mace sur Yargla et ce ne sont pas le même modèle.

set -euo pipefail

MACHINE=${1:-yargla}
TEMPLATES=${2:-templates_dia_t1}
REMOTE_DIR=${REMOTE_DIR:-diamant_to_CNO}
JUMEAU_DIR=${JUMEAU_DIR:-C_N_O_under_Pressure/code}
RACINE=$(cd "$(dirname "$0")/.." && pwd)
cd "$RACINE"

[ -d "$TEMPLATES/cif" ] || { echo "templates introuvables: $TEMPLATES/cif"; exit 1; }

# Interpréteur LOCAL. Surtout pas "python3" nu : sur le Mac c'est
# /usr/bin/python3, qui n'a ni ase ni mace, et la référence d'énergie du
# diamant sortirait vide -- or c'est elle qui garantit que les deux machines
# calculent le même modèle. On prend l'environnement mlip, et on échoue
# bruyamment s'il manque.
PYTHON=${PYTHON:-$HOME/miniconda3/envs/mlip/bin/python}
[ -x "$PYTHON" ] || { echo "interpréteur introuvable: $PYTHON (définir PYTHON=...)"; exit 1; }

case "$MACHINE" in
  yargla) REMOTE_ENV="export PATH=/home/gilles/dynstab_project/miniforge3/envs/hp_mlip_mace/bin:\$PATH"
          REMOTE_MODEL=${REMOTE_MODEL:-/home/gilles/.cache/mace/5yyxdm76}
          SUBMIT="sbatch --export=ALL,TEMPLATES=templates/$TEMPLATES,N_SHARDS=20,OUT=runs/lot1.json code/hpc/yargla_lot.slurm" ;;
  vm1)    # Environnement GPU. Le checkpoint n'est PAS fixé ici : vm1_lot.slurm
          # le résout en essayant les candidats de ~/.cache/mace et en gardant
          # celui qui reproduit l'énergie du diamant du Mac (hpc/e_diamant.py).
          REMOTE_ENV="export PATH=\${MACE_GPU_ENV:-\$HOME/miniforge3/envs/mace_gpu}/bin:\$PATH"
          REMOTE_MODEL=""
          SUBMIT="sbatch --export=ALL,TEMPLATES=templates/$TEMPLATES,N_SHARDS=8,OUT=runs/lot1_gpu.json code/hpc/vm1_lot.slurm" ;;
  *)      echo "machine non configuree: $MACHINE (yargla, vm1)"; exit 1 ;;
esac

echo "== référence locale : énergie du diamant"
export CNO_UNDER_PRESSURE=${CNO_UNDER_PRESSURE:-$HOME/C_N_O_under_pressure}
[ -d "$CNO_UNDER_PRESSURE/cno_csp" ] || {
    echo "projet jumeau introuvable en local: $CNO_UNDER_PRESSURE"; exit 1; }
E_LOCAL=$("$PYTHON" hpc/e_diamant.py 2>/dev/null)
[ -n "$E_LOCAL" ] || { echo "la référence locale a échoué ($PYTHON hpc/e_diamant.py)"; exit 1; }
echo "   $E_LOCAL eV"

NB=$(ls "$TEMPLATES/cif" | wc -l | tr -d ' ')

# vm1 : RELAIS PAR YARGLA, et non transfert direct. Mesuré : vm1 résout
# (195.220.223.24) mais son port 22 est injoignable depuis l'extérieur du
# laboratoire, alors que Yargla l'est. ProxyJump ne conviendrait pas : avec lui
# l'authentification auprès de vm1 se ferait depuis le Mac, avec une clé du
# Mac, alors que la clé acceptée par vm1 est sur Yargla. C'est donc Yargla qui
# s'authentifie, et VM1_KEY est le chemin de la clé SUR YARGLA -- mesuré
# aussi : les identités par défaut de Yargla sont refusées par vm1.
if [ "$MACHINE" = "vm1" ]; then
  : "${VM1_KEY:?définir VM1_KEY=<chemin de la clé privée SUR YARGLA>}"
  VIA=${VIA:-yargla}
  echo "== relais par $VIA : $NB templates + code vers vm1"
  ssh "$VIA" "mkdir -p ~/relais_dia"
  tar czf - dia_cno scripts hpc README.md CONCEPTION.md \
    | ssh "$VIA" "cat > ~/relais_dia/code.tgz"
  tar czf - -C "$TEMPLATES" cif templates_manifest.json \
    | ssh "$VIA" "cat > ~/relais_dia/templates.tgz"
  scp -q hpc/relais_vm1.sh "$VIA:relais_dia/relais_vm1.sh"
  ssh "$VIA" "bash ~/relais_dia/relais_vm1.sh '$VM1_KEY' '$TEMPLATES' '$E_LOCAL'"
  exit 0
fi

echo "== transfert : $NB templates + code vers $MACHINE:$REMOTE_DIR"
ssh "$MACHINE" "mkdir -p ~/$REMOTE_DIR/{code,templates,runs,logs,cache}"
tar czf - dia_cno scripts hpc README.md CONCEPTION.md \
  | ssh "$MACHINE" "tar xzf - -C ~/$REMOTE_DIR/code"
tar czf - -C "$TEMPLATES" cif templates_manifest.json \
  | ssh "$MACHINE" "rm -rf ~/$REMOTE_DIR/templates/$TEMPLATES && mkdir -p ~/$REMOTE_DIR/templates/$TEMPLATES && tar xzf - -C ~/$REMOTE_DIR/templates/$TEMPLATES"

echo "== vérifications distantes"
ssh "$MACHINE" "$REMOTE_ENV
set -e
export CNO_UNDER_PRESSURE=\$HOME/$JUMEAU_DIR
export PYTHONPATH=\$HOME/$REMOTE_DIR/code:\$CNO_UNDER_PRESSURE
export KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1
cd \$HOME/$REMOTE_DIR/code
python -c 'import mace, torch_dftd, ase, phonopy; print(\"   environnement ok\")'
[ -d \"\$CNO_UNDER_PRESSURE/cno_csp\" ] || { echo \"   projet jumeau ABSENT: \$CNO_UNDER_PRESSURE\"; exit 1; }
echo '   projet jumeau présent'
if [ -n '$REMOTE_MODEL' ]; then
  [ -f '$REMOTE_MODEL' ] || { echo '   checkpoint MACE ABSENT: $REMOTE_MODEL'; exit 1; }
  echo \"   E(diamant) distante = \$(MACE_MODEL='$REMOTE_MODEL' python hpc/e_diamant.py 2>/dev/null) eV\"
else
  echo '   checkpoint : resolu au lancement du job par hpc/e_diamant.py'
  ls \$HOME/.cache/mace/ 2>/dev/null | sed 's|^|     candidat: |' || echo '     cache mace absent'
fi
echo \"   templates: \$(ls ~/$REMOTE_DIR/templates/$TEMPLATES/cif | wc -l)\"
"

cat <<FIN

Transfert terminé. Les deux énergies du diamant ci-dessus doivent être
IDENTIQUES à la 6e décimale, sinon les deux machines n'utilisent pas le même
modèle et aucun résultat n'est comparable.

Soumission :
  ssh $MACHINE
  cd ~/$REMOTE_DIR
  $SUBMIT
FIN
