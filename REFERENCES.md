# Choisir les références : de l'enthalpie de formation à la métastabilité

Le diagnostic est juste et c'est le point faible de toute la chaîne. N2 et O2
sont les deux pires cas possibles :

- **N2** a une triple liaison (dissociation expérimentale 9.79 eV). PBE la
  surlie de plusieurs dixièmes d'eV ; MACE-MP, entraîné sur des solides
  périodiques, ne voit pour ainsi dire jamais ce motif.
- **O2** a un fondamental **triplet** : il demande une polarisation de spin, et
  l'erreur de self-interaction de PBE le surlie d'environ 1 eV.
- Les deux sont des **gaz**. Même avec une énergie électronique exacte, une
  comparaison d'énergies internes ignore le `−TΔS` du dégagement gazeux,
  plusieurs dixièmes d'eV par molécule à 298 K.

Ces erreurs entrent **linéairement** dans E_f, pondérées par les fractions
atomiques. D'où la question : peut-on y substituer des cristaux à liaisons
simples ? Réponse mesurée ci-dessous — et elle est plus intéressante que
prévu, parce qu'elle déplace le problème.

## 1. Deux choses qu'un changement de référence ne peut pas faire

**(a) Il ne change aucun verdict de métastabilité.** Décaler les potentiels
chimiques de constantes `δ_C, δ_N, δ_O` décale E_f d'une fonction **affine de
la composition**. L'enveloppe convexe se décale de la même fonction affine,
donc la **distance au-dessus de l'enveloppe est invariante**. Ce qui change le
verdict, c'est *quelles phases concurrencent*, pas comment on fixe le zéro.

**(b) Un composé n'est pas un substitut d'élément.** C'est le piège, et j'y
suis tombé en rédigeant la première version de ce document. Écrire
`μ_N = [E(Si3N4) − 3μ_Si]/4` ne donne pas un « meilleur μ_N » : cela donne le
potentiel chimique de l'azote **en équilibre avec Si3N4 + Si**, une condition
thermodynamique entièrement différente. Mesuré ici : −10.32 eV contre −8.11 eV
pour N2, soit 2.2 eV d'écart — qui n'est pas une erreur, mais exactement
l'enthalpie de formation de Si3N4 rapportée à l'azote. S'en servir comme
référence rendrait toutes nos E_f massivement positives, et répondrait à la
question « mes structures sont-elles stables face à Si3N4 ? », qui n'a pas de
sens en l'absence de silicium.

Un cristal de référence sert donc à **calibrer** l'erreur, pas à remplacer
l'élément.

## 2. La calibration, mesurée

`scripts/calibre_refs.py` : six composés cristallins d'enthalpie de formation
expérimentale connue, relaxés au même niveau que la campagne, et l'écart
attribué à l'élément léger. `δ implicite` = écart ramené à la fraction de N ou
de O, c'est-à-dire la correction qu'il faudrait porter sur μ_N ou μ_O pour que
ce composé-là tombe juste.

**MACE seul** (le niveau du pool 3D, donc de nos meilleurs candidats) :

| composé | motif de l'élément léger | H_f MACE | H_f exp. | écart | δ implicite |
|---|---|---|---|---|---|
| Si3N4 | N lié à 3 tétraèdres | −1.261 | −1.103 | −0.158 | **−0.276** |
| AlN | N tétracoordiné | −1.518 | −1.648 | +0.129 | **+0.259** |
| BN (h) | N trigonal plan | −1.420 | −1.318 | −0.102 | **−0.204** |
| SiO2 (quartz) | **O pontant coudé** | −2.891 | −3.146 | +0.256 | **+0.383** |
| Al2O3 | O ionique | −3.075 | −3.473 | +0.399 | **+0.665** |
| MgO | O ionique | −2.749 | −3.118 | +0.369 | **+0.738** |

(eV/atome. Avec D3 : δ_N de −0.477 à +0.070, δ_O de +0.339 à +0.509.)

**Trois conclusions, dont une inattendue.**

**L'oxygène est calibrable.** Les trois oxydes s'accordent en signe et en
ordre de grandeur : **δ_O ≈ +0.4 à +0.7 eV par atome d'oxygène**. μ_O tiré de
O2 est trop bas, donc MACE surlie O2 — exactement l'erreur attendue. Et la
référence **chimiquement appariée** donne la plus petite correction : SiO2,
dont l'oxygène pontant coudé Si–O–Si *est* le motif O_bent du cahier des
charges, donne +0.383 contre +0.665 et +0.738 pour les oxydes ioniques. C'est
la confirmation quantitative de l'argument « même environnement local, erreur
qui se compense ».

**L'azote n'est pas calibrable avec ce jeu.** Les trois nitrures donnent des
corrections de **signes opposés** (−0.28, +0.26, −0.20). L'erreur n'est donc
pas dominée par μ_N : les références métalliques (Si, Al, B élémentaires)
portent des erreurs du même ordre, et B élémentaire est un mauvais standard
(le β-bore est structuralement complexe). On ne peut pas attribuer l'écart à
l'azote. **C'est à reporter comme une limite, pas à masquer par un ajustement
aux moindres carrés** qui donnerait un chiffre unique sans signification.

