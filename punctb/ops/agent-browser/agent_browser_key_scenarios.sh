#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$(cd "$script_dir/../lib" && pwd)/common.sh"

BASE_URL="${BASE_URL:-https://dev.punctb.pro}"
WORKSPACE_PASSWORD="${WORKSPACE_PASSWORD:-<SECRET>}"

ADMIN_EMAIL="${ADMIN_EMAIL:-admin.demo@punctb.test}"
SPECIALIST_EMAIL="${SPECIALIST_EMAIL:-specialist.demo@punctb.test}"
CLIENT_EMAIL="${CLIENT_EMAIL:-client.demo@punctb.test}"

PUBLIC_CLIENT_FIRST_NAME="${PUBLIC_CLIENT_FIRST_NAME:-Тестовый}"
PUBLIC_CLIENT_FAMILY_NAME="${PUBLIC_CLIENT_FAMILY_NAME:-Клиент}"
PUBLIC_CLIENT_PHONE="${PUBLIC_CLIENT_PHONE:-+7 900 000 00 00}"
PUBLIC_CLIENT_EMAIL="${PUBLIC_CLIENT_EMAIL:-public.demo@punctb.test}"

normalize_base_url() {
  printf '%s' "${1%/}"
}

BASE_URL="$(normalize_base_url "${BASE_URL}")"

REPORT_PATH="${REPORT_PATH:-$ops_runtime_root/agent_browser_key_scenarios_$(date -u +%Y%m%dT%H%M%SZ).json}"
REPORT_DIR="$(dirname "${REPORT_PATH}")"
mkdir -p "${REPORT_DIR}" "$ops_runtime_root"

CHECKS_JSONL="$ops_runtime_root/agent_browser_key_scenarios_results_$$.jsonl"
trap 'rm -f "${CHECKS_JSONL}"' EXIT

if ! command -v agent-browser >/dev/null 2>&1; then
  echo "SCENARIOS_FAIL: agent-browser is not installed"
  echo "Install: npm install -g agent-browser && agent-browser install"
  exit 1
fi

safe_eval() {
  local session="$1"
  local script="$2"
  local raw

  raw="$(agent-browser eval "${script}" --session "${session}" --json 2>/dev/null || true)"

  node -e '
    const raw = process.argv[1] || "";
    let payload = null;
    try {
      payload = JSON.parse(raw);
    } catch {
      process.stdout.write(JSON.stringify({ __error: "eval_parse_failed", raw }));
      process.exit(0);
    }

    if (!payload.success) {
      process.stdout.write(JSON.stringify({ __error: payload.error || "eval_failed" }));
      process.exit(0);
    }

    process.stdout.write(JSON.stringify(payload.data?.result ?? {}));
  ' "${raw}"
}

safe_console() {
  local session="$1"
  local raw

  raw="$(agent-browser console --session "${session}" --json 2>/dev/null || true)"

  node -e '
    const raw = process.argv[1] || "";
    try {
      const payload = JSON.parse(raw);
      process.stdout.write(JSON.stringify(payload.data ?? { __error: payload.error || "console_failed" }));
    } catch {
      process.stdout.write(JSON.stringify({ __error: "console_parse_failed", raw }));
    }
  ' "${raw}"
}

record_check() {
  local id="$1"
  local pass="$2"
  local details_json="$3"
  printf '{"id":"%s","pass":%s,"details":%s}\n' "${id}" "${pass}" "${details_json}" >> "${CHECKS_JSONL}"
}

login_workspace() {
  local session="$1"
  local email="$2"

  agent-browser open "${BASE_URL}/lk" --session "${session}" >/dev/null || true
  agent-browser wait 1500 --session "${session}" >/dev/null || true

  local has_email_form="false"
  local i
  for i in 1 2 3 4; do
    if agent-browser is visible '#email' --session "${session}" >/dev/null 2>&1; then
      has_email_form="true"
      break
    fi
    agent-browser wait 700 --session "${session}" >/dev/null || true
  done

  if [[ "${has_email_form}" == "true" ]]; then
    agent-browser fill '#email' "${email}" --session "${session}" >/dev/null || true
    agent-browser fill '#password' "${WORKSPACE_PASSWORD}" --session "${session}" >/dev/null || true
    agent-browser click 'button[type="submit"]' --session "${session}" >/dev/null || true
    agent-browser wait 2400 --session "${session}" >/dev/null || true
  fi

  safe_eval "${session}" '(() => ({
    path: location.pathname,
    url: location.href,
    title: document.title,
    text: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 320)
  }))()'
}

