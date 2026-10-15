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

**La conception complète est dans [`CONCEPTION.md`](CONCEPTION.md)** : pourquoi
la coordinence détermine l'élément, pourquoi la règle de Lewis se réduit à un
couplage parfait, pourquoi la décoration canonique (`z=4→C, 3→N, 2→O`) est
toujours valide, comment la composition est contrainte par la topologie des
lacunes, et comment optimiser (x, y, z).

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
# 1. engendrer les templates (lacunes + décorations)
python scripts/gen_templates.py --mailles 1x1x1 2x1x1 2x2x1 --kmax 3 \
    --motifs canonique --out templates_dia

# 2. relaxer au MACE (volume + forme + positions), valider, calculer E_f
python scripts/relax_lot.py templates_dia --out runs/lot1.json
```

Environnement : `conda run -n mlip python ...`, ou directement
`~/miniconda3/envs/mlip/bin/python -u` (mace 0.3.12, ase 3.29.0, phonopy 4.7.2,
torch 2.2.2, torch-dftd). `conda run` tamponne la sortie : pour suivre un lot
en direct, utiliser l'interpréteur directement.

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
