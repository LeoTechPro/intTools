#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

BASE_URL="${BASE_URL:-https://dev.punctb.pro}"
WORKSPACE_PASSWORD="${WORKSPACE_PASSWORD:-REDACTED}"

ADMIN_EMAIL="${ADMIN_EMAIL:-qa.admin02@punctb.test}"
SPECIALIST_EMAIL="${SPECIALIST_EMAIL:-demo.manager90@punctb.test}"
CLIENT_EMAIL="${CLIENT_EMAIL:-client.specialist02@punctb.test}"

normalize_base_url() {
  printf '%s' "${1%/}"
}

BASE_URL="$(normalize_base_url "${BASE_URL}")"

REPORT_PATH="${REPORT_PATH:-$ops_runtime_root/agent_browser_role_smoke_$(date -u +%Y%m%dT%H%M%SZ).json}"
REPORT_DIR="$(dirname "${REPORT_PATH}")"

mkdir -p "${REPORT_DIR}"

if ! command -v agent-browser >/dev/null 2>&1; then
  echo "SMOKE_FAIL: agent-browser is not installed"
  echo "Install:"
  echo "  npm install -g agent-browser"
  echo "  agent-browser install"
  exit 1
fi

read -r -d '' JS_PAGE_STATE <<'EOF' || true
(() => {
  const txt = (document.body.innerText || '').replace(/\s+/g, ' ').trim();
  const hasDialog = Array.from(document.querySelectorAll('[role=dialog],dialog')).some((el) =>
    /Личный кабинет/i.test(el.textContent || '')
  );
  return {
    url: location.href,
    path: location.pathname,
    title: document.title,
    deny_section: txt.includes('Доступ к разделу не подтверждён.'),
    deny_workspace: txt.includes('Доступ к рабочей зоне не подтверждён.'),
    not_found: txt.includes('Страница не найдена или доступ ограничен.'),
    lk_dialog: hasDialog,
    has_workspace_panel: !!document.querySelector('[aria-label="Панель рабочей области"]'),
    has_copy_link: txt.includes('Скопировать ссылку'),
    snippet: txt.slice(0, 260)
  };
})()
EOF

eval_result_json() {
  local session="$1"
  local script="$2"
  local raw
  raw="$(agent-browser eval "${script}" --session "${session}" --json)"
  node -e '
    const payload = JSON.parse(process.argv[1]);
    if (!payload.success) {
      console.error("SMOKE_FAIL: agent-browser eval returned unsuccessful payload");
      process.exit(2);
    }
    process.stdout.write(JSON.stringify(payload.data.result));
  ' "${raw}"
}

login_role() {
  local session="$1"
  local email="$2"
  local attempt

  agent-browser open "${BASE_URL}/lk" --session "${session}" >/dev/null || true
  agent-browser wait 1300 --session "${session}" >/dev/null || true

  for attempt in 1 2 3 4; do
    if agent-browser is visible '#email' --session "${session}" >/dev/null 2>&1; then
      agent-browser fill "#email" "${email}" --session "${session}" >/dev/null || true
      agent-browser fill "#password" "${WORKSPACE_PASSWORD}" --session "${session}" >/dev/null || true
      agent-browser click 'button[type="submit"]' --session "${session}" >/dev/null || true
      agent-browser wait 1800 --session "${session}" >/dev/null || true
    fi

    local state_after_login
    state_after_login="$(eval_result_json "${session}" "${JS_PAGE_STATE}")"
    local still_on_lk
    still_on_lk="$(node -e 'const s=JSON.parse(process.argv[1]); process.stdout.write((String(s.path || "").startsWith("/lk") || s.lk_dialog) ? "true" : "false");' "${state_after_login}")"
    if [[ "${still_on_lk}" == "false" ]]; then
      return 0
    fi

    agent-browser wait 700 --session "${session}" >/dev/null || true
  done
}

JSONL_FILE="$ops_runtime_root/agent_browser_role_smoke_results_$$.jsonl"
trap 'rm -f "${JSONL_FILE}"' EXIT

record_state() {
  local role="$1"
  local route="$2"
  local session="$3"
  local state_json
  state_json="$(eval_result_json "${session}" "${JS_PAGE_STATE}")"
  printf '{"role":"%s","route":"%s","state":%s}\n' "${role}" "${route}" "${state_json}" >> "${JSONL_FILE}"
}

probe_route() {
  local role="$1"
  local route="$2"
  local session="$3"

  agent-browser open "${BASE_URL}${route}" --session "${session}" >/dev/null || true
  agent-browser wait 1200 --session "${session}" >/dev/null || true
  record_state "${role}" "${route}" "${session}"
}

session_name() {
  local role="$1"
  printf 'ab-smoke-%s-%s-%s' "${role}" "$RANDOM" "$$"
}