session_name() {
  local prefix="$1"
  printf 'ab-key-%s-%s-%s' "${prefix}" "$RANDOM" "$$"
}

PUBLIC_LINK=""

# 1) Specialist scenarios
spec_session="$(session_name specialist)"
spec_login_state="$(login_workspace "${spec_session}" "${SPECIALIST_EMAIL}")"
spec_login_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = !String(s.path||"").startsWith("/lk") && !String(s.text||"").includes("500 Internal Server Error"); process.stdout.write(ok ? "true" : "false");' "${spec_login_state}")"
record_check "specialist.login" "${spec_login_pass}" "${spec_login_state}"

agent-browser open "${BASE_URL}/demo.manager90/diagnostics" --session "${spec_session}" >/dev/null || true
agent-browser wait 1700 --session "${spec_session}" >/dev/null || true
spec_diag_state="$(safe_eval "${spec_session}" '(() => {
  const text = (document.body.innerText || "").replace(/\s+/g, " ").trim();
  const match = text.match(/https:\/\/punctb\.pro\/diag\/43-professions\?[^\s]+/i);
  return {
    path: location.pathname,
    url: location.href,
    has_copy_link: /Скопировать ссылку/i.test(text),
    public_43_link: match ? match[0] : null,
    text: text.slice(0, 380)
  };
})()')"
PUBLIC_LINK="$(node -e 'const s=JSON.parse(process.argv[1]); process.stdout.write(String(s.public_43_link || ""));' "${spec_diag_state}")"
spec_diag_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = Boolean(s.has_copy_link && s.public_43_link); process.stdout.write(ok ? "true" : "false");' "${spec_diag_state}")"
record_check "specialist.assign_diagnostics_link" "${spec_diag_pass}" "${spec_diag_state}"

agent-browser open "${BASE_URL}/demo.manager90/results" --session "${spec_session}" >/dev/null || true
agent-browser wait 1500 --session "${spec_session}" >/dev/null || true
spec_results_state="$(safe_eval "${spec_session}" '(() => {
  const text = (document.body.innerText || "").replace(/\s+/g, " ").trim();
  return {
    path: location.pathname,
    url: location.href,
    has_results_page: /Результат/i.test(document.title || "") || /Результат/i.test(text),
    has_public_result_link: /Скопировать публичную ссылку/i.test(text),
    text: text.slice(0, 360)
  };
})()')"
spec_results_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = Boolean(s.has_results_page); process.stdout.write(ok ? "true" : "false");' "${spec_results_state}")"
record_check "specialist.work_with_results" "${spec_results_pass}" "${spec_results_state}"

agent-browser open "${BASE_URL}/clients" --session "${spec_session}" >/dev/null || true
agent-browser wait 1500 --session "${spec_session}" >/dev/null || true
spec_clients_state="$(safe_eval "${spec_session}" '(() => {
  const text = (document.body.innerText || "").replace(/\s+/g, " ").trim();
  const hasAdd = Array.from(document.querySelectorAll("button")).some((b) => /^Добавить$/i.test((b.textContent || "").trim()));
  return {
    path: location.pathname,
    url: location.href,
    has_add_client_button: hasAdd,
    has_clients_table: /КЛИЕНТ/i.test(text) || /Клиенты/i.test(document.title || ""),
    text: text.slice(0, 360)
  };
})()')"
spec_clients_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = Boolean(s.has_add_client_button && s.has_clients_table); process.stdout.write(ok ? "true" : "false");' "${spec_clients_state}")"
record_check "specialist.work_with_clients" "${spec_clients_pass}" "${spec_clients_state}"

