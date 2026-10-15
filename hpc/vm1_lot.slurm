#!/bin/bash
# Relaxation d'un lot de templates lacunaires sur VM1 (GPU H100 NVL).
#
#   cd ~/diamant_to_CNO && sbatch --export=ALL,TEMPLATES=templates/templates_dia_t1,N_SHARDS=8 \
#          code/hpc/vm1_lot.slurm
#
# POURQUOI LE GPU ICI. Les bancs du projet jumeau (runs_random/bench_calls/)
# mesurent le coût d'un appel énergie+forces MACE-MP float64, sans D3 :
#
#   atomes   Yargla 1 coeur   Yargla 8 coeurs   H100 vm1   gain / 1 coeur
#     20        1391 ms           362 ms          62 ms         x23
#     44        3407 ms           846 ms          37 ms         x93
#    352       28474 ms          6827 ms          89 ms        x318
#
# Le gain CROÎT avec la taille : en dessous de ~50 atomes le GPU est
# sous-occupé. C'est exactement le régime de ce projet -- les templates sans
# interaction d'images font 61-62 atomes. En débit total, un H100 partagé
# entre 16 processus débite 35.8 appels/s sur 44 atomes avec D3, l'équivalent
# de ~150 coeurs Yargla, soit presque quatre noeuds.
#
# N_SHARDS = 8 et non 16 : le débit sature déjà à 8 processus (33.5 appels/s
# contre 35.8 à 16) alors que la latence par appel double (233 ms contre 445).
# Huit processus donnent 94 % du débit avec deux fois moins d'attente par
# structure.
#
# ATTENTION, D3 SUR GPU. La dispersion coûte beaucoup plus cher en relatif sur
# GPU que sur CPU (352 atomes : 89 ms sans D3, 417 ms avec). Le pool 3D, qui
# se relaxe sans D3, est donc le meilleur cas du GPU ; les pools 0D/1D/2D y
# gagnent moins.
#SBATCH --job-name=dia_cno_gpu
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --output=logs/dia_cno_gpu-%j.out

set -u
cd "${SLURM_SUBMIT_DIR:-$PWD}" || exit 1
mkdir -p logs runs cache

# Environnement GPU de vm1 (cf. README du jumeau : E(diamant) y est identique
# au microélectronvolt près, donc les résultats sont comparables au Mac).
export PATH=${MACE_GPU_ENV:-$HOME/miniforge3/envs/mace_gpu}/bin:$PATH
export CNO_DEVICE=cuda           # lu par cno_csp.relax.get_calculator
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export KMP_DUPLICATE_LIB_OK=TRUE

export CNO_UNDER_PRESSURE=${CNO_UNDER_PRESSURE:-$HOME/C_N_O_under_Pressure/code}
export PYTHONPATH="$PWD/code:${PYTHONPATH:-}"
[ -d "$CNO_UNDER_PRESSURE/cno_csp" ] || {
    echo "projet jumeau absent : $CNO_UNDER_PRESSURE"; exit 1; }

# RÉSOLUTION DU CHECKPOINT. Sur Yargla deux checkpoints cohabitent dans
# ~/.cache/mace et ce ne sont pas le même modèle (13 meV d'écart sur le
# diamant, aucune erreur levée, résultats silencieusement incomparables). On
# ne devine donc pas le nom : on essaie les candidats et on garde celui qui
# reproduit l'énergie du Mac. Un noeud de calcul n'ayant pas forcément
# Internet, mace_mp() ne doit jamais avoir à télécharger.
if [ -z "${MACE_MODEL:-}" ]; then
    echo "== résolution du checkpoint MACE par l'énergie du diamant"
    for cand in "$HOME"/.cache/mace/*; do
        [ -f "$cand" ] || continue
        e=$(MACE_MODEL="$cand" python code/hpc/e_diamant.py 2>/dev/null)
        echo "   $(basename "$cand") : ${e:-echec}"
        if [ "$e" = "-18.149009" ]; then export MACE_MODEL="$cand"; fi
    done
fi
[ -n "${MACE_MODEL:-}" ] || { echo "aucun checkpoint ne donne -18.149009 eV"; exit 1; }
echo "checkpoint retenu : $MACE_MODEL"

N_SHARDS=${N_SHARDS:-8}
TEMPLATES=${TEMPLATES:-templates/templates_dia_t1}
OUT=${OUT:-runs/lot1_gpu.json}
FMAX=${FMAX:-1e-3}

echo "début $(date) | $(hostname) | $N_SHARDS processus sur 1 GPU | $TEMPLATES"
python -c "import torch; print('cuda :', torch.cuda.is_available(), torch.cuda.get_device_name(0))" || exit 1

# Références (graphite, diamant, N2, O2, CO2, N2O) une seule fois AVANT les
# shards : mises en cache sur disque, deux shards les écriraient en concurrence.
python code/scripts/relax_lot.py "$TEMPLATES" --out "$OUT" --limite 1 \
    --fmax "$FMAX" > logs/refs_gpu.log 2>&1 || { cat logs/refs_gpu.log; exit 1; }

for k in $(seq 0 $((N_SHARDS - 1))); do
    python code/scripts/relax_lot.py "$TEMPLATES" \
           --out "$OUT" --fmax "$FMAX" --shard "$k/$N_SHARDS" \
       > "logs/shard_gpu_$k.log" 2>&1 &
done
wait
echo "fin $(date)"