run_role_matrix() {
  local role="$1"
  local email="$2"
  local session="$3"
  shift 3
  local routes=("$@")

  login_role "${session}" "${email}"
  record_state "${role}" "__login__" "${session}"

  local route
  for route in "${routes[@]}"; do
    probe_route "${role}" "${route}" "${session}"
  done

  agent-browser close --session "${session}" >/dev/null || true
}

run_role_matrix "admin" "${ADMIN_EMAIL}" "$(session_name admin)" "/" "/users" "/crm/revenue"
run_role_matrix "specialist" "${SPECIALIST_EMAIL}" "$(session_name specialist)" "/" "/diagnostics" "/users"
run_role_matrix "client" "${CLIENT_EMAIL}" "$(session_name client)" "/" "/diag" "/users" "/timeline"

set +e
node - "${JSONL_FILE}" "${REPORT_PATH}" "${BASE_URL}" "${ADMIN_EMAIL}" "${SPECIALIST_EMAIL}" "${CLIENT_EMAIL}" <<'NODE'
const fs = require("fs");

const [jsonlPath, reportPath, baseUrl, adminEmail, specialistEmail, clientEmail] = process.argv.slice(2);
const lines = fs.readFileSync(jsonlPath, "utf8").split("\n").filter(Boolean);
const records = lines.map((line) => JSON.parse(line));

const index = new Map();
for (const rec of records) {
  index.set(`${rec.role}:${rec.route}`, rec.state);
}

const checks = [];
const addCheck = (id, pass, details) => checks.push({ id, pass, details });
const get = (role, route) => index.get(`${role}:${route}`) || null;
const blocked = (state) => Boolean(state && (state.deny_section || state.deny_workspace || state.not_found));
const loginLike = (state) =>
  Boolean(state && (state.lk_dialog || String(state.path || "").startsWith("/lk")));
const allowed = (state) => Boolean(state) && !blocked(state) && !loginLike(state);

const adminLogin = get("admin", "__login__");
addCheck(
  "admin.login.redirected_from_lk",
  Boolean(adminLogin) && !adminLogin.lk_dialog && !String(adminLogin.path || "").startsWith("/lk"),
  adminLogin
);

const adminUsers = get("admin", "/users");
addCheck(
  "admin.users.allowed",
  allowed(adminUsers),
  adminUsers
);

const adminCrmRevenue = get("admin", "/crm/revenue");
addCheck(
  "admin.crm_revenue.allowed",
  allowed(adminCrmRevenue),
  adminCrmRevenue
);

const specialistLogin = get("specialist", "__login__");
addCheck(
  "specialist.login.no_lk_dialog",
  Boolean(specialistLogin) && !specialistLogin.lk_dialog && !String(specialistLogin.path || "").startsWith("/lk"),
  specialistLogin
);

const specialistDiagnostics = get("specialist", "/diagnostics");
addCheck(
  "specialist.diagnostics.allowed",
  allowed(specialistDiagnostics),
  specialistDiagnostics
);

const specialistUsers = get("specialist", "/users");
addCheck(
  "specialist.users.blocked",
  blocked(specialistUsers),
  specialistUsers
);

const clientLogin = get("client", "__login__");
addCheck(
  "client.login.no_lk_dialog",
  Boolean(clientLogin) && !clientLogin.lk_dialog && !String(clientLogin.path || "").startsWith("/lk"),
  clientLogin
);

const clientDiag = get("client", "/diag");
addCheck(
  "client.diag.allowed",
  allowed(clientDiag),
  clientDiag
);

const clientUsers = get("client", "/users");
addCheck(
  "client.users.blocked",
  blocked(clientUsers),
  clientUsers
);

const clientTimeline = get("client", "/timeline");
addCheck(
  "client.timeline.blocked",
  blocked(clientTimeline),
  clientTimeline
);

const failed = checks.filter((c) => !c.pass);
const report = {
  created_utc: new Date().toISOString(),
  tool: "agent-browser",
  base_url: baseUrl,
  accounts: {
    admin: adminEmail,
    specialist: specialistEmail,
    client: clientEmail,
  },
  checks,
  failed_check_ids: failed.map((item) => item.id),
  ok: failed.length === 0,
  total_checks: checks.length,
  total_failed: failed.length,
};

fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

if (failed.length > 0) {
  console.log("SMOKE_FAIL: agent-browser role smoke failed");
  for (const item of failed) {
    console.log(`- ${item.id}`);
  }
  console.log(`REPORT_PATH=${reportPath}`);
  process.exit(1);
}

console.log("SMOKE_OK: agent-browser role smoke passed");
console.log(`REPORT_PATH=${reportPath}`);
NODE
status=$?
set -e

exit "${status}"