agent-browser open "${BASE_URL}/conclusions/add" --session "${spec_session}" >/dev/null || true
agent-browser wait 1500 --session "${spec_session}" >/dev/null || true
spec_conclusion_state="$(safe_eval "${spec_session}" '(() => {
  const text = (document.body.innerText || "").replace(/\s+/g, " ").trim();
  return {
    path: location.pathname,
    url: location.href,
    has_conclusion_form: /Заключение для участника программы/i.test(text),
    has_next_button: Array.from(document.querySelectorAll("button")).some((b) => /Далее/i.test((b.textContent || "").trim())),
    text: text.slice(0, 360)
  };
})()')"
spec_conclusion_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = Boolean(s.has_conclusion_form && s.has_next_button); process.stdout.write(ok ? "true" : "false");' "${spec_conclusion_state}")"
record_check "specialist.issue_conclusion" "${spec_conclusion_pass}" "${spec_conclusion_state}"

agent-browser close --session "${spec_session}" >/dev/null || true

# 2) Public new-client diagnostic scenario
if [[ -z "${PUBLIC_LINK}" ]]; then
  record_check "client.public_new.link_available" "false" '{"reason":"public_link_not_found_from_specialist_diagnostics"}'
  record_check "client.public_new.registration_without_backend_error" "false" '{"reason":"public_link_not_found_from_specialist_diagnostics"}'
  record_check "client.public_new.no_blocker_signature_detected" "false" '{"reason":"public_link_not_found_from_specialist_diagnostics"}'
else
  record_check "client.public_new.link_available" "true" "$(node -e 'process.stdout.write(JSON.stringify({ public_link: process.argv[1] }));' "${PUBLIC_LINK}")"

  public_session="$(session_name public)"
  agent-browser open "${PUBLIC_LINK}" --session "${public_session}" >/dev/null || true
  agent-browser wait 2200 --session "${public_session}" >/dev/null || true

  agent-browser fill '#form-first-name' "${PUBLIC_CLIENT_FIRST_NAME}" --session "${public_session}" >/dev/null || true
  agent-browser fill '#form-family-name' "${PUBLIC_CLIENT_FAMILY_NAME}" --session "${public_session}" >/dev/null || true
  agent-browser fill '#form-phone' "${PUBLIC_CLIENT_PHONE}" --session "${public_session}" >/dev/null || true
  agent-browser fill '#form-email' "${PUBLIC_CLIENT_EMAIL}" --session "${public_session}" >/dev/null || true
  agent-browser check '#policy' --session "${public_session}" >/dev/null || true

  public_click_state="$(safe_eval "${public_session}" '(() => {
    const nextButtons = Array.from(document.querySelectorAll("button")).filter((b) => /Далее/i.test((b.textContent || "").trim()) && !b.disabled);
    const next = nextButtons.length > 0 ? nextButtons[nextButtons.length - 1] : null;
    if (next) {
      next.click();
      return { clicked_next: true };
    }
    return { clicked_next: false };
  })()')"
  agent-browser wait 4200 --session "${public_session}" >/dev/null || true

  public_state="$(safe_eval "${public_session}" '(() => ({
    path: location.pathname,
    url: location.href,
    text: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 550)
  }))()')"

  public_console="$(safe_console "${public_session}")"

  public_flow_details="$(node - <<'NODE' "${public_state}" "${public_console}" "${public_click_state}"
const [stateRaw, consoleRaw, clickRaw] = process.argv.slice(2);
const state = JSON.parse(stateRaw || '{}');
const consoleData = JSON.parse(consoleRaw || '{}');
const click = JSON.parse(clickRaw || '{}');

const messages = Array.isArray(consoleData.messages) ? consoleData.messages.map((m) => String(m.text || '')) : [];
const rlsError = messages.find((text) => /column "rls" of relation "users" does not exist/i.test(text)) || null;
const has400 = messages.some((text) => /status of 400/i.test(text));
const stateText = String(state.text || '');
const stayedOnRegStep = /После заполнения анкеты вам откроется доступ/i.test(stateText);
const passwordCreatedNotice = /Для входа в личный кабинет клиента создан пароль/i.test(stateText);
const diagnosticIntroVisible =
  /«43 ПРОФЕССИИ»/i.test(stateText)
  || /В ЭТОМ ТЕСТЕ ВАМ БУДЕТ ПРЕДЛОЖЕНО 43 РАЗА СДЕЛАТЬ ВЫБОР/i.test(stateText);

const progressed =
  !stayedOnRegStep
  && (
    String(state.path || '') !== '/diag/43-professions'
    || passwordCreatedNotice
    || diagnosticIntroVisible
  );
