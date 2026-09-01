#!/bin/bash
# Speed test script for Intel Arc B60 LLM inference
# Measures tokens/second for a given GGUF model

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Defaults
MODEL_PATH=""
QUANT=""
PORT=8083
HOST="127.0.0.1"
TEST_PROMPT="Write a Python function that merges two sorted lists and returns a sorted list."
WARMUP_RUNS=1
MEASURE_RUNS=3
RESULTS_DIR="results/latest"

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_PATH="$2"
            shift 2
            ;;
        --quant)
            QUANT="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --prompt)
            TEST_PROMPT="$2"
            shift 2
            ;;
        --warmup)
            WARMUP_RUNS="$2"
            shift 2
            ;;
        --runs)
            MEASURE_RUNS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ -z "$MODEL_PATH" ]]; then
    echo -e "${RED}Error: --model is required${NC}"
    echo "Usage: $0 --model <path-to-gguf> --quant <quant_name> [--port 8083] [--host 127.0.0.1]"
    exit 1
fi

if [[ ! -f "$MODEL_PATH" ]]; then
    echo -e "${RED}Error: Model file not found: $MODEL_PATH${NC}"
    exit 1
fi

# Create results dir
mkdir -p "$RESULTS_DIR"

# Get model info
MODEL_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
MODEL_NAME=$(basename "$MODEL_PATH" | sed 's/.gguf$//')

echo -e "${GREEN}=== Intel Arc B60 Speed Test ===${NC}"
echo "Model: $MODEL_NAME"
echo "Size: $MODEL_SIZE"
echo "Quant: ${QUANT:-unknown}"
echo "Target: http://$HOST:$PORT"
echo "Warmup runs: $WARMUP_RUNS"
echo "Measure runs: $MEASURE_RUNS"
echo ""

# Function to run single inference and measure speed
run_inference() {
    local prompt="$1"
    local run_num="$2"

    local start_time=$(date +%s.%N)
    local output=$(curl -s -X POST "http://$HOST:$PORT/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$MODEL_NAME\",
            \"messages\": [{\"role\": \"user\", \"content\": \"$prompt\"}],
            \"max_tokens\": 150,
            \"temperature\": 0.7
        }")
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    # Count tokens in response
    local tokens=$(echo "$output" | jq -r '.choices[0].message.content' | wc -w)
    local tok_per_sec=$(echo "scale=2; $tokens / $duration" | bc)

    echo "$tokens|$duration|$tok_per_sec|$output"
}

# Warmup runs (not measured)
echo -e "${YELLOW}Warming up...${NC}"
for i in $(seq 1 $WARMUP_RUNS); do
    echo -n "  Warmup $i/$WARMUP_RUNS... "
    run_inference "$TEST_PROMPT" "warmup-$i" > /dev/null
    echo "done"
done
echo ""

# Measured runs
echo -e "${GREEN}Running measured tests...${NC}"
declare -a tok_per_sec_array
declare -a token_counts
declare -a durations

for i in $(seq 1 $MEASURE_RUNS); do
    echo -n "  Run $i/$MEASURE_RUNS... "

    local result=$(run_inference "$TEST_PROMPT" "measure-$i")
    local tokens=$(echo "$result" | cut -d'|' -f1)
    local duration=$(echo "$result" | cut -d'|' -f2)
    local tps=$(echo "$result" | cut -d'|' -f3)

    tok_per_sec_array+=("$tps")
    token_counts+=("$tokens")
    durations+=("$duration")

    echo "$tokens tokens in ${duration}s = ${tps} tok/s"
done
echo ""

# Calculate stats
sum=0
for tps in "${tok_per_sec_array[@]}"; do
    sum=$(echo "$sum + $tps" | bc)
done
avg_tps=$(echo "scale=2; $sum / $MEASURE_RUNS" | bc)

# Find min/max
min_tps=$(printf '%s\n' "${tok_per_sec_array[@]}" | sort -n | head -1)
max_tps=$(printf '%s\n' "${tok_per_sec_array[@]}" | sort -n | tail -1)

# Save results
cat > "$RESULTS_DIR/speed-test.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "model": {
    "name": "$MODEL_NAME",
    "path": "$MODEL_PATH",
    "size": "$MODEL_SIZE",
    "quant": "$QUANT"
  },
  "hardware": {
    "gpu": "Intel Arc Pro B60 21GB",
    "backend": "Vulkan1",
    "driver": "xe"
  },
  "test_config": {
    "prompt": "$TEST_PROMPT",
    "max_tokens": 150,
    "warmup_runs": $WARMUP_RUNS,
    "measure_runs": $MEASURE_RUNS
  },
  "results": {
    "avg_tok_per_sec": $avg_tps,
    "min_tok_per_sec": $min_tps,
    "max_tok_per_sec": $max_tps,
    "runs": [
EOF

# Add individual runs
first=true
for i in $(seq 0 $(($MEASURE_RUNS - 1))); do
    if [ "$first" = true ]; then
        first=false
    else
        echo "," >> "$RESULTS_DIR/speed-test.json"
    fi
    cat >> "$RESULTS_DIR/speed-test.json" << EOF
      {
        "run": $((i + 1)),
        "tokens": ${token_counts[$i]},
        "duration": ${durations[$i]},
        "tok_per_sec": ${tok_per_sec_array[$i]}
      }
EOF
done

cat >> "$RESULTS_DIR/speed-test.json" << EOF

    ]
  }
}
EOF

# Print summary
echo -e "${GREEN}=== Results ===${NC}"
echo "Average speed: ${avg_tps} tok/s"
echo "Range: ${min_tps} - ${max_tps} tok/s"
echo ""
echo "Results saved to: $RESULTS_DIR/speed-test.json"

# Threshold check
THRESHOLD=20.0
is_above=$(echo "$avg_tps > $THRESHOLD" | bc)
if [ "$is_above" -eq 1 ]; then
    echo -e "${GREEN}✓ Above production threshold (${THRESHOLD} tok/s)${NC}"
    exit 0
else
    echo -e "${RED}✗ Below production threshold (${THRESHOLD} tok/s)${NC}"
    exit 1
fi