**Et l'erreur dominante n'est ni l'azote ni l'oxygène : c'est le carbone.**
MACE donne diamant − graphite = **+0.138 eV/atome** sans dispersion, **+0.096**
avec, contre **+0.0196** expérimental. Soit 0.08–0.12 eV/atome d'erreur sur
μ_C — parce que le graphite sans dispersion relaxe à 10.30 Å³/atome contre
8.80 mesuré. Or nos charpentes sont **riches en carbone** : C52N8O, notre
meilleur candidat, a x_C = 0.85. Cette erreur-là pèse donc **0.08 × 0.85 ≈
0.07 eV/atome** sur son E_f, contre 0.5 × 0.016 ≈ 0.008 pour l'oxygène. Le
terme qu'on ne surveillait pas est le plus gros.

## 3. Ce que je propose

**(1) μ_C = diamant, et non graphite.** Pour ce projet c'est le choix évident
et je le recommande sans réserve : nos carbones sont tétraédriques, le diamant
*est* le site C_tet, et nos structures sont littéralement du diamant lacunaire.
L'erreur de description du carbone sp³ se compense alors presque exactement.
Avec graphite on paie en plus une erreur de dispersion qui n'a rien à voir
avec nos structures. Conséquence à assumer : E_f devient « par rapport au
diamant », donc décalée de ~+0.02 eV/atome par rapport à la convention
standard — négligeable devant l'erreur qu'on supprime.

**(2) μ_O calibré par SiO2**, la référence chimiquement appariée :
`μ_O ← μ_O(O2) + 0.383` sans D3, `+0.339` avec. Avec une barre d'erreur de
±0.18, l'écart entre SiO2 et les oxydes ioniques.

**(3) μ_N : pas de correction, mais une barre d'erreur de ±0.26 eV/atome
d'azote**, mesurée comme la dispersion des trois nitrures. Pour descendre il
faudrait des nitrures dont le partenaire soit mieux décrit — Mg3N2, Ca3N2,
Li3N (liaisons simples, métaux simples bien décrits) — ou une référence N–N
simple liaison condensée, mais aucune n'est stable à l'ambiante.

**(4) Reporter trois niveaux**, et non une seule colonne :

- **Niveau 1 — classement à composition égale.** Aucune référence
  n'intervient. C'est la seule affirmation qu'aucun choix de référence ne peut
  invalider, et elle dit déjà quel polymorphe gagne.
- **Niveau 2 — enveloppe des phases condensées seules** : diamant, graphite,
  CO2 solide, et les C-N-O cristallins connus. Aucun gaz, donc fiable. Réserve
  honnête : le ternaire C-N-O n'a presque aucun composé cristallin stable
  connu à l'ambiante — ce qui est en soi un résultat, et explique pourquoi les
  gaz dominent l'enveloppe.
- **Niveau 3 — décomposition réelle, calibrée et sous pression** :

      ΔG_dec(P,T) = ΔE_calculé + δ_calibration + P·ΔV − T·ΔS_gaz

  Le terme `P·ΔV` est **décisif ici** : une mole de N2 occupe ~24 L à
  l'ambiante contre ~5 cm³ dans nos charpentes. Un candidat à +0.24 eV/atome
  au-dessus des gaz à 0 GPa peut passer sous l'enveloppe à quelques dizaines
  de GPa par ce seul terme. C'est l'axe du projet jumeau, et la raison pour
  laquelle **la pression doit être exposée** (cf. PARAMETRES.md).

## 4. Pourquoi pas C3N4, malgré le bon réflexe

L'idée est juste — c'est bien le motif visé — mais ce composé-là ne convient
pas comme référence :

1. **Aucun C3N4 cristallin n'a d'enthalpie de formation expérimentale
   fiable.** Les nitrures de carbone sont notoirement difficiles à
   synthétiser ; le produit usuel est le « melon » polymérique, hydrogéné et
   mal cristallisé. Une référence sans valeur expérimentale ne calibre rien.
2. **C3N4 pseudocubique est un membre de notre propre famille** : c'est la
   lacune isolée du diamant (§14 de CONCEPTION.md), le témoin de validation de
   la méthode. S'en servir comme référence serait circulaire.

Si3N4 est le même motif avec Si à la place de C, expérimentalement
caractérisé, extérieur à la famille — et c'est pourquoi il figure dans le jeu
de calibration. Il y joue le rôle qui lui revient : **mesurer l'erreur**, pas
définir le zéro.

## 5. Réserve sur les valeurs expérimentales

Les six enthalpies de `scripts/calibre_refs.py` (Si3N4 −744.8, SiO2 −910.7,
AlN −318.0, Al2O3 −1675.7, MgO −601.6, BN −254.4 kJ/mol) sont des valeurs
CODATA/NIST standard, **à recontrôler sur table avant publication**. Une
erreur de facteur sur le nombre de formules par maille a déjà été commise une
fois dans ce calcul, et elle changeait toutes les conclusions.