const noBackendError = !rlsError && !has400;
const blockerEvidence = Boolean(rlsError || has400 || stayedOnRegStep);

const details = {
  clicked_next: Boolean(click.clicked_next),
  state,
  console_messages: messages.slice(0, 6),
  blocker_signature: rlsError,
  has_http_400_console: has400,
  stayed_on_registration_step: stayedOnRegStep,
  password_created_notice: passwordCreatedNotice,
  diagnostic_intro_visible: diagnosticIntroVisible,
  progressed_after_registration: progressed,
  no_backend_error: noBackendError,
  blocker_evidence: blockerEvidence,
};

process.stdout.write(JSON.stringify(details));
NODE
)"

  public_flow_pass="$(node -e 'const d=JSON.parse(process.argv[1]); const ok = Boolean(d.clicked_next && d.progressed_after_registration && d.no_backend_error); process.stdout.write(ok ? "true" : "false");' "${public_flow_details}")"
  record_check "client.public_new.registration_without_backend_error" "${public_flow_pass}" "${public_flow_details}"

  public_blocker_absent="$(node -e 'const d=JSON.parse(process.argv[1]); process.stdout.write(d.blocker_evidence ? "false" : "true");' "${public_flow_details}")"
  record_check "client.public_new.no_blocker_signature_detected" "${public_blocker_absent}" "${public_flow_details}"

  agent-browser close --session "${public_session}" >/dev/null || true
fi

# 3) Authorized client full diagnostic completion
client_session="$(session_name client)"
client_login_state="$(login_workspace "${client_session}" "${CLIENT_EMAIL}")"
client_login_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = !String(s.path||"").startsWith("/lk") && !String(s.text||"").includes("500 Internal Server Error"); process.stdout.write(ok ? "true" : "false");' "${client_login_state}")"
record_check "client.authorized.login" "${client_login_pass}" "${client_login_state}"

agent-browser open "${BASE_URL}/diag/43-professions" --session "${client_session}" >/dev/null || true
agent-browser wait 1500 --session "${client_session}" >/dev/null || true
safe_eval "${client_session}" '(() => {
  const btn = Array.from(document.querySelectorAll("button")).find((b) => /Начать тестирование/i.test((b.textContent || "").trim()) && !b.disabled);
  if (btn) {
    btn.click();
    return { start_clicked: true };
  }
  return { start_clicked: false };
})()' >/dev/null
agent-browser wait 800 --session "${client_session}" >/dev/null || true

client_max_progress=0
client_reached_final="false"
client_loop_iterations=0

for i in $(seq 1 95); do
  step_state="$(safe_eval "${client_session}" '(() => {
    const text = (document.body.innerText || "").replace(/\s+/g, " ").trim();
    const progressMatch = text.match(/\b(\d+)\s*\/\s*43\b/);
    const progress = progressMatch ? Number(progressMatch[1]) : null;

    if (/Запишите 3 профессии/i.test(text)) {
      return { stage: "final", progress, text: text.slice(0, 220) };
    }

    const radios = Array.from(document.querySelectorAll("input[name=\"diagnostic-43-choice\"]")).filter((radio) => !radio.disabled);
    if (radios.length > 0) {
      const target = radios[0];
      target.click();
      target.dispatchEvent(new Event("input", { bubbles: true }));
      target.dispatchEvent(new Event("change", { bubbles: true }));
    }

    const nextButtons = Array.from(document.querySelectorAll("button")).filter((b) => /Далее/i.test((b.textContent || "").trim()) && !b.disabled);
    const next = nextButtons.length > 0 ? nextButtons[nextButtons.length - 1] : null;
    if (next) {
      next.click();
      return { stage: "next", progress };
    }

    return { stage: "idle", progress, text: text.slice(0, 160) };
  })()')"

  client_loop_iterations=$((client_loop_iterations + 1))
  step_progress="$(node -e 'const s=JSON.parse(process.argv[1]); const p=s.progress; process.stdout.write(Number.isFinite(p) ? String(p) : "");' "${step_state}")"
  if [[ "${step_progress}" =~ ^[0-9]+$ ]] && (( step_progress > client_max_progress )); then
    client_max_progress="${step_progress}"
  fi

  step_stage="$(node -e 'const s=JSON.parse(process.argv[1]); process.stdout.write(String(s.stage || ""));' "${step_state}")"
  if [[ "${step_stage}" == "final" ]]; then
    client_reached_final="true"
    break
  fi

  agent-browser wait 240 --session "${client_session}" >/dev/null || true
