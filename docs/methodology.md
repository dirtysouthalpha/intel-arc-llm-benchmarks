# Benchmark Methodology

## Testing Philosophy

We test **production-like conditions**, not synthetic benchmarks. Our methodology is designed to answer: "Will this model actually work in my real LLM application?"

## Hardware Baseline

- **GPU**: Intel Arc Pro B60 21GB (Vulkan1)
- **Driver**: Xe (Mesa 3D)
- **Backend**: llama.cpp with Vulkan backend
- **Host OS**: Ubuntu 26.04 LTS, kernel 7.0.0-30-generic
- **RAM**: 30GB total (8.6GB available during tests)

## Metrics We Care About

### 1. Tokens/Second (Primary Metric)
- **What we measure**: Actual inference speed in tokens per second
- **How we measure**: Time from API request to response completion, divided by word count in response
- **Why it matters**: This is what users experience. Latency and throughput in one number.

### 2. Warmup vs. Cold Performance
- **Cold first run**: Server just started, model not cached in GPU memory
- **Warm performance**: Server has handled 1+ requests, caches warmed
- **Why we care**: Production servers are always warm. Cold start matters for deployment, not ongoing performance.

### 3. Production Threshold: 20 tok/s
- Our hard minimum for production deployment
- Below this, users perceive latency as "slow"
- Based on real user feedback and production traffic patterns

## Test Procedure

### 1. Model Loading
```bash
llama-server \
  --model <path-to-gguf> \
  --port 8083 \
  --host 127.0.0.1 \
  --n-gpu-layers 999 \
  --ctx-size 8192 \
  --threads 8 \
  --batch-size 512
```

### 2. Warmup Phase
- Run **1 warmup request** with a simple prompt
- This loads model weights into GPU memory and initializes caches
- Warmup time is NOT included in speed measurements

### 3. Measurement Phase
- Run **3 measured requests** with identical prompts
- Use production-like prompts (code generation, Q&A)
- Record tokens generated and wall-clock time for each
- Calculate tok/s for each run, then average

### 4. Speed Calculation
```bash
# For each measured run:
tokens = word_count(response_text)
duration = end_time - start_time
tok_per_sec = tokens / duration

# Final result:
average_tok_per_sec = sum(tok_per_sec_array) / num_runs
```

## Test Prompt

We use a consistent, production-relevant prompt:

```
Write a Python function that merges two sorted lists and returns a sorted list.
```

This prompt:
- Generates ~50-150 tokens (typical real-world response size)
- Requires reasoning (not just completion)
- Is code generation (our primary workload)
- Is consistent across tests (fair comparison)

## Known Limitations

### 1. Word Count vs. Token Count
- We count words (`wc -w`) as a proxy for tokens
- This undercounts by ~10-15% vs. true tokenization
- We're okay with this: it's consistent across tests and simpler
- For exact token counts, we'd need to run the model's tokenizer separately

### 2. Single-User Testing
- We test one request at a time
- Production handles concurrent requests
- This measures **per-request latency**, not system throughput
- For throughput, we'd need a load testing tool (e.g., Locust)

### 3. Context Window Effects
- We use small contexts (512 tokens) for speed tests
- Large contexts (8K+) may behave differently
- Attention computation scales quadratically with context length
- We plan to add context-size sensitivity testing

### 4. Quantization Artifacts
- Different quants (IQ4_XS, Q4_K_M, Q5_K_S) have different quality
- We measure speed, not quality
- For production, we need both: fast AND coherent outputs

## Fair Comparison Rules

1. **Same hardware**: All tests on same Arc B60, same driver version
2. **Same software**: Same llama.cpp binary, same launch params
3. **Same prompt**: Identical test prompt for all models
4. **Same procedure**: 1 warmup + 3 measured runs
5. **Clean state**: No other models loaded, no GPU competition

## What We DON'T Test (Yet)

- **Multi-request throughput**: Concurrent load, batching behavior
- **Long-context performance**: 4K+ token prompts/responses
- **Quality metrics**: Coherence, factual accuracy, code correctness
- **Memory usage**: VRAM consumption patterns (we trust llama.cpp's reports)
- **Temperature effects**: Different sampling params may affect speed

## Reproducing Our Results

To reproduce our benchmarks:

```bash
# 1. Clone this repo
git clone https://github.com/sentinel-prime/intel-arc-llm-benchmarks.git
cd intel-arc-llm-benchmarks

# 2. Download the model (replace with actual URL)
# Example: wget https://huggingface.co/.../model.gguf

# 3. Run speed test
./scripts/speed-test.sh \
  --model /path/to/model.gguf \
  --quant IQ4_XS \
  --port 8083 \
  --host 127.0.0.1

# 4. Compare results
cat results/latest/speed-test.json | jq '.results.avg_tok_per_sec'
```

## Contributing New Benchmarks

When adding a new model benchmark:

1. Follow this methodology exactly
2. Record your hardware/driver versions
3. Include warmup + measured run times separately
4. Note any deviations from this procedure
5. Submit results as a PR with JSON in `results/latest/`

## Version History

- **v1.0** (2026-09-01): Initial methodology
- Focused on single-request latency on Arc B60
- Production threshold: 20 tok/s
