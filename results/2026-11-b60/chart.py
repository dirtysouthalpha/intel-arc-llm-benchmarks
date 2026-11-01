#!/usr/bin/env python3
"""chart.py — render results.csv -> bench-b60.png (three panels: decode tok/s, TTFT, VRAM)."""
import csv, os, sys, json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [r for r in csv.DictReader(open(os.path.join(HERE, "results.csv"))) if r["kind"] == "generate" and r["decode_tok_s"]]
env = json.load(open(os.path.join(HERE, "env.json")))
fills = sorted({int(r["ctx_fill"]) for r in rows})
models = []
for r in rows:
    if r["alias"] not in models: models.append(r["alias"])

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]           # fixed slots 1-3 = context fills, never cycled
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK, "axes.edgecolor": GRID,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.facecolor": SURF, "figure.facecolor": SURF})

def val(alias, fill, key):
    for r in rows:
        if r["alias"] == alias and int(r["ctx_fill"]) == fill: return float(r[key])
    return float("nan")

panels = [("decode_tok_s", "Decode speed (tokens/s, higher is better)", "{:.1f}"),
          ("ttft_ms", "Time to first token (ms, lower is better)", "{:.0f}"),
          ("vram_mib_peak", "VRAM resident per lane (MiB, peak during run)", "{:.0f}")]
fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), dpi=160)
w = 0.8 / len(fills)
for ax, (key, title, fmt) in zip(axes, panels):
    for j, fill in enumerate(fills):
        xs = [i + (j - (len(fills) - 1) / 2) * w for i in range(len(models))]
        ys = [val(m, fill, key) for m in models]
        bars = ax.bar(xs, ys, width=w - 0.02, color=SERIES[j], label=f"{fill // 1024}K-token prompt", linewidth=0)
        for b, y in zip(bars, ys):
            if y == y: ax.text(b.get_x() + b.get_width() / 2, y, fmt.format(y), ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_title(title, loc="left", fontsize=10.5, color=INK, pad=10)
    ax.set_xticks(range(len(models))); ax.set_xticklabels(models, fontsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
axes[0].legend(frameon=False, fontsize=8.5, loc="upper right")
fig.suptitle(f"Intel Arc Pro B60 · co-resident llama.cpp Vulkan lanes · {env['host']} · {env['ts'][:10]}",
             x=0.01, ha="left", fontsize=12, color=INK, fontweight="bold")
fig.text(0.01, 0.005, f"In place, no restarts. cache_prompt=false, temperature=0, up to {env['gen_tokens']} generated tokens, median of {env['reps']} runs. "
         "VRAM = kernel xe fdinfo per process. Data + script: results/2026-11-b60/", fontsize=7.5, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
out = os.path.join(HERE, "bench-b60.png"); fig.savefig(out); print("wrote", out)
