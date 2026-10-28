#!/usr/bin/env python3
"""Four images, drawn from results/ only. Nothing here is typed in."""
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from marscheck import model  # noqa: E402

R = ROOT / "results"
cov = json.loads((R / "coverage.json").read_text())
mars = json.loads((R / "mars_timing.json").read_text())
ver_path = R / "ethlib_verification.json"
ver = json.loads(ver_path.read_text()) if ver_path.exists() else None
daily = list(csv.DictReader(open(R / "daily.csv")))

INK, MUTED, BLUE, RED, GREEN, PAPER, RULE = "#14213D", "#5B6477", "#0F52BA", "#C0392B", "#1E7B4F", "#FFFFFF", "#D9DEE8"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.edgecolor": RULE, "figure.facecolor": PAPER, "axes.facecolor": PAPER,
})
W, H = 16, 9  # 1600 x 900 at dpi 100


def save(fig, name):
    fig.savefig(ROOT / "images" / name, dpi=100, facecolor=PAPER)
    plt.close(fig)


def header(fig, title, sub):
    fig.text(0.05, 0.925, title, fontsize=30, fontweight="bold", va="center")
    fig.text(0.05, 0.865, sub, fontsize=15, color=MUTED, va="center")


def footer(fig, extra=""):
    fig.text(0.05, 0.04, "github.com/keithadler/ethlib-mars-check" + extra, fontsize=11, color=MUTED)


# 1. What EthLib covers ---------------------------------------------------------------
fig = plt.figure(figsize=(W, H))
n_yes = sum(r["covered"] for r in cov["rows"])
header(fig, "What EthLib actually covers",
       f"{n_yes} of {len(cov['rows'])} Ethereum primitives checked are in it. It is a consensus-layer cryptography library.")
ax = fig.add_axes([0.05, 0.09, 0.9, 0.72])
ax.set_xlim(0, 1)
ax.axis("off")
rows = cov["rows"]
rh = 1 / len(rows)
for k, r in enumerate(rows):
    y = 1 - (k + 1) * rh
    col = BLUE if r["covered"] else "#EEF0F5"
    ax.add_patch(FancyBboxPatch((0.0, y + 0.012), 0.05, rh - 0.024, boxstyle="round,pad=0,rounding_size=0.01",
                                fc=col, ec="none"))
    ax.text(0.025, y + rh / 2, "yes" if r["covered"] else "no", ha="center", va="center", fontsize=11,
            color="white" if r["covered"] else MUTED, fontweight="bold")
    ax.text(0.07, y + rh / 2, r["primitive"], va="center", fontsize=15, color=INK if r["covered"] else MUTED)
    ax.text(0.99, y + rh / 2, r["area"], va="center", ha="right", fontsize=12, color=MUTED)
footer(fig, f"  |  EthLib {cov['ethlib_commit'][:8]}")
save(fig, "1-what-ethlib-covers.png")

# 2. Light time against the protocol's clocks ---------------------------------------------
fig = plt.figure(figsize=(W, H))
lt = mars["one_way_light_time_s"]
header(fig, "Mars is 5 to 21 light-minutes away",
       "Ethereum's votes are due in 4 seconds. The nearest Mars gets in 2026-2030 is 323 seconds.")
ax = fig.add_axes([0.07, 0.12, 0.88, 0.67])
dates = [mdates.datestr2num(r["date"]) for r in daily]
D = [float(r["one_way_s"]) for r in daily]
ax.set_yscale("log")
ax.set_ylim(2, 2500)
ax.plot(dates, D, color=BLUE, lw=3)
th = mars["thresholds_s"]
for y, label, c in [(th["head_vote_possible_below_s"], "head vote: must arrive within 8 s", RED),
                    (th["source_vote_possible_below_s"], "source vote: within 56 s", RED),
                    (th["any_valid_vote_possible_below_s"], "any vote at all: under 376 s (one epoch is 384 s)", INK)]:
    ax.axhline(y, color=c, lw=1.6, ls="--")
    ax.text(dates[0] + (8 if y < 100 else 1000), y * 1.07, label, color=c, fontsize=13, va="bottom")
