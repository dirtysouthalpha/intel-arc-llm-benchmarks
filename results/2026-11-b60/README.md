# B60 lane benchmark — 2026-11-01

Measured on the production host (Strix Halo box with the Arc Pro B60 on OCuLink). Hostnames and local paths in these files are genericized.

Files: `results.csv` (12 rows, one per lane x context fill), `raw_runs.jsonl` (every individual run),
`env.json` (host, kernel, Mesa, lanes, load), `bench-b60.png` (chart), `bench_b60.py`, `chart.py`, `bench.log`.

Rerun: `python3 bench_b60.py --reps 3 && python3 chart.py` (needs passwordless sudo for fdinfo of root-owned lanes).

## What was benchmarked
There is no llama-swap on this rig; the `intel-arc-llm-stack` llama-swap config is the old Windows layout from a previous Windows host. Here the B60 runs four fixed systemd
llama-server lanes (llama.cpp b11706, Vulkan0 = Arc Pro B60), all co-resident, discovered live by the script:

| port | alias | model | slot n_ctx |
|---|---|---|---|
| 8083 | internvl3-8b | InternVL3-8B-Instruct-Q4_K_M (+mmproj) | 32768 |
| 8086 | decider-4b | decider-4b-v2.1-Q4_K_M | 8192 |
| 8087 | qwen3-8b-fast | Qwen3-8B-finetune-Q5_K_M | 8192 x 2 slots |
| 8088 | qwen3-reranker | qwen3-reranker-0.6b-q8_0 | 8192 (rerank) |

`:8084` cyber-tiel-coder-35b is `--device Vulkan1` = Radeon 8060S iGPU, so it is NOT on the B60 and is excluded.

## Method
Context fills 1024 / 4096 / 7680 prompt tokens (7680 + 128 gen fits the 8192-slot lanes), built with each
lane's own `/tokenize`+`/detokenize`. `POST /completion` streamed, `cache_prompt=false`, `temperature=0`,
`n_predict=128`. TTFT = client wall time to first streamed token. Prefill/decode tok/s = server `timings`.
VRAM = kernel xe `drm-total-vram0` from `/proc/<pid>/fdinfo` (deduped by drm-client-id), baseline + 0.25 s peak sampling.
Rerank: `/v1/rerank` with 8/32/64 ~220-token docs; `ttft_ms` column = full rerank latency.

## Caveats
- In place and co-resident: the four lanes share the card and the host was at load ~11-13 (an unrelated CPU job was running). These are production-condition numbers, not peak numbers.
- internvl3-8b and decider-4b hit EOS at ~40 generated tokens; decode tok/s comes from server timings so it is still valid.
- VRAM is per-process resident on the B60 and does not move with context here because KV is pre-allocated at slot n_ctx.
