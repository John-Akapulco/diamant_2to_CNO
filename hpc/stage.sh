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

case "$MACHINE" in
  yargla) REMOTE_ENV="export PATH=/home/gilles/dynstab_project/miniforge3/envs/hp_mlip_mace/bin:\$PATH"
          REMOTE_MODEL=${REMOTE_MODEL:-/home/gilles/.cache/mace/5yyxdm76} ;;
  *)      echo "machine non configurée: $MACHINE"; exit 1 ;;
esac

echo "== référence locale : énergie du diamant"
E_LOCAL=$(CNO_UNDER_PRESSURE=${CNO_UNDER_PRESSURE:-$HOME/C_N_O_under_pressure} \
  python3 - <<'PY'
import sys; sys.path.insert(0, ".")
from dia_cno import jumeau; jumeau()
from ase.build import bulk
from cno_csp.relax import get_calculator
a = bulk("C", "diamond", a=3.567); a.calc = get_calculator("mace")
print("%.6f" % a.get_potential_energy())
PY
)
echo "   $E_LOCAL eV"

NB=$(ls "$TEMPLATES/cif" | wc -l | tr -d ' ')
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
python -c 'import mace, torch_dftd, ase, phonopy; print(\"   environnement ok\")'
[ -d \"\$CNO_UNDER_PRESSURE/cno_csp\" ] || { echo \"   projet jumeau ABSENT: \$CNO_UNDER_PRESSURE\"; exit 1; }
echo '   projet jumeau présent'
[ -f $REMOTE_MODEL ] || { echo '   checkpoint MACE ABSENT: $REMOTE_MODEL'; exit 1; }
MACE_MODEL=$REMOTE_MODEL python - <<'PY'
from ase.build import bulk
from cno_csp.relax import get_calculator
a = bulk('C','diamond',a=3.567); a.calc = get_calculator('mace')
print('   E(diamant) distante = %.6f eV' % a.get_potential_energy())
PY
echo \"   templates: \$(ls ~/$REMOTE_DIR/templates/$TEMPLATES/cif | wc -l)\"
"

cat <<FIN

Transfert terminé. Les deux énergies du diamant ci-dessus doivent être
IDENTIQUES à la 6e décimale, sinon les deux machines n'utilisent pas le même
modèle et aucun résultat n'est comparable.

Soumission :
  ssh $MACHINE
  cd ~/$REMOTE_DIR
  sbatch --export=ALL,TEMPLATES=templates/$TEMPLATES,N_SHARDS=20,OUT=runs/lot1.json \\
         code/hpc/yargla_lot.slurm
FIN
