#!/bin/bash
# Relaxation d'un lot de templates lacunaires sur YARGLA.
#
#   cd ~/diamant_to_CNO && sbatch --export=ALL,TEMPLATES=templates/cif_lot1,N_SHARDS=20 \
#          code/hpc/yargla_lot.slurm
#
# Parallélisation PAR PROCESSUS et non par threads : MACE en float64 sur CPU
# ne sature pas les cœurs (mesuré par le projet jumeau, un seul cœur
# réellement occupé par processus). On lance donc N_SHARDS processus d'un
# thread chacun, chaque shard prenant les templates entrelacés k, k+N, k+2N...
# pour recevoir un mélange de petites et de grandes mailles.
#
# Reprise : relax_lot.py réécrit son JSON après CHAQUE structure. Un lot
# interrompu est inspectable, et la relance ne perd que la structure en cours.
#SBATCH --job-name=dia_cno
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks=40
#SBATCH --exclusive
#SBATCH --time=24:00:00
#SBATCH --output=logs/dia_cno-%j.out

set -u
cd "${SLURM_SUBMIT_DIR:-$PWD}" || exit 1
mkdir -p logs runs cache

# Environnement : hp_mlip_mace et NON hp_mlip. Les deux portent mace 0.3.16,
# mais hp_mlip a e3nn 0.6.0, qui ne sait pas désérialiser un checkpoint
# MACE-MP écrit avec e3nn 0.4.4 (constaté par le jumeau, job 63858).
export PATH=/home/gilles/dynstab_project/miniforge3/envs/hp_mlip_mace/bin:$PATH
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE      # conflit OpenMP conda/pip

# Ce projet IMPORTE l'outillage du jumeau (cno_csp.relax, cno_csp.validator,
# scripts/funnel_table.py). Il doit donc être déployé sur la machine, et
# dia_cno.jumeau() le localise par cette variable.
export CNO_UNDER_PRESSURE=${CNO_UNDER_PRESSURE:-$HOME/C_N_O_under_Pressure/code}
export PYTHONPATH="$PWD/code:${PYTHONPATH:-}"
[ -d "$CNO_UNDER_PRESSURE/cno_csp" ] || {
    echo "projet jumeau absent : $CNO_UNDER_PRESSURE"
    echo "déployer C_N_O_under_pressure d'abord (hpc/stage.sh de ce projet-là)"
    exit 1; }

# Checkpoint LOCAL : les nœuds de calcul n'ont pas Internet, mace_mp()
# tenterait un téléchargement et échouerait APRÈS la file d'attente.
# 5yyxdm76 et NON macempa0mediummodel : deux checkpoints cohabitent dans
# ~/.cache/mace et ce ne sont pas le même modèle (13 meV d'écart sur le
# diamant). Celui-ci est bien celui du Mac, vérifié par l'énergie du diamant
# à 2 atomes : -18.149009 eV sur les deux machines.
export MACE_MODEL=${MACE_MODEL:-/home/gilles/.cache/mace/5yyxdm76}
[ -f "$MACE_MODEL" ] || { echo "checkpoint MACE introuvable: $MACE_MODEL"; exit 1; }

N_SHARDS=${N_SHARDS:-20}
TEMPLATES=${TEMPLATES:-templates/lot1}
OUT=${OUT:-runs/lot1.json}
FMAX=${FMAX:-1e-3}

echo "début $(date) | nœud $(hostname) | $N_SHARDS shards | templates $TEMPLATES"
python -c "import mace, torch_dftd, ase, phonopy; print('environnement ok')" || exit 1
python - <<'PY' || exit 1
from ase.build import bulk
from cno_csp.relax import get_calculator
a = bulk("C", "diamond", a=3.567); a.calc = get_calculator("mace")
e = a.get_potential_energy()
print("E(diamant, 2 at) = %.6f eV" % e)
assert abs(e + 18.149009) < 1e-5, "checkpoint MACE différent de celui du Mac"
PY

# Les références (graphite, diamant, N2, O2, CO2, N2O) une seule fois AVANT
# les shards : elles sont mises en cache sur disque, et deux shards qui les
# calculeraient en parallèle écriraient le même fichier en même temps.
python code/scripts/relax_lot.py "$TEMPLATES" --out "$OUT" --limite 1 \
    --fmax "$FMAX" > logs/refs.log 2>&1 || { cat logs/refs.log; exit 1; }
echo "références en cache : $(ls cache/)"

for k in $(seq 0 $((N_SHARDS - 1))); do
    srun --exclusive --ntasks=1 --cpus-per-task=1 \
         python code/scripts/relax_lot.py "$TEMPLATES" \
                --out "$OUT" --fmax "$FMAX" --shard "$k/$N_SHARDS" \
         > "logs/shard_$k.log" 2>&1 &
done
wait
echo "fin $(date)"