done

if [[ "${client_reached_final}" == "true" ]]; then
  agent-browser fill '#question-open-input' 'Психолог, Аналитик, Предприниматель' --session "${client_session}" >/dev/null || true
  agent-browser wait 650 --session "${client_session}" >/dev/null || true
fi

client_finish_state="$(safe_eval "${client_session}" '(() => {
  const btn = Array.from(document.querySelectorAll("button")).find((b) => /Завершить/i.test((b.textContent || "").trim()));
  if (!btn) {
    return { finish_present: false, finish_enabled: false, clicked: false };
  }
  const enabled = !btn.disabled;
  if (enabled) {
    btn.click();
  }
  return { finish_present: true, finish_enabled: enabled, clicked: enabled };
})()')"

agent-browser wait 2600 --session "${client_session}" >/dev/null || true
client_final_state="$(safe_eval "${client_session}" '(() => ({
  path: location.pathname,
  url: location.href,
  text: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 420)
}))()')"

client_full_details="$(node - <<'NODE' "${client_finish_state}" "${client_final_state}" "${client_max_progress}" "${client_reached_final}" "${client_loop_iterations}"
const [finishRaw, finalRaw, maxProgressRaw, reachedFinalRaw, loopRaw] = process.argv.slice(2);
const finishState = JSON.parse(finishRaw || '{}');
const finalState = JSON.parse(finalRaw || '{}');
const maxProgress = Number(maxProgressRaw || '0');
const reachedFinal = reachedFinalRaw === 'true';
const loopIterations = Number(loopRaw || '0');

const success = reachedFinal && maxProgress >= 43 && String(finalState.path || '') === '/diag/testing-end' && /Спасибо за ваши ответы/i.test(String(finalState.text || ''));

process.stdout.write(JSON.stringify({
  success,
  reached_final_screen: reachedFinal,
  max_progress: maxProgress,
  loop_iterations: loopIterations,
  finish_state: finishState,
  final_state: finalState,
}));
NODE
)"

client_full_pass="$(node -e 'const d=JSON.parse(process.argv[1]); process.stdout.write(d.success ? "true" : "false");' "${client_full_details}")"
record_check "client.authorized.full_diag_completion" "${client_full_pass}" "${client_full_details}"

agent-browser close --session "${client_session}" >/dev/null || true

# 4) Admin scenarios
admin_session="$(session_name admin)"
admin_login_state="$(login_workspace "${admin_session}" "${ADMIN_EMAIL}")"
admin_login_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = !String(s.path||"").startsWith("/lk") && !String(s.text||"").includes("500 Internal Server Error"); process.stdout.write(ok ? "true" : "false");' "${admin_login_state}")"
record_check "admin.login" "${admin_login_pass}" "${admin_login_state}"

agent-browser open "${BASE_URL}/users" --session "${admin_session}" >/dev/null || true
agent-browser wait 1700 --session "${admin_session}" >/dev/null || true
admin_users_state="$(safe_eval "${admin_session}" '(() => {
  const text = (document.body.innerText || "").replace(/\s+/g, " ").trim();
  const hasAdd = Array.from(document.querySelectorAll("button")).some((b) => /^Добавить$/i.test((b.textContent || "").trim()));
  const roleControls = Array.from(document.querySelectorAll("button")).filter(
    (b) => /▾/.test((b.textContent || "")) && /(Администратор|Менеджер заботы|Партн(?:ё|е)р|Франчайзи|Специалист|Не назнач)/i.test((b.textContent || ""))
  );
  return {
    path: location.pathname,
    url: location.href,
    has_add_button: hasAdd,
    role_control_count: roleControls.length,
    text: text.slice(0, 420)
  };
})()')"
admin_users_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = Boolean(s.has_add_button && Number(s.role_control_count || 0) > 0); process.stdout.write(ok ? "true" : "false");' "${admin_users_state}")"
record_check "admin.users_page_access" "${admin_users_pass}" "${admin_users_state}"