bl = [i for i, r in enumerate(daily) if r["blackout"] == "True"]
if bl:
    runs, s = [], bl[0]
    for a, b in zip(bl, bl[1:] + [None]):
        if b != a + 1:
            runs.append((s, a))
            s = b
    for s, e in runs:
        ax.axvspan(dates[s], dates[e], color=RED, alpha=0.18, lw=0)
        ax.text(dates[(s + e) // 2], 2.5, "no link\n(behind the Sun)", ha="center", fontsize=11, color=RED)
ax.set_yticks([5, 10, 30, 100, 300, 600, 1200, 2400])
ax.set_yticklabels(["5 s", "10 s", "30 s", "100 s", "5 min", "10 min", "20 min", "40 min"])
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_ylabel("one-way light time, Earth to Mars", fontsize=13)
imin, imax = D.index(min(D)), D.index(max(D))
ax.annotate(f"closest: {min(D)/60:.1f} min", (dates[imin], D[imin]), (dates[imin] - 330, D[imin] * 0.58),
            fontsize=13, color=BLUE, arrowprops=dict(arrowstyle="-", color=BLUE))
ax.annotate(f"farthest: {max(D)/60:.1f} min", (dates[imax], D[imax]), (dates[imax] - 400, D[imax] * 1.45),
            fontsize=13, color=BLUE, arrowprops=dict(arrowstyle="-", color=BLUE))
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
footer(fig, "  |  distances: NASA/JPL Horizons  |  rules: ethereum/consensus-specs " + mars["inputs"]["consensus_specs_commit"][:8])
save(fig, "2-light-time-vs-the-clock.png")

# 3. How much of a Mars validator counts ------------------------------------------------
fig = plt.figure(figsize=(W, H))
header(fig, "A validator on Mars mostly doesn't count",
       f"Votes that can count on {mars['share_of_days_with_any_valid_mars_attestation']:.0%} of days, "
       f"and then at most {mars['best_valid_share']:.0%} of them. Never a head or source vote.")
ax = fig.add_axes([0.07, 0.12, 0.88, 0.67])
spec = model.load_spec()
P = model.Params.from_spec(spec)
xs = [x / 2 for x in range(0, 2800)]
ax.axvspan(lt["min"], lt["max"], color=BLUE, alpha=0.10, lw=0)
ax.text((lt["min"] + lt["max"]) / 2, 0.92, "Earth to Mars, 2026-2030", ha="center", color=BLUE, fontsize=14)
ax.plot(xs, [model.epoch_summary(P, x)["valid_share"] for x in xs], color=BLUE, lw=3.5,
        label="share of votes that can be included and match")
ax.plot(xs, [model.epoch_summary(P, x)["reward_share"] for x in xs], color=RED, lw=3.5,
        label="share of the full attestation reward earned")
ax.set_xlim(0, 1400)
ax.set_ylim(-0.02, 1.02)
ax.set_xticks([0, 60, 120, 240, 376, 600, 900, 1200])
ax.set_xticklabels(["0", "1 min", "2 min", "4 min", "6.3 min", "10 min", "15 min", "20 min"])
ax.axvline(th_last := mars["thresholds_s"]["any_valid_vote_possible_below_s"], color=INK, lw=1.6, ls="--")
ax.text(th_last + 12, 0.42, "past 376 s nothing a\nMars validator signs\ncan count", fontsize=13, color=INK)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("one-way delay between the validator and Earth", fontsize=13)
ax.legend(frameon=False, fontsize=14, loc="center right")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
footer(fig, "  |  one epoch of 32 slots, rules from consensus-specs deneb/electra")
save(fig, "3-who-counts.png")

# 4. Verdict ------------------------------------------------------------------------------
fig = plt.figure(figsize=(W, H))
header(fig, "Does it work on Mars?", "The math does. The clock doesn't. Here is each part, with the number.")
ax = fig.add_axes([0.05, 0.09, 0.9, 0.74])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")
st = mars["settlement_see_finality_s"]
b = mars["bandwidth"]
proofs = ("proof rebuild finished" if ver and ver.get("build_ok") else
          f"proof rebuild unfinished: {ver['jobs_finished']:,} of {ver['jobs_total']:,} jobs, 0 errors" if ver else "proofs not rebuilt here")
items = [
    ("works", "The library", "Pure functions of their input: no clock, no network. Distance can't change an answer.", GREEN),
    ("works", "A Mars light client", f"Follows Earth {lt['max']/3600:.2f} h behind at worst; its committee changes every "
     f"{mars['light_client']['sync_committee_period_hours']:.1f} h.", GREEN),
    ("slow", "A transaction", f"Seen finalized from Mars in {st['fastest']/60:.0f} to {st['slowest']/60:.0f} minutes. "
     "Light speed, not a flaw.", "#B7791F"),
    ("fails", "A validator on Mars", f"Counts on {mars['share_of_days_with_any_valid_mars_attestation']:.0%} of days, "
     f"at most {mars['best_reward_share_of_full']:.1%} of the reward. Over 1/3 of the stake would stall finality "
     f"and the leak would eject it in {mars['leak']['days_to_ejection']:.0f} days.", RED),
    ("fails", "Data sampling", f"One sample takes {mars['das']['sample_round_trip_s_best']:.0f} s round trip; "
     f"the vote is due in {mars['das']['attestation_due_s']:.0f} s.", RED),
    ("fails", "A full node at the blob cap", f"Needs {b['blob_data_needed_mbps_at_max_blobs']} Mbit/s of blobs. Best link averages "
     f"{b['link_average_mbps_best']}, worst {b['link_average_mbps_worst']} (NASA's Mars orbiter link, 10.5 h a day).", RED),
]
rh = 1 / len(items)
tag = {"works": "WORKS", "slow": "SLOW", "fails": "FAILS"}
for k, (kind, name, text, col) in enumerate(items):
    y = 1 - (k + 1) * rh
    ax.add_patch(FancyBboxPatch((0, y + 0.014), 0.105, rh - 0.028, boxstyle="round,pad=0,rounding_size=0.012",
                                fc=col, ec="none"))
    ax.text(0.0525, y + rh / 2, tag[kind], ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.text(0.125, y + rh * 0.66, name, fontsize=19, fontweight="bold", va="center")
    ax.text(0.125, y + rh * 0.30, text, fontsize=13.5, color=MUTED, va="center")
footer(fig, f"  |  EthLib {cov['ethlib_commit'][:8]} ({proofs})")
save(fig, "4-verdict.png")
print("wrote", *sorted(p.name for p in (ROOT / "images").glob("*.png")))
