#!/usr/bin/env bats
# Contract tests for scripts/speed-test.sh. No llama-server is needed:
# every case exits before any network call is made.

setup() {
    REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    SCRIPT="$REPO_ROOT/scripts/speed-test.sh"
}

@test "shellcheck passes on scripts/speed-test.sh" {
    run shellcheck "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "script is executable and has a bash shebang" {
    [ -x "$SCRIPT" ]
    run head -n1 "$SCRIPT"
    [ "$output" = "#!/bin/bash" ]
}

@test "--help prints usage and exits 0" {
    run bash "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    [[ "$output" == *"--model <path-to-gguf>"* ]]
}

@test "-h is an alias for --help" {
    run bash "$SCRIPT" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "no arguments: reports --model is required, prints usage, exits 1" {
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"--model is required"* ]]
    [[ "$output" == *"Usage:"* ]]
}

@test "missing model file exits 1 with a clear error" {
    run bash "$SCRIPT" --model "$BATS_TEST_TMPDIR/does-not-exist.gguf" --quant IQ4_XS
    [ "$status" -eq 1 ]
    [[ "$output" == *"Model file not found"* ]]
}

@test "unknown option exits 1 and names the option" {
    run bash "$SCRIPT" --bogus
    [ "$status" -eq 1 ]
    [[ "$output" == *"Unknown option: --bogus"* ]]
}

@test "failed runs do not create results/latest" {
    cd "$BATS_TEST_TMPDIR"
    run bash "$SCRIPT"
    [ "$status" -eq 1 ]
    [ ! -d "$BATS_TEST_TMPDIR/results" ]
}