safe_eval "${admin_session}" '(() => {
  const add = Array.from(document.querySelectorAll("button")).find((b) => /^Добавить$/i.test((b.textContent || "").trim()));
  if (add) {
    add.click();
    return { add_clicked: true };
  }
  return { add_clicked: false };
})()' >/dev/null
agent-browser wait 1300 --session "${admin_session}" >/dev/null || true

admin_add_state="$(safe_eval "${admin_session}" '(() => {
  const roleSelect = document.querySelector("#create-user-role");
  const roleOptions = roleSelect
    ? Array.from(roleSelect.options)
        .map((o) => ({
          value: (o.value || "").trim(),
          label: (o.textContent || "").trim(),
        }))
        .filter((option) => option.label)
    : [];
  return {
    path: location.pathname,
    url: location.href,
    has_create_form: Boolean(document.querySelector("#create-user-name") && document.querySelector("#create-user-email") && roleSelect),
    has_specialist_subrole_option: roleOptions.some(
      (option) => /^(partner|franchisee)$/i.test(option.value) || /партн(?:ё|е)р|франчайзи|специалист/i.test(option.label)
    ),
    has_not_assigned_option: roleOptions.some((option) => /не назнач/i.test(option.label)),
    role_options: roleOptions.slice(0, 20),
    text: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 420)
  };
})()')"

admin_create_spec_pass="$(node -e 'const s=JSON.parse(process.argv[1]); const ok = Boolean(s.has_create_form && s.has_specialist_subrole_option); process.stdout.write(ok ? "true" : "false");' "${admin_add_state}")"
record_check "admin.create_specialist_form_available" "${admin_create_spec_pass}" "${admin_add_state}"

admin_grant_revoke_pass="$(node -e 'const users=JSON.parse(process.argv[1]); const add=JSON.parse(process.argv[2]); const ok = Number(users.role_control_count || 0) > 0 && (Boolean(add.has_specialist_subrole_option) || Boolean(add.has_not_assigned_option)); process.stdout.write(ok ? "true" : "false");' "${admin_users_state}" "${admin_add_state}")"
admin_grant_revoke_details="$(node -e 'const users=JSON.parse(process.argv[1]); const add=JSON.parse(process.argv[2]); process.stdout.write(JSON.stringify({role_control_count: users.role_control_count || 0, has_specialist_subrole_option: Boolean(add.has_specialist_subrole_option), has_not_assigned_option: Boolean(add.has_not_assigned_option), source_users: users, source_add_modal: add}));' "${admin_users_state}" "${admin_add_state}")"
record_check "admin.grant_revoke_controls_available" "${admin_grant_revoke_pass}" "${admin_grant_revoke_details}"

agent-browser close --session "${admin_session}" >/dev/null || true

set +e
node - <<'NODE' "${CHECKS_JSONL}" "${REPORT_PATH}" "${BASE_URL}" "${ADMIN_EMAIL}" "${SPECIALIST_EMAIL}" "${CLIENT_EMAIL}" "${PUBLIC_CLIENT_EMAIL}" "${PUBLIC_LINK}"
const fs = require('fs');

const [checksPath, reportPath, baseUrl, adminEmail, specialistEmail, clientEmail, publicClientEmail, publicLink] = process.argv.slice(2);
const lines = fs.readFileSync(checksPath, 'utf8').split('\n').filter(Boolean);
const checks = lines.map((line) => JSON.parse(line));
const failed = checks.filter((item) => !item.pass);

const report = {
  created_utc: new Date().toISOString(),
  tool: 'agent-browser',
  suite: 'key_scenarios',
  base_url: baseUrl,
  accounts: {
    admin: adminEmail,
    specialist: specialistEmail,
    client: clientEmail,
    public_new_client_email: publicClientEmail,
  },
  specialist_public_link_43: publicLink || null,
  checks,
  failed_check_ids: failed.map((item) => item.id),
  ok: failed.length === 0,
  total_checks: checks.length,
  total_failed: failed.length,
};

fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');

if (failed.length > 0) {
  console.log('SCENARIOS_FAIL: key scenarios have failures');
  for (const item of failed) {
    console.log(`- ${item.id}`);
  }
  console.log(`REPORT_PATH=${reportPath}`);
  process.exit(1);
}

console.log('SCENARIOS_OK: key scenarios passed');
console.log(`REPORT_PATH=${reportPath}`);
NODE
status=$?
set -e

exit $status
