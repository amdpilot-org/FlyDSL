#!/usr/bin/env bash

set -u

REPO_ROOT=/job/work/FlyDSL
PYTHON=/opt/venv/bin/python
export PYTHONPATH="/job/build-cache/flydsl-build/python_packages:/job/build-cache/python-deps"
export FLYDSL_RUNTIME_ENABLE_CACHE=0

RAW_DIR="${REPO_ROOT}/reports/j-bd24d07a80de/raw"
mkdir -p "${RAW_DIR}"

run_probe() {
    local name=$1
    local form=$2
    local flag=$3
    local flag_const=$4
    local expected=$5
    local expected_status=$6
    local log="${RAW_DIR}/${name}.log"
    echo "=== ${name}: form=${form} flag=${flag} flag_const=${flag_const} expected=${expected} expected_status=${expected_status} ==="
    timeout 30s "${PYTHON}" "${REPO_ROOT}/reports/j-bd24d07a80de/probe_early_return.py" \
        "${form}" --flag "${flag}" --flag-const "${flag_const}" --expected "${expected}" \
        >"${log}" 2>&1
    local status=$?
    cat "${log}"
    echo "EXIT_CODE=${status}"
    if [[ "${status}" -ne "${expected_status}" ]]; then
        echo "UNEXPECTED_STATUS name=${name} actual=${status} expected=${expected_status}"
        return 1
    fi
    return 0
}

status=0
run_probe baseline_no_return baseline_no_return 1 1 1 0 || status=1
run_probe top_level_return top_level_return 1 1 1 0 || status=1
run_probe top_level_value_return top_level_value_return 1 1 1 1 || status=1
run_probe dynamic_if_return_last dynamic_if_return_last 1 1 1 1 || status=1
run_probe dynamic_if_return_after dynamic_if_return_after 1 1 1 1 || status=1
run_probe dynamic_if_state_return dynamic_if_state_return 1 1 1 1 || status=1
run_probe for_return_after for_return_after 1 1 10 1 || status=1
run_probe while_return_after while_return_after 1 1 2 1 || status=1
run_probe nested_if_return_after nested_if_return_after 1 1 1 1 || status=1
run_probe constexpr_if_return_after_true constexpr_if_return_after 1 1 1 0 || status=1
run_probe constexpr_if_return_after_false constexpr_if_return_after 0 0 2 0 || status=1
run_probe constexpr_for_return_after constexpr_for_return_after 1 1 10 0 || status=1

exit "${status}"
