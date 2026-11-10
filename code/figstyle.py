"""House style for the static figures: light paper, Fraunces titles, Source Serif and IBM Plex Mono text, a blue sequence for
the distance to the nearest visible sea and warm sand for land with no sea view."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
from common import *

_FD = os.path.join(SCR, "fonts")
os.makedirs(_FD, exist_ok=True)
if not os.path.exists(f"{_FD}/Fraunces-Black.ttf"):
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    for w, nm in ((900, "Black"), (700, "Bold")):
        instancer.instantiateVariableFont(TTFont(f"{FONTS}/FrauncesVar.ttf"), {"wght": w, "opsz": 144, "SOFT": 0, "WONK": 0}).save(f"{_FD}/Fraunces-{nm}.ttf")
DISP = fm.FontProperties(fname=f"{_FD}/Fraunces-Black.ttf")
DISPB = fm.FontProperties(fname=f"{_FD}/Fraunces-Bold.ttf")
SERP = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Regular.ttf")
SERI = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-It.ttf")
for f in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
    fm.fontManager.addfont(f"{FONTS}/{f}")
MONO = "IBM Plex Mono"
plt.rcParams.update({"font.family": MONO, "font.size": 11, "axes.edgecolor": "#636A72", "axes.labelcolor": "#1D2128",
                     "xtick.color": "#636A72", "ytick.color": "#636A72", "axes.unicode_minus": False, "pdf.fonttype": 42})
PAPER, FG, MUT, RULE = "#F6F4EF", "#1D2128", "#636A72", "#DDD8CC"
SEA, SAND, EDGE = "#E4ECF0", "#E6DCC8", "#B9AE98"
HOT = "#B3202A"
# nearest visible sea: 0-2, 2-5, 5-10, 10-20, 20-35, 35-50 km
DBINS = [0, 2, 5, 10, 20, 35, 50]
DCOL = ["#08306B", "#1B5A9C", "#3A84C0", "#6FA9D6", "#A6CBE6", "#D2E4F1"]
DLAB = ["under 2 km", "2 to 5 km", "5 to 10 km", "10 to 20 km", "20 to 35 km", "35 to 50 km"]
NOVIEW = SAND
YES = "#2D6FAE"
BANDCOL = {"0 to 50": "#D08A1E", "50 to 150": "#3B8B5A", "150 to 300": "#2F7FB8", "300+": "#7A4FA0"}


def dist_class(near_km):
    """0..5 for the six distance classes, 6 = no sea view, -1 = not a square"""
    out = np.full(near_km.shape, 6, np.int8)
    for i in range(6):
        out[(near_km >= DBINS[i]) & (near_km < DBINS[i + 1] + (1e-6 if i == 5 else 0))] = i
    return out


def class_cmap():
    return ListedColormap(DCOL + [NOVIEW]), BoundaryNorm(np.arange(-0.5, 7.5, 1), 7)


def style_axes(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=RULE, lw=0.6)
    ax.set_axisbelow(True)


def savefig(fig, stem, blog=None, img=None, pdf=True):
    """f_<stem>.pdf for the paper, release/blog/b_<blog>.png at 1800 px wide, img/<img>.jpg for the page"""
    os.makedirs(f"{REL}/paper", exist_ok=True); os.makedirs(f"{REL}/blog", exist_ok=True)
    if pdf:
        fig.savefig(f"{REL}/paper/f_{stem}.pdf", facecolor=fig.get_facecolor())
    w = fig.get_figwidth()
    if blog:
        fig.savefig(f"{REL}/blog/b_{blog}.png", dpi=1800 / w, facecolor=fig.get_facecolor())
    if img:
        tmp = f"{SCR}/_tmp.png"
        fig.savefig(tmp, dpi=1400 / w, facecolor=fig.get_facecolor())
        from PIL import Image
        Image.open(tmp).convert("RGB").save(f"{IMG}/{img}.jpg", quality=86, optimize=True)
        os.remove(tmp)
    plt.close(fig)
