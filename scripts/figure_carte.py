#!/usr/bin/env python3
"""
Figure : où, dans le simplexe C-N-O, la famille lacunaire est-elle favorable ?

    python scripts/figure_carte.py runs/vm1_lot2/carte.json --out rapport/carte_cno

Diagramme ternaire des compositions atteintes, colorées par le MEILLEUR
ΔE_dec de chaque composition, avec les lignes d'iso-ΔE_dec du plan ajusté.
Ces lignes sont droites sur un ternaire : le paysage est, au premier ordre,
un plan, et sa direction de plus grande pente EST la réponse à la question
« quelle région ».

Choix graphiques, et leurs raisons :
  - rampe MONOCHROME clair -> foncé (magnitude), jamais un arc-en-ciel :
    l'ordre des valeurs doit se lire sans légende, et la figure doit survivre
    à une impression en niveaux de gris ;
  - foncé = ΔE_dec élevé = loin de la stabilité, convention habituelle
    (plus sombre = plus grand) ;
  - taille des points = nombre de polymorphes de la composition, c'est-à-dire
    la densité d'échantillonnage, qui n'est pas uniforme ;
  - cercle noir = composition sur l'enveloppe convexe INTERNE (stable vis-à-vis
    de la dismutation dans la famille, indépendamment de tout potentiel
    chimique) ;
  - axes et grille récessifs, étiquettes directes sur les seules compositions
    remarquables.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

S3 = np.sqrt(3.0) / 2.0


def ternaire(xc, xn, xo):
    """Coordonnées cartésiennes d'un point du simplexe. C en bas à gauche,
    N en bas à droite, O au sommet."""
    return xn + 0.5 * xo, S3 * xo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("carte", help="JSON produit par carte_stabilite.py")
    ap.add_argument("--out", default="rapport/carte_cno")
    ap.add_argument("--titre", default="")
    args = ap.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    d = json.loads(Path(args.carte).read_text())
    xc = np.array([l["x_C"] for l in d])
    xn = np.array([l["x_N"] for l in d])
    xo = np.array([l["x_O"] for l in d])
    dec = np.array([l["e_dec"] for l in d])
    npoly = np.array([l["n_polymorphes"] for l in d])
    sur_hull = np.array([l["d_hull"] < 1e-6 for l in d])

    # plan ajusté : dec = a*x_N + b*x_O + c
    A = np.column_stack([xn, xo, np.ones_like(xn)])
    (a, b, c), *_ = np.linalg.lstsq(A, dec, rcond=None)
    pred = A @ np.array([a, b, c])
    r2 = 1 - ((dec - pred) ** 2).sum() / ((dec - dec.mean()) ** 2).sum()

    fig, ax = plt.subplots(figsize=(7.0, 7.0))
    ax.set_aspect("equal")
    ax.axis("off")

    # ---- cadre du ternaire, récessif
    coins = np.array([ternaire(1, 0, 0), ternaire(0, 1, 0), ternaire(0, 0, 1)])
    ax.add_patch(plt.Polygon(coins, closed=True, fill=False,
                             edgecolor="#9aa0a6", linewidth=1.0, zorder=1))
    for f in (0.2, 0.4, 0.6, 0.8):     # grille à 20 %
        for p, q in (((1 - f, f, 0), (1 - f, 0, f)),
                     ((f, 1 - f, 0), (0, 1 - f, f)),
                     ((f, 0, 1 - f), (0, f, 1 - f))):
            (x1, y1), (x2, y2) = ternaire(*p), ternaire(*q)
            ax.plot([x1, x2], [y1, y2], color="#e3e5e8", lw=0.6, zorder=0)

    # ---- lignes d'iso-ΔE_dec du plan ajusté (droites sur un ternaire)
    niveaux = np.arange(0.2, 1.01, 0.2)
    gx, gy = np.meshgrid(np.linspace(0, 1, 400), np.linspace(0, S3, 400))
    # inverse de la projection : x_O = gy/S3, x_N = gx - gy/(2*S3)
    XO = gy / S3
    XN = gx - gy / (2 * S3)
    XC = 1 - XN - XO
    Z = a * XN + b * XO + c
    Z = np.where((XN >= -1e-9) & (XO >= -1e-9) & (XC >= -1e-9), Z, np.nan)
    cs = ax.contour(gx, gy, Z, levels=niveaux, colors="#b0b4b9",
                    linewidths=0.8, linestyles="--", zorder=1)
    ax.clabel(cs, fmt=lambda v: f"{v:.1f}", fontsize=7, colors="#80868b")

    # ---- points : rampe monochrome, foncé = ΔE_dec élevé
    px, py = ternaire(xc, xn, xo)
    sc = ax.scatter(px, py, c=dec, cmap="Blues", s=18 + 10 * np.sqrt(npoly),
                    vmin=0.1, vmax=1.0, linewidths=0.6, edgecolors="#ffffff",
                    zorder=3)
    ax.scatter(px[sur_hull], py[sur_hull], s=(18 + 10 * np.sqrt(npoly[sur_hull])) * 2.4,
               facecolors="none", edgecolors="#202124", linewidths=1.0, zorder=4)

    # ---- étiquettes directes sur les trois meilleures seulement, décalages
    # alternés : sans cela les deux meilleures du coin carboné se superposent.
    decalages = [(14, 16), (16, -20), (-66, 14)]
    for rang, i in enumerate(np.argsort(dec)[:3]):
        cc = d[i]["comp"]
        ax.annotate(f"C$_{{{cc[0]}}}$N$_{{{cc[1]}}}$O$_{{{cc[2]}}}$  {dec[i]:+.2f}",
                    (px[i], py[i]), textcoords="offset points",
                    xytext=decalages[rang % 3],
                    fontsize=7.5, color="#202124",
                    arrowprops=dict(arrowstyle="-", color="#9aa0a6", lw=0.6))

    for (x, y), lab, dx, dy in (
            (coins[0], "C", -0.03, -0.045), (coins[1], "N", 0.02, -0.045),
            (coins[2], "O", 0.0, 0.025)):
        ax.text(x + dx, y + dy, lab, fontsize=12, color="#202124", ha="center")

    cb = fig.colorbar(sc, ax=ax, shrink=0.62, pad=0.02)
    cb.set_label(r"meilleur $\Delta E_{\mathrm{dec}}$ (eV/atome)", fontsize=9)
    cb.ax.tick_params(labelsize=8)
    cb.outline.set_visible(False)

    # Légende SOUS le triangle : en haut à droite elle recouvrait le sommet O.
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="", mfc="none", mec="#202124",
               ms=9, label="sur l'enveloppe convexe interne"),
        Line2D([], [], ls="--", color="#b0b4b9",
               label=f"plan ajusté : {a:+.2f}·$x_N$ {b:+.2f}·$x_O$ {c:+.2f}"
                     f"  ($R^2$={r2:.2f})")],
        loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False,
        fontsize=8, ncol=1)
    # marge haute pour que le titre ne morde pas sur le sommet O
    ax.set_ylim(-0.12, S3 + 0.14)
    ax.set_xlim(-0.08, 1.08)

    titre = args.titre or ("Stabilité dans le simplexe C-N-O : "
                           f"{len(d)} compositions, famille lacunaire du diamant")
    ax.set_title(titre, fontsize=10.5, color="#202124", pad=18)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out.with_suffix(f".{ext}"), dpi=200, bbox_inches="tight")
    print(f"plan ajusté : ΔE_dec = {a:+.3f}·x_N {b:+.3f}·x_O {c:+.3f}  (R² = {r2:.2f})")
    print(f"-> {out.with_suffix('.pdf')} et {out.with_suffix('.png')}")


if __name__ == "__main__":
    main()
