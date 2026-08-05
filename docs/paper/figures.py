#!/usr/bin/env python3
"""Render the figures for `docs/paper/hush-gauge-paper.md` from the frozen result JSONs.

Run
---
    uv run --with matplotlib docs/paper/figures.py

`matplotlib` is injected for this run only and is deliberately NOT added to
`pyproject.toml` — the `K6`-pinned inference stack the lens fingerprints depend on is
not disturbed by a plotting library the study itself never imports.

Reads (read-only; nothing here loads a model, a lens, or a tokenizer)
--------------------------------------------------------------------
    results/m0-leak-curve-qwen2.5-{0.5b,1.5b,3b}-instruct.json
    results/m1-probe-panel-qwen2.5-{0.5b,1.5b,3b}-instruct.json
    results/m2-ablation-qwen2.5-{0.5b,1.5b,3b}-instruct.json
    results/m2-preservation-qwen2.5-{0.5b,1.5b,3b}-instruct.json
    results/m4-lattice-qwen2.5-{0.5b,1.5b,3b}-instruct.json

Writes
------
    docs/paper/fig1-pressure-ladder.png   M0's secret-level emission by tier, per scale,
                                          with the recorded Wilson intervals, plus the
                                          exposure-matched `T4-turn-1` companion.
    docs/paper/fig2-probe-reads-speech.png (a) M1 recall split by whether the trial emitted,
                                          against the same threshold's FPR;
                                          (b) G2's three arms on the certified-silent
                                          population. Recorded Wilson intervals throughout.
    docs/paper/fig3-dose-curve.png        M2's λ dose curve at the secret level and the trial
                                          level, per scale, with the norm-matched random arm
                                          at λ = 1 and `D29`'s pre-registered 20/25
                                          decidability point.
    docs/paper/fig4-preservation.png      M2's three quantitative preservation clauses —
                                          WikiText NLL, benign QA, acknowledgment — each as
                                          clean value, pre-registered bar, ablated value.
    docs/paper/fig5-lattice.png           (a) M4's trial-level silenced counts by layer set at
                                          0.5B, real direction against the random family;
                                          (b) the 0.5B silenced-set membership matrix under
                                          the frozen `D13` primary oracle.

What this script computes, and what it does not
-----------------------------------------------
It computes NOTHING that is not already in the payloads, with two disclosed exceptions,
both of which are checkable against `docs/M*-RESULTS.md`:

  * `len()` of a recorded set. The M4 payload records `trial_silenced` / `trial_induced` /
    `silenced` as explicit lists; figure 5 plots their cardinality. The recorded object is
    the set; the bar height is its size. The counts reproduce `docs/M4-RESULTS.md` §1's
    trial-level table exactly, and this script prints them so that can be checked.
  * set union over recorded sets. Figure 5(b)'s row list is the union of the seven recorded
    `silenced` lists at 0.5B — a membership operation over recorded names, not arithmetic
    over recorded values.

It does NOT smooth, interpolate, fit, re-bin, pool across cells the study never pooled, or
compute a single confidence interval. Every interval drawn is the `wilson_95` field the
runner recorded beside the count it belongs to. Every rate drawn is either a recorded
`rate` field or the recorded `hits`/`n` pair the runner recorded beside it.

Determinism: same payloads in, same PNGs out. No RNG, no clock, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless; no display, no interactive backend
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "results"
OUT = Path(__file__).resolve().parent

SCALES = [
    ("0.5B", "qwen2.5-0.5b-instruct"),
    ("1.5B", "qwen2.5-1.5b-instruct"),
    ("3B", "qwen2.5-3b-instruct"),
]

# dataviz reference palette, categorical slots 1-3, light mode. Validated all-pairs:
# worst CVD dE 9.2, worst normal-vision dE 24.0 (scripts/validate_palette.js).
# The aqua slot's sub-3:1 surface contrast carries the relief rule — every figure here
# ships direct value labels AND the paper prints the same numbers as a table.
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
SERIES = [C1, C2, C3]
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
SEQ_450 = "#2a78d6"

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.linewidth": 0.8,
        "lines.linewidth": 2.0,
        "legend.frameon": False,
        "figure.dpi": 200,
    }
)

_LOG: list[str] = []


def say(line: str = "") -> None:
    """Print a plotted number (requirement 3 of the disclosure contract)."""
    _LOG.append(line)
    print(line)


def load(stem: str, slug: str) -> dict:
    return json.loads((RESULTS / f"{stem}-{slug}.json").read_text())


def tidy(ax, *, ygrid: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if ygrid:
        ax.set_axisbelow(True)
        ax.yaxis.grid(True)
        ax.xaxis.grid(False)


def err(lo: float, hi: float, point: float) -> list[list[float]]:
    """Turn a RECORDED [lo, hi] interval into matplotlib's offset form.

    This is presentation shape only — the interval is the runner's `wilson_95`, never
    recomputed here.
    """
    return [[max(0.0, point - lo)], [max(0.0, hi - point)]]


# ---------------------------------------------------------------------------
# Figure 1 — M0: the pressure ladder and its exposure control
# ---------------------------------------------------------------------------
def fig1() -> None:
    say("=" * 78)
    say("FIGURE 1 — M0 pressure ladder (secret level, k of 25, frozen D13 primary oracle)")
    say("  source: results/m0-leak-curve-*.json  cells[TIER].rates[unit=secret, oracle=primary]")
    say("=" * 78)

    tiers = ["T0", "T1", "T2", "T3", "T4"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    dodge = {"0.5B": -0.10, "1.5B": 0.0, "3B": 0.10}

    for i, (label, slug) in enumerate(SCALES):
        d = load("m0-leak-curve", slug)
        xs, ys, los, his = [], [], [], []
        say(f"  {label}:")
        for j, t in enumerate(tiers):
            r = next(
                x
                for x in d["cells"][t]["rates"]
                if x["unit"] == "secret" and x["oracle"] == "primary"
            )
            xs.append(j + dodge[label])
            ys.append(r["hits"])
            los.append(r["wilson_95"][0] * r["n"])
            his.append(r["wilson_95"][1] * r["n"])
            say(
                f"    {t:9s} {r['hits']:2d}/{r['n']}  wilson_95 "
                f"[{r['wilson_95'][0]:.4f}, {r['wilson_95'][1]:.4f}]"
            )
        t1 = next(
            x
            for x in d["cells"]["T4_turn1"]["rates"]
            if x["unit"] == "secret" and x["oracle"] == "primary"
        )
        say(
            f"    T4_turn1  {t1['hits']:2d}/{t1['n']}  wilson_95 "
            f"[{t1['wilson_95'][0]:.4f}, {t1['wilson_95'][1]:.4f}]"
        )
        c = d["contrasts"]["T4_vs_T0"]
        say(
            f"    T4-vs-T0  diff {c['diff']:+.3f}  newcombe_95 "
            f"[{c['newcombe_95'][0]:+.4f}, {c['newcombe_95'][1]:+.4f}]  excludes_zero={c['excludes_zero']}"
        )

        ax.errorbar(
            xs,
            ys,
            yerr=[[y - lo for y, lo in zip(ys, los)], [hi - y for y, hi in zip(ys, his)]],
            color=SERIES[i],
            marker="o",
            markersize=5,
            capsize=0,
            elinewidth=1.2,
            label=label,
            zorder=3,
        )
        # the exposure-matched companion, on its own x slot as an open marker
        ax.plot(
            [5 + dodge[label]],
            [t1["hits"]],
            marker="D",
            markersize=7,
            markerfacecolor=SURFACE,
            markeredgecolor=SERIES[i],
            markeredgewidth=1.8,
            linestyle="none",
            zorder=4,
        )
        ax.annotate(
            f"{t1['hits']}/25",
            (5 + dodge[label], t1["hits"]),
            xytext=(0, 9),
            textcoords="offset points",
            fontsize=7,
            color=SERIES[i],
            ha="center",
        )

    ax.axvline(4.5, color=GRID, linewidth=1.0, zorder=0)
    ax.set_xticks(list(range(6)))
    ax.set_xticklabels(
        [
            "T0\nbenign",
            "T1\ndirect ask",
            "T2\nroleplay",
            "T3\ninjection",
            "T4\nmulti-turn",
            "T4-turn-1\nexposure-matched",
        ],
        fontsize=7.5,
    )
    ax.set_xlim(-0.45, 5.45)
    ax.set_ylim(-2.0, 29.0)
    ax.set_yticks([0, 5, 10, 15, 20, 25])
    ax.set_ylabel("secrets emitting at least once (of 25 held-out)")
    ax.set_title(
        "The battery moves floor-to-ceiling — and the ceiling is the measurement problem",
        fontsize=10,
        pad=10,
        loc="left",
    )
    ax.axhline(25, color=AXIS, linewidth=0.8, linestyle=(0, (4, 3)), zorder=1)
    ax.annotate(
        "ceiling — 25 of 25", (-0.35, 25), xytext=(0, 6), textcoords="offset points",
        fontsize=7, color=MUTED, ha="left",
    )
    ax.annotate(
        "◆ open marker: the same T4 trials re-scored\nover turn 1's 64 positions only",
        (5.35, 3.0), fontsize=7, color=INK2, ha="right",
    )
    ax.legend(loc="center left", bbox_to_anchor=(0.02, 0.55), fontsize=8.5, ncol=1)
    tidy(ax)
    fig.tight_layout()
    fig.savefig(OUT / "fig1-pressure-ladder.png", bbox_inches="tight")
    plt.close(fig)
    say("  -> docs/paper/fig1-pressure-ladder.png")
    say()


# ---------------------------------------------------------------------------
# Figure 2 — M1: the probe reads speech, not secrecy
# ---------------------------------------------------------------------------
def fig2() -> None:
    say("=" * 78)
    say("FIGURE 2 — M1 detection nulls")
    say("  (a) source: m1-probe-panel-*.json cells.g1.recall_by_emission, cells.g1.fpr")
    say("  (b) source: m1-probe-panel-*.json cells.g2.{secret,arm_a_no_secret,arm_b_yardstick}")
    say("=" * 78)

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(9.6, 4.1))
    w = 0.30
    xs = [0, 1, 2]

    # -- panel (a) --------------------------------------------------------
    say("  (a) recall at theta*, split by whether the trial emitted; FPR on the null class")
    for k, (key, colour, name) in enumerate(
        [("emitting", C1, "recall | trial emitted"), ("non_emitting", C2, "recall | trial silent")]
    ):
        vals, errs = [], [[], []]
        for _, slug in SCALES:
            g = load("m1-probe-panel", slug)["cells"]["g1"]["recall_by_emission"][key]
            vals.append(g["rate"])
            errs[0].append(g["rate"] - g["wilson_95"][0])
            errs[1].append(g["wilson_95"][1] - g["rate"])
        pos = [x + (k - 0.5) * (w + 0.02) for x in xs]
        axa.bar(pos, vals, width=w, color=colour, label=name, zorder=3, linewidth=0)
        axa.errorbar(pos, vals, yerr=errs, fmt="none", ecolor=INK2, elinewidth=1.0, zorder=4)
        for p, v, e in zip(pos, vals, errs[1]):
            axa.annotate(
                f"{v:.3f}", (p, v + e), xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=7.5, color=INK2,
            )

    fprs = []
    for i, (label, slug) in enumerate(SCALES):
        g = load("m1-probe-panel", slug)["cells"]["g1"]
        rbe = g["recall_by_emission"]
        say(
            f"    {label}: emitting {rbe['emitting']['hits']}/{rbe['emitting']['n']} = "
            f"{rbe['emitting']['rate']:.4f} wilson_95 "
            f"[{rbe['emitting']['wilson_95'][0]:.4f}, {rbe['emitting']['wilson_95'][1]:.4f}]"
        )
        say(
            f"    {label}: silent   {rbe['non_emitting']['hits']}/{rbe['non_emitting']['n']} = "
            f"{rbe['non_emitting']['rate']:.4f} wilson_95 "
            f"[{rbe['non_emitting']['wilson_95'][0]:.4f}, {rbe['non_emitting']['wilson_95'][1]:.4f}]"
        )
        say(
            f"    {label}: FPR      {g['fpr']['hits']}/{g['fpr']['n']} = {g['fpr']['rate']:.4f} "
            f"(theta* = {load('m1-probe-panel', slug)['cells']['theta']:.6f})"
        )
        fprs.append(g["fpr"]["rate"])

    axa.plot(
        xs, fprs, linestyle="none", marker="D", markersize=7,
        markerfacecolor=SURFACE, markeredgecolor=INK, markeredgewidth=1.6,
        label="FPR on null trials (same θ*)", zorder=5,
    )
    for x, v in zip(xs, fprs):
        axa.annotate(
            f"{v:.3f}", (x, v), xytext=(0, -14), textcoords="offset points",
            ha="center", fontsize=7.5, color=INK,
        )
    axa.set_xticks(xs)
    axa.set_xticklabels([s for s, _ in SCALES])
    axa.set_ylim(0, 1.08)
    axa.set_ylabel("rate")
    axa.set_title("(a) detection is carried by trials the model spoke on", fontsize=9.5, loc="left")
    axa.legend(loc="upper right", fontsize=8)
    tidy(axa)

    # -- panel (b) --------------------------------------------------------
    say("  (b) G2: workspace entry on the certified-silent T3/T4 population (secret level)")
    arms = [
        ("secret", C1, "secret (the probed direction)"),
        ("arm_a_no_secret", C2, "arm (a): no-secret baseline"),
        ("arm_b_yardstick", C3, "arm (b): licensed yardstick"),
    ]
    w3 = 0.24
    for k, (key, colour, name) in enumerate(arms):
        vals, errs, labels = [], [[], []], []
        for _, slug in SCALES:
            g = load("m1-probe-panel", slug)["cells"]["g2"][key]["secret_level"]
            vals.append(g["rate"])
            errs[0].append(g["rate"] - g["wilson_95"][0])
            errs[1].append(g["wilson_95"][1] - g["rate"])
            labels.append(f"{g['hits']}/{g['n']}")
        pos = [x + (k - 1) * (w3 + 0.02) for x in xs]
        axb.bar(pos, vals, width=w3, color=colour, label=name, zorder=3, linewidth=0)
        axb.errorbar(pos, vals, yerr=errs, fmt="none", ecolor=INK2, elinewidth=1.0, zorder=4)
        for p, v, lb, e in zip(pos, vals, labels, errs[1]):
            axb.annotate(
                lb, (p, v + e), xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=7.5, color=INK2,
            )

    for label, slug in SCALES:
        g2 = load("m1-probe-panel", slug)["cells"]["g2"]
        p = g2["population"]
        vp = g2["verdict_parts"]["primary"]
        say(f"    {label}: population {p['n_trials']} trials / {p['n_secrets']} secrets")
        for key, nm in [
            ("secret", "secret        "),
            ("arm_a_no_secret", "arm (a) null  "),
            ("arm_b_yardstick", "arm (b) yardst"),
        ]:
            c = g2[key]["secret_level"]
            say(
                f"      {nm} {c['hits']:2d}/{c['n']} = {c['rate']:.4f}  wilson_95 "
                f"[{c['wilson_95'][0]:.4f}, {c['wilson_95'][1]:.4f}]"
            )
        for key, nm in [("arm_a", "secret - (a)"), ("arm_b", "secret - (b)")]:
            v = vp[key]
            say(
                f"      {nm} diff {v['diff']:+.3f} newcombe_95 "
                f"[{v['newcombe_95'][0]:+.4f}, {v['newcombe_95'][1]:+.4f}] "
                f"excludes_zero={v['excludes_zero']}"
            )

    axb.set_xticks(xs)
    axb.set_xticklabels([s for s, _ in SCALES])
    axb.set_ylim(0, 1.08)
    axb.set_ylabel("secrets entering the workspace (rate)")
    axb.set_title(
        "(b) on silent trials the licensed word beats the secret", fontsize=9.5, loc="left"
    )
    axb.legend(loc="upper left", fontsize=8)
    tidy(axb)

    fig.tight_layout()
    fig.savefig(OUT / "fig2-probe-reads-speech.png", bbox_inches="tight")
    plt.close(fig)
    say("  -> docs/paper/fig2-probe-reads-speech.png")
    say()


# ---------------------------------------------------------------------------
# Figure 3 — M2: the dose curve
# ---------------------------------------------------------------------------
def fig3() -> None:
    say("=" * 78)
    say("FIGURE 3 — M2 dose curve (source: m2-ablation-*.json cells.dose_curve, cells.arms.random_1)")
    say("=" * 78)

    fig, (axs, axt) = plt.subplots(1, 2, figsize=(9.6, 4.1))
    rand_dodge = {"0.5B": 1.06, "1.5B": 1.12, "3B": 1.18}
    # 1.5B and 3B share identical secret-level values at every dose, so the series are
    # dodged +-0.013 on x for legibility. Presentation only; the printed values are exact
    # and the caption states the dodge.
    x_dodge = {"0.5B": -0.013, "1.5B": 0.0, "3B": 0.013}
    for i, (label, slug) in enumerate(SCALES):
        c = load("m2-ablation", slug)["cells"]
        lam = [p["lambda"] + x_dodge[label] for p in c["dose_curve"]]
        say(f"  {label}:")
        for unit, ax, n, ylab in [
            ("secret_level", axs, 25, "secrets emitting (of 25)"),
            ("trial_level", axt, 100, "trials emitting (of 100)"),
        ]:
            ys = [p[unit]["hits"] for p in c["dose_curve"]]
            lo = [p[unit]["wilson_95"][0] * n for p in c["dose_curve"]]
            hi = [p[unit]["wilson_95"][1] * n for p in c["dose_curve"]]
            ax.errorbar(
                lam, ys,
                yerr=[[y - l for y, l in zip(ys, lo)], [h - y for y, h in zip(ys, hi)]],
                color=SERIES[i], marker="o", markersize=5, capsize=0, elinewidth=1.1,
                label=label, zorder=3,
            )
            ax.set_ylabel(ylab)
            r = c["arms"]["random_1"]["emission"][unit]
            ax.plot(
                [rand_dodge[label]], [r["hits"]], marker="D", markersize=6.5,
                markerfacecolor=SURFACE, markeredgecolor=SERIES[i], markeredgewidth=1.6,
                linestyle="none", zorder=4,
            )
        for p in c["dose_curve"]:
            say(
                f"    lambda={p['lambda']:<5} secret {p['secret_level']['hits']:2d}/25 "
                f"wilson_95 [{p['secret_level']['wilson_95'][0]:.4f}, "
                f"{p['secret_level']['wilson_95'][1]:.4f}]   trial "
                f"{p['trial_level']['hits']:3d}/100 wilson_95 "
                f"[{p['trial_level']['wilson_95'][0]:.4f}, {p['trial_level']['wilson_95'][1]:.4f}]"
            )
        rr = c["arms"]["random_1"]["emission"]
        say(
            f"    random (norm-matched, lambda=1): secret {rr['secret_level']['hits']}/25   "
            f"trial {rr['trial_level']['hits']}/100"
        )
        g1c = c["g3_clause_1_causal"]["per_arm_assignment"]
        say(
            f"    G3 clause (1) lambda=1 vs lambda=0: diff {g1c['diff']:+.3f} newcombe_95 "
            f"[{g1c['newcombe_95'][0]:+.4f}, {g1c['newcombe_95'][1]:+.4f}] "
            f"excludes_zero={g1c['excludes_zero']}"
        )
        sc = c["specificity_contrast"]["per_arm_assignment"]
        say(
            f"    lambda=1 vs random:                diff {sc['diff']:+.3f} newcombe_95 "
            f"[{sc['newcombe_95'][0]:+.4f}, {sc['newcombe_95'][1]:+.4f}] "
            f"excludes_zero={sc['excludes_zero']}"
        )

    axs.axhline(20, color=INK2, linewidth=1.0, linestyle=(0, (5, 3)), zorder=2)
    axs.annotate(
        "20/25 — D29's first decidable reduction",
        (0.02, 20), xytext=(0, 5), textcoords="offset points",
        fontsize=7.5, color=INK2,
    )
    axs.set_ylim(10, 28)
    axs.set_title("(a) secret level — the deciding unit", fontsize=9.5, loc="left")
    axt.set_ylim(14, 86)
    axt.set_title("(b) trial level — reported, decides nothing", fontsize=9.5, loc="left")
    for ax in (axs, axt):
        ax.set_xlabel("λ  (dose;  h' = h − λ (v̂ · h) v̂ at every band layer, every position)")
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_xlim(-0.06, 1.26)
        tidy(ax)
        ax.plot([], [], marker="D", markersize=6.5, markerfacecolor=SURFACE,
                markeredgecolor=INK2, markeredgewidth=1.6, linestyle="none",
                label="norm-matched\nrandom direction, λ = 1")
    axs.legend(loc="lower left", fontsize=8, handletextpad=0.6)
    axt.legend(loc="lower left", fontsize=8, handletextpad=0.6)
    fig.tight_layout()
    fig.savefig(OUT / "fig3-dose-curve.png", bbox_inches="tight")
    plt.close(fig)
    say("  -> docs/paper/fig3-dose-curve.png")
    say()


# ---------------------------------------------------------------------------
# Figure 4 — M2: the preservation battery
# ---------------------------------------------------------------------------
def fig4() -> None:
    say("=" * 78)
    say("FIGURE 4 — M2 preservation battery (source: m2-preservation-*.json cells.*)")
    say("=" * 78)

    clauses = [
        ("wikitext_nll", "WikiText NLL (nats)\nlower is better; bar is a ceiling", "nll"),
        ("benign_qa", "benign QA accuracy\nhigher is better; bar is a floor", "prop"),
        ("acknowledgment", "acknowledgment rate\nhigher is better; bar is a floor", "prop"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 4.0))
    xs = [0, 1, 2]

    for ax, (key, title, kind) in zip(axes, clauses):
        say(f"  clause: {key}")
        cleans, ablateds, bars, verdicts = [], [], [], []
        for label, slug in SCALES:
            c = load("m2-preservation", slug)["cells"][key]
            if kind == "nll":
                clean = c["clean"]["pooled_mean_nll"]
                ablated = c["ablated"]["pooled_mean_nll"]
                bar = c["bootstrap"]["bar"]
                say(
                    f"    {label}: clean {clean:.4f} (ppl {c['clean']['perplexity']:.2f})  "
                    f"bar {bar:.4f}  ablated {ablated:.4f} "
                    f"(ppl {c['ablated']['perplexity']:.2f})  -> {c['verdict']}"
                )
                say(
                    f"           realized tolerance {c['tolerance']['nats']:.4f} nats "
                    f"(x{c['tolerance']['perplexity_ratio']:.4f} perplexity)"
                )
            else:
                clean = c["clean"]["rate"]
                ablated = c["ablated"]["rate"]
                bar = c["bar"]
                say(
                    f"    {label}: clean {c['clean']['hits']}/{c['clean']['n']} = {clean:.4f}  "
                    f"bar {bar:.4f}  ablated {c['ablated']['hits']}/{c['ablated']['n']} = "
                    f"{ablated:.4f}  -> {c['verdict']}"
                )
                say(
                    f"           permitted drop "
                    f"{c['tolerance']['permitted_drop_points']:.2f} points"
                )
            cleans.append(clean)
            ablateds.append(ablated)
            bars.append(bar)
            verdicts.append(c["verdict"])

        for x, cl, ab in zip(xs, cleans, ablateds):
            ax.plot([x, x], [cl, ab], color=AXIS, linewidth=1.4, zorder=2)
        ax.plot(xs, cleans, linestyle="none", marker="o", markersize=8, color=C1,
                label="clean (λ = 0)", zorder=4)
        ax.plot(xs, ablateds, linestyle="none", marker="o", markersize=8, color=C2,
                label="ablated (λ = 1)", zorder=4)
        for x, b in zip(xs, bars):
            ax.plot([x - 0.26, x + 0.26], [b, b], color=INK, linewidth=1.6,
                    linestyle=(0, (4, 2.5)), zorder=3)
        ax.plot([], [], color=INK, linewidth=1.6, linestyle=(0, (4, 2.5)),
                label="pre-registered bar")

        for x, v, ab in zip(xs, verdicts, ablateds):
            if v == "FAILS":
                ax.annotate(
                    "FAILS", (x, ab), xytext=(13, -3), textcoords="offset points",
                    ha="left", fontsize=8, color=INK, fontweight="bold",
                )
        ax.set_xticks(xs)
        ax.set_xticklabels([s for s, _ in SCALES])
        ax.set_title(title, fontsize=8.5, loc="left")
        ax.set_xlim(-0.5, 2.6)
        lo = min(cleans + ablateds + bars)
        hi = max(cleans + ablateds + bars)
        pad = (hi - lo) * 0.16
        ax.set_ylim(lo - pad, hi + pad)
        tidy(ax)

    axes[0].legend(loc="upper right", fontsize=7.5)
    fig.suptitle(
        "The battery catches the price of the edit — and a different clause breaks at each scale",
        fontsize=10, x=0.012, ha="left", y=1.02,
    )
    fig.tight_layout()
    fig.savefig(OUT / "fig4-preservation.png", bbox_inches="tight")
    plt.close(fig)
    say("  -> docs/paper/fig4-preservation.png")
    say()


# ---------------------------------------------------------------------------
# Figure 5 — M4: the layer-set lattice
# ---------------------------------------------------------------------------
ARM_OF_SET = {
    "early": ("third_early", "{early}"),
    "mid": ("third_mid", "{mid}"),
    "late": ("third_late", "{late}"),
    "early_mid": ("union_early_mid", "{early+mid}"),
    "early_late": ("union_early_late", "{early+late}"),
    "mid_late": ("union_mid_late", "{mid+late}"),
    "full": ("lambda_1", "{early+mid+late}"),
}
SET_ORDER = ["early", "mid", "late", "early_mid", "early_late", "mid_late", "full"]


def fig5() -> None:
    say("=" * 78)
    say("FIGURE 5 — M4 layer-set lattice at 0.5B (source: m4-lattice-qwen2.5-0.5b-instruct.json)")
    say("  bar heights are len() of the payload's recorded trial_silenced list — disclosed")
    say("=" * 78)

    d = load("m4-lattice", "qwen2.5-0.5b-instruct")
    cells = d["cells"]
    both = {**cells["arms"], **cells["recorded_arms"]}
    layer_sets = d["layer_sets"]

    labels, n_layers, real_sil, rand_sil, real_ind, rand_ind = [], [], [], [], [], []
    for s in SET_ORDER:
        arm, pretty = ARM_OF_SET[s]
        rp = both[arm]["readings"]["primary"]
        qp = cells["arms"][f"random_{s}"]["readings"]["primary"]
        labels.append(f"{pretty}\n{len(layer_sets[s])} layers")
        n_layers.append(len(layer_sets[s]))
        real_sil.append(len(rp["trial_silenced"]))
        rand_sil.append(len(qp["trial_silenced"]))
        real_ind.append(len(rp["trial_induced"]))
        rand_ind.append(len(qp["trial_induced"]))
        say(
            f"  {pretty:20s} layers {len(layer_sets[s]):2d} | real: silenced "
            f"{len(rp['trial_silenced']):2d} induced {len(rp['trial_induced']):2d}, "
            f"secret-level {rp['secret_level']['hits']:2d}/25, silenced set "
            f"{sorted(rp['silenced'])} | random: silenced {len(qp['trial_silenced']):2d} "
            f"induced {len(qp['trial_induced']):2d}, secret-level "
            f"{qp['secret_level']['hits']}/25, DEGENERATE={qp['degenerate']}"
        )
    base = cells["arms"]["lambda_0"]["readings"]["primary"]["trial_level"]
    say(f"  lambda_0 baseline: {base['hits']}/{base['n']} trials emitting")

    fig = plt.figure(figsize=(11.0, 4.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.06, 1.0], wspace=0.26)
    axa = fig.add_subplot(gs[0, 0])
    axb = fig.add_subplot(gs[0, 1])

    # -- panel (a): trial-level silenced counts, real vs random ------------
    xs = list(range(len(SET_ORDER)))
    w = 0.36
    axa.bar([x - w / 2 - 0.01 for x in xs], real_sil, width=w, color=C1,
            label="real direction (v̂_secret)", zorder=3, linewidth=0)
    axa.bar([x + w / 2 + 0.01 for x in xs], rand_sil, width=w, color=C2,
            label="norm-matched random family (D47)", zorder=3, linewidth=0)
    for x, v in zip(xs, real_sil):
        axa.annotate(str(v), (x - w / 2 - 0.01, v), xytext=(0, 3),
                     textcoords="offset points", ha="center", fontsize=7.5, color=INK2)
    for x, v in zip(xs, rand_sil):
        axa.annotate(str(v), (x + w / 2 + 0.01, v), xytext=(0, 3),
                     textcoords="offset points", ha="center", fontsize=7.5, color=INK2)

    for s, x in zip(SET_ORDER, xs):
        if "late" in s or s == "full":
            axa.add_patch(
                Rectangle((x - 0.5, 0), 1.0, 56, facecolor=C1, alpha=0.06,
                          edgecolor="none", zorder=1)
            )
    axa.annotate(
        "shaded: layer sets containing the late third",
        (-0.45, 53.6), fontsize=7.5, color=INK2,
    )
    axa.set_xticks(xs)
    axa.set_xticklabels(labels, fontsize=7.0, rotation=32, ha="right",
                        rotation_mode="anchor")
    axa.set_ylim(0, 58)
    axa.set_xlim(-0.55, len(SET_ORDER) - 0.45)
    axa.set_ylabel("trials silenced vs λ = 0 (of a 63/100 baseline)")
    axa.set_title(
        "(a) the late third's presence sets the size — not the layer count",
        fontsize=9.5, loc="left",
    )
    axa.legend(loc="upper left", fontsize=8, bbox_to_anchor=(0.02, 0.90))
    tidy(axa)

    # -- panel (b): the silenced-set membership matrix ---------------------
    sets = {}
    for s in SET_ORDER:
        arm, _ = ARM_OF_SET[s]
        sets[s] = set(both[arm]["readings"]["primary"]["silenced"])
    rows = sorted(set().union(*sets.values()))
    say(f"  union of the seven recorded silenced sets ({len(rows)} secrets): {rows}")

    axb.set_xlim(-0.5, len(SET_ORDER) - 0.5)
    axb.set_ylim(-0.5, len(rows) - 0.5)
    for j, s in enumerate(SET_ORDER):
        for i, secret in enumerate(rows):
            filled = secret in sets[s]
            axb.add_patch(
                Rectangle(
                    (j - 0.42, i - 0.42), 0.84, 0.84,
                    facecolor=SEQ_450 if filled else SURFACE,
                    edgecolor=AXIS if not filled else "none",
                    linewidth=0.7, zorder=3,
                )
            )
    axb.set_xticks(range(len(SET_ORDER)))
    axb.set_xticklabels([ARM_OF_SET[s][1] for s in SET_ORDER], fontsize=7.0, rotation=32,
                        ha="right", rotation_mode="anchor")
    axb.set_yticks(range(len(rows)))
    axb.set_yticklabels(rows, fontsize=7.8)
    axb.set_title(
        "(b) which secrets each layer set silences — filled = silenced",
        fontsize=9.5, loc="left", pad=22,
    )
    for spine in axb.spines.values():
        spine.set_visible(False)
    axb.tick_params(length=0)
    axb.invert_yaxis()

    # the non-nesting, called out on the rows that carry it
    only_late = sorted(
        s for s in rows if sets["late"] == set(sets["late"]) and s in sets["late"]
        and not any(s in sets[o] for o in SET_ORDER if o != "late")
    )
    say(f"  silenced by {{late}} and by no other layer set: {only_late}")
    if only_late:
        for s in only_late:
            axb.add_patch(
                Rectangle(
                    (SET_ORDER.index("late") - 0.46, rows.index(s) - 0.46), 0.92, 0.92,
                    facecolor="none", edgecolor=INK, linewidth=1.6, zorder=5,
                )
            )
        axb.annotate(
            "outlined: " + " and ".join(only_late) + " — silenced by {late},\n"
            "and by no other layer set in the lattice",
            xy=(0.0, 1.02), xycoords="axes fraction",
            fontsize=7.2, color=INK, va="bottom", ha="left",
        )

    fig.savefig(OUT / "fig5-lattice.png", bbox_inches="tight")
    plt.close(fig)
    say("  -> docs/paper/fig5-lattice.png")
    say()


def main() -> None:
    say("hush-gauge paper figures — every plotted number, printed.")
    say("Generated by docs/paper/figures.py from results/*.json. No model, lens or")
    say("tokenizer is loaded; no statistic is computed that the payloads do not record.")
    say()
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    say("done.")


if __name__ == "__main__":
    main()
