#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

MODE="${MODE:-handoff}"
REPORT_PREFIX="${REPORT_PREFIX:-$ops_runtime_root/agent_browser_gate_$(date -u +%Y%m%dT%H%M%SZ)}"
SUMMARY_PATH="${SUMMARY_PATH:-${REPORT_PREFIX}_summary.json}"

mkdir -p "$(dirname "${SUMMARY_PATH}")"

run_role_smoke() {
  local report_path="$1"
  REPORT_PATH="${report_path}" bash "$ops_home/ops/agent-browser/agent_browser_role_smoke.sh"
}

run_key_scenarios() {
  local report_path="$1"
  REPORT_PATH="${report_path}" bash "$ops_home/ops/agent-browser/agent_browser_key_scenarios.sh"
}

role_status="skipped"
role_report=""
key_status="skipped"
key_report=""

case "${MODE}" in
  handoff)
    role_report="${REPORT_PREFIX}_role_smoke.json"
    if run_role_smoke "${role_report}"; then
      role_status="passed"
    else
      role_status="failed"
      node - <<'NODE' "${SUMMARY_PATH}" "${MODE}" "${role_status}" "${role_report}" "${key_status}" "${key_report}"
const fs = require('fs');
const [summaryPath, mode, roleStatus, roleReport, keyStatus, keyReport] = process.argv.slice(2);
const summary = {
  created_utc: new Date().toISOString(),
  mode,
  role_smoke: { status: roleStatus, report_path: roleReport || null },
  key_scenarios: { status: keyStatus, report_path: keyReport || null },
  ok: false,
};
fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
NODE
      echo "GATE_FAIL: mode=${MODE}"
      echo "SUMMARY_PATH=${SUMMARY_PATH}"
      exit 1
    fi
    ;;
  full|release|nightly)
    role_report="${REPORT_PREFIX}_role_smoke.json"
    key_report="${REPORT_PREFIX}_key_scenarios.json"

    if run_role_smoke "${role_report}"; then
      role_status="passed"
    else
      role_status="failed"
      node - <<'NODE' "${SUMMARY_PATH}" "${MODE}" "${role_status}" "${role_report}" "${key_status}" "${key_report}"
const fs = require('fs');
const [summaryPath, mode, roleStatus, roleReport, keyStatus, keyReport] = process.argv.slice(2);
const summary = {
  created_utc: new Date().toISOString(),
  mode,
  role_smoke: { status: roleStatus, report_path: roleReport || null },
  key_scenarios: { status: keyStatus, report_path: keyReport || null },
  ok: roleStatus === 'passed' && keyStatus === 'passed',
};
fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
NODE
      echo "GATE_FAIL: mode=${MODE}"
      echo "SUMMARY_PATH=${SUMMARY_PATH}"
      exit 1
    fi

    if run_key_scenarios "${key_report}"; then
      key_status="passed"
    else
      key_status="failed"
      if [[ "${MODE}" == "nightly" && "${ALLOW_NIGHTLY_SOFT_FAIL:-0}" == "1" ]]; then
        :
      else
        node - <<'NODE' "${SUMMARY_PATH}" "${MODE}" "${role_status}" "${role_report}" "${key_status}" "${key_report}"
const fs = require('fs');
const [summaryPath, mode, roleStatus, roleReport, keyStatus, keyReport] = process.argv.slice(2);
const summary = {
  created_utc: new Date().toISOString(),
  mode,
  role_smoke: { status: roleStatus, report_path: roleReport || null },
  key_scenarios: { status: keyStatus, report_path: keyReport || null },
  ok: false,
};
fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
NODE
        echo "GATE_FAIL: mode=${MODE}"
        echo "SUMMARY_PATH=${SUMMARY_PATH}"
        exit 1
      fi
    fi
    ;;
  *)
    echo "GATE_FAIL: unknown MODE=${MODE}"
    echo "Supported: handoff | full | release | nightly"
    exit 2
    ;;
esac

node - <<'NODE' "${SUMMARY_PATH}" "${MODE}" "${role_status}" "${role_report}" "${key_status}" "${key_report}"
const fs = require('fs');
const [summaryPath, mode, roleStatus, roleReport, keyStatus, keyReport] = process.argv.slice(2);
const summary = {
  created_utc: new Date().toISOString(),
  mode,
  role_smoke: { status: roleStatus, report_path: roleReport || null },
  key_scenarios: { status: keyStatus, report_path: keyReport || null },
  ok: mode === 'handoff' ? roleStatus === 'passed' : roleStatus === 'passed' && keyStatus === 'passed',
};
fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
NODE

echo "GATE_OK: mode=${MODE}"
echo "SUMMARY_PATH=${SUMMARY_PATH}"
if [[ -n "${role_report}" ]]; then
  echo "ROLE_REPORT=${role_report}"
fi
if [[ -n "${key_report}" && "${key_status}" != "skipped" ]]; then
  echo "KEY_REPORT=${key_report}"
fi

exit 0
