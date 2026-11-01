# intel-arc-llm-benchmarks

**Production-validated LLM inference benchmarks for Intel Arc GPUs (Battlemage B60) — real measured tok/s, proven quantization recipes, and MoE-vs-dense data, not synthetic marketing numbers.**

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22D3EE?style=flat-square&labelColor=0A0A0F" alt="MIT license"></a>
  <a href="https://github.com/dirtysouthalpha/intel-arc-llm-benchmarks/actions/workflows/ci.yml"><img src="https://github.com/dirtysouthalpha/intel-arc-llm-benchmarks/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/GPU-Intel%20Arc%20B60-22D3EE?style=flat-square&labelColor=0A0A0F" alt="Intel Arc B60">
  <img src="https://img.shields.io/badge/backend-llama.cpp%20Vulkan-22D3EE?style=flat-square&labelColor=0A0A0F" alt="llama.cpp Vulkan">
  <img src="https://img.shields.io/badge/workload-24%2F7%20production-8B5CF6?style=flat-square&labelColor=0A0A0F" alt="24/7 production">
</p>

<p align="center">
  <img src="assets/banner.svg" alt="intel-arc-llm-benchmarks — real measured LLM inference on Intel Arc">
</p>

> 🔧 **Want to run these models yourself?** The companion repo **[intel-arc-llm-stack](https://github.com/dirtysouthalpha/intel-arc-llm-stack)** is the full one-command server (IPEX-LLM SYCL + Vulkan llama.cpp + model hot-swap + OpenAI-compatible gateway) these benchmarks are measured on.

## Quickstart

Requirements: `bash`, `curl`, `jq`, `bc`, and a running `llama-server` (llama.cpp, Vulkan backend) serving the model you want to measure. The launch flags we use are in [docs/methodology.md](docs/methodology.md#test-procedure).

```bash
# Clone
git clone https://github.com/dirtysouthalpha/intel-arc-llm-benchmarks.git
cd intel-arc-llm-benchmarks

# Start llama-server on 127.0.0.1:8083 (see docs/methodology.md), then run a speed test:
./scripts/speed-test.sh --model /path/to/model.gguf --quant IQ4_XS
#   options: --port 8083 --host 127.0.0.1 --prompt "<text>" --warmup 1 --runs 3   (-h for usage)

# View results (1 warmup + 3 measured runs, averaged)
jq '.results.avg_tok_per_sec' results/latest/speed-test.json

# Run the repo's own test suite (needs shellcheck + bats)
make test
```

The script exits `0` when the average is above the 20 tok/s production threshold and `1` otherwise, so it drops straight into CI or a cron job.

## Hardware tested

All numbers in this repo come from one machine, measured under the [documented methodology](docs/methodology.md) (1 warmup + 3 measured runs, word count as token proxy).

| GPU | VRAM | Driver / Backend | Host OS | Model | Quant | Speed (warm) | Status |
|-----|------|------------------|---------|-------|-------|--------------|--------|
| Intel Arc Pro B60 (Battlemage) | 21 GB | xe (Mesa 3D) / llama.cpp Vulkan | Ubuntu 26.04 LTS, kernel 7.0.0-30-generic | Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated (MoE) | IQ4_XS | ~40 tok/s | ✅ PRODUCTION |
| Intel Arc Pro B60 (Battlemage) | 21 GB | xe (Mesa 3D) / llama.cpp Vulkan | Ubuntu 26.04 LTS, kernel 7.0.0-30-generic | Huihui-Qwen3.8-27B-abliterated (dense) | IQ4_XS | 4.4 tok/s | ❌ REJECTED |

Full write-up: [docs/findings/dense-vs-moe-2026-09-01.md](docs/findings/dense-vs-moe-2026-09-01.md). Got a different Intel Arc card? Add a row via PR following the methodology.

## Our Setup

- **GPU**: Intel Arc Pro B60 21GB (Vulkan1)
- **Host**: Ubuntu 26.04 LTS, 7.0.0-30-generic kernel
- **Driver**: xe driver (Xe architecture)
- **Backend**: llama.cpp Vulkan
- **Production Model**: Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated IQ4_XS @ ~40 tok/s

## Why This Exists

Most LLM benchmarks are NVIDIA-focused. Intel Arc owners get vague "it works" claims but no real-world data.

We run **production LLM workloads** on an Arc B60 24/7. We have:
- Real speed measurements (not synthetic benchmarks)
- Proven quantization recipes
- Actual production traffic patterns
- Autonomous testing infrastructure

## Current Findings (2026-09-01)

### Models Tested

| Model | Size | Quant | Speed (warm) | Status |
|-------|------|-------|--------------|--------|
| Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated | 30B | IQ4_XS | ~40 tok/s | ✅ PRODUCTION |
| Huihui-Qwen3.8-27B-abliterated | 27B | IQ4_XS | 4.4 tok/s | ❌ REJECTED |

### Key Insights

1. **MoE > Dense**: 30B MoE outperforms 27B dense by 9x on B60 Vulkan
2. **Speed floor**: 20 tok/s is our hard minimum for production
3. **A3B quantization**: IQ4_XS hits the sweet spot of speed + quality
4. **No co-loading**: Never load two models on B60 simultaneously - driver spills to RAM

### Known Bottlenecks

- **Speculative decoding**: Not available on Intel Vulkan backend
- **Low-bit tensor kernels**: Missing compared to NVIDIA's CUDA implementations
- **Attention optimization**: Basic implementation, no Flash Attention equivalent

## Repository Structure

```
intel-arc-llm-benchmarks/
├── README.md                 # This file
├── CONTRIBUTING.md           # How to submit benchmarks and patches
├── docs/
│   ├── methodology.md        # Testing methodology and metrics
│   └── findings/             # Detailed benchmark results by model
├── scripts/
│   ├── speed-test.sh         # Speed test script (tok/s via llama-server API)
│   └── test.sh               # Repo test entrypoint (shellcheck + bats + link check)
├── tests/                    # bats tests + markdown link checker
├── Makefile                  # make test / lint / links
└── results/latest/           # Generated by speed-test.sh (git-ignored)
```

Planned, not yet in the tree: `docs/setup.md`, `scripts/benchmark.sh`, `scripts/cleanup.sh`, `configs/launch-templates/`.

## Testing

```bash
make test        # shellcheck + bats + markdown link check (what CI runs)
make lint        # shellcheck only
make links       # relative-link check only
BATS=/path/to/bats make test   # use a bats binary that is not on PATH
```

## Contributing

We welcome contributions, especially:
- Model benchmarks (please follow our [methodology](docs/methodology.md))
- Driver optimization patches
- Quantization experiments
- Production deployment guides

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

## License

MIT License - See [LICENSE](LICENSE) file. Trademark terms: [TRADEMARK.md](TRADEMARK.md).

## Contact

- **Maintainer**: [@dirtysouthalpha](https://github.com/dirtysouthalpha)
- **Hardware**: Intel Arc Pro B60 (Battlemage), Ubuntu 26.04
- **Production**: 24/7 local LLM inference
- Questions, corrections, or your own numbers? [Open an issue](https://github.com/dirtysouthalpha/intel-arc-llm-benchmarks/issues).

---

**Our mission**: Make Intel Arc a first-class citizen for LLM inference through transparent, production-validated benchmarks.

---

## Support this project

Built and maintained by one person, in the open. If it saves you time or
money, you can throw something in the hat — entirely optional, and it changes
nothing about the license or what ships.

<a href="https://cash.app/$vladien"><img src="docs/assets/donate-cashapp.png" alt="Cash App donation QR code for $vladien" width="170" align="left" hspace="18" vspace="6"></a>

**Cash App — [$vladien](https://cash.app/$vladien)**

Scan the code, or follow the link.

No tiers, no paywalled features, no "pro" build.

<br clear="left">

---
### More from Dirty South Alpha
*Self-hosted AI. Security-first. Always innovating.*

- 🚀 [intel-arc-llm-stack](https://github.com/dirtysouthalpha/intel-arc-llm-stack) — run any LLM locally on Intel Arc
- 🎛️ [muse-maestro](https://github.com/dirtysouthalpha/muse-maestro) — guardrails, memory & cost telemetry for Meta Muse Code
- 🤖 [sentinel-code](https://github.com/dirtysouthalpha/sentinel-code) — multi-provider AI coding agent with smart model routing
- 🛠️ [msp-tier3-toolkit](https://github.com/dirtysouthalpha/msp-tier3-toolkit) — battle-tested MSP PowerShell
- 👤 [@dirtysouthalpha](https://github.com/dirtysouthalpha) — the full fleet

⭐ If this saved you time, star it and follow for more.

---
<p align="center"><sub><b>Dirty South Alpha™</b> · © 2026 · <a href="https://dirtysouthalpha.com">dirtysouthalpha.com</a> · self-hosted AI · security-first</sub></p>
