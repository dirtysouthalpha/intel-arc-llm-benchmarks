# Contributing to Intel Arc LLM Benchmarks

We welcome contributions! This project is about building a comprehensive, transparent knowledge base for Intel Arc GPU LLM inference.

## What We're Looking For

### 1. Model Benchmarks
- Test new models on Intel Arc GPUs
- Follow our documented methodology (see `docs/methodology.md`)
- Submit JSON results + writeup in `docs/findings/`

### 2. Code Improvements
- Enhance the `speed-test.sh` script
- Add new test scripts (e.g., throughput, memory usage)
- Fix bugs or improve error handling

### 3. Documentation
- Improve setup guides
- Add troubleshooting sections
- Document your own Intel Arc LLM journey

### 4. Driver Optimization
- Submit PRs to Intel's open-source projects (llama.cpp, Mesa, oneAPI)
- Reference our benchmarks as evidence for needed optimizations
- Share your findings with Intel's GPU AI team

## How to Contribute

### Step 1: Fork and Clone

```bash
# Fork this repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/intel-arc-llm-benchmarks.git
cd intel-arc-llm-benchmarks
git remote add upstream https://github.com/dirtysouthalpha/intel-arc-llm-benchmarks.git
```

### Step 2: Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### Step 3: Make Your Changes

- For benchmarks: Run `scripts/speed-test.sh` following methodology
- For code: Test thoroughly on your Intel Arc GPU
- For docs: Ensure clarity and accuracy

### Step 4: Commit and Push

```bash
git add .
git commit -m "Clear, descriptive commit message"
git push origin feature/your-feature-name
```

### Step 5: Submit a Pull Request

- Go to the original repo on GitHub
- Click "Pull Requests" → "New Pull Request"
- Describe your changes clearly
- Link to any related issues

## Benchmark Submission Template

When submitting a new model benchmark, include:

```markdown
# Model Name Benchmark

**Test Date**: YYYY-MM-DD
**Hardware**: [Your GPU specs]
**Driver**: [Driver version]
**Backend**: [llama.cpp / vLLM / etc.]

## Model Info

- File: `model-name-quant.gguf`
- Size: X GB
- Architecture: Dense/MoE, X parameters
- Quantization: Q4_K_M / IQ4_XS / etc.

## Test Results

```
Run 1 (warm):  X tokens in Ys = Z tok/s
Run 2 (warm):  X tokens in Ys = Z tok/s
Run 3 (warm):  X tokens in Ys = Z tok/s
```

**Average Speed**: X tok/s

## Analysis

- Comparison to baseline models
- Any unique observations
- Production viability (yes/no/maybe)

## Hardware Notes

- VRAM usage
- Thermal behavior
- Any stability issues
```

## Code Style

### Shell Scripts
- Use `set -e` for error handling
- Add comments for complex logic
- Use variables for magic numbers
- Follow existing patterns in `scripts/speed-test.sh`

### Documentation
- Use clear, concise language
- Include code examples with copy-pasteable blocks
- Link to related docs
- Update table of contents if needed

## Getting Help

- **GitHub Issues**: For bugs, feature requests, questions
- **Discussions**: For general chat, sharing experiences
- **Email**: [Your email for serious inquiries]

## Recognition

Contributors will be:
- Listed in `CONTRIBUTORS.md`
- Credited in related blog posts
- Invited to collaborate on Intel partnership outreach

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for helping make Intel Arc a first-class LLM platform!**
