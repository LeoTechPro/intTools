#!/usr/bin/env bash
#
# Helper script to manage Keycloak + Kill Bill stack for /id.
# Requires: docker compose (v2), env file with required variables.
#
# Usage examples:
#   scripts/devops/setup_keycloak_killbill.sh start --env .env.dev
#   scripts/devops/setup_keycloak_killbill.sh stop
#   scripts/devops/setup_keycloak_killbill.sh logs keycloak
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ID_ROOT="/int/id"
COMPOSE_FILE="$ID_ROOT/docker-compose.yaml"
SCRIPT_NAME="$(basename "$0")"

command="${1:-}"
shift || true

ENV_FILE=""
DOCKER_COMPOSE_CMD="docker compose"
DEFAULT_PROFILES="keycloak"
CLEAR_THEME_CACHE=false
RUN_SELENIUM_SMOKE=false
SELENIUM_SMOKE_SCRIPT="$ID_ROOT/scripts/devops/run_selenium_smoke.sh"
REQUIRED_VARS=(
  ID_KEYCLOAK_DB_NAME
  ID_KEYCLOAK_DB_USER
  ID_KEYCLOAK_DB_PASSWORD
  ID_KEYCLOAK_ADMIN
  ID_KEYCLOAK_ADMIN_PASSWORD
  ID_KEYCLOAK_ADMIN_CLIENT_ID
  ID_KILLBILL_DB_NAME
  ID_KILLBILL_DB_USER
  ID_KILLBILL_DB_PASSWORD
  ID_KILLBILL_ADMIN_USER
  ID_KILLBILL_ADMIN_PASSWORD
  ID_KILLBILL_DEFAULT_API_KEY
  ID_KILLBILL_DEFAULT_API_SECRET
)

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME <command> [options]

Commands:
  start        Start Keycloak + Kill Bill stack (docker compose up -d)
  stop         Stop services (docker compose stop)
  restart      Restart services
  down         Stop and remove containers/volumes (BE CAREFUL)
  logs [svc]   Tail logs (default: all services)
  status       Show docker compose ps

Options:
  --env FILE   Path to env file (default: .env in repo root)
  --clear-theme-cache  Remove Keycloak static theme cache after up/restart
  --selenium-smoke     Run Selenium smoke (scripts/devops/run_selenium_smoke.sh)

Environment variables must define (see README):
  ID_KEYCLOAK_DB_NAME, ID_KEYCLOAK_DB_USER, ID_KEYCLOAK_DB_PASSWORD, ...

Examples:
  $SCRIPT_NAME start --env .env.dev
  $SCRIPT_NAME logs keycloak
EOF
}

EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_FILE="$2"
      shift 2
      ;;
    --clear-theme-cache)
      CLEAR_THEME_CACHE=true
      shift
      ;;
    --selenium-smoke)
      RUN_SELENIUM_SMOKE=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

EXTRA_ARGS=${EXTRA_ARGS:-()}

ensure_requirements() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is required" >&2
    exit 1
  fi
  if ! command -v docker compose >/dev/null 2>&1; then
    echo "ERROR: docker compose v2 is required" >&2
    exit 1
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl is required" >&2
    exit 1
  fi
}

load_env() {
  local env_path="$1"
  local default_env="$ID_ROOT/.env"
  local legacy_env="$ROOT_DIR/scripts/devops/id-stack.env"

  if [[ -z "$env_path" ]]; then
    if [[ -f "$default_env" ]]; then
      env_path="$default_env"
    elif [[ -f "$legacy_env" ]]; then
      env_path="$legacy_env"
    else
      env_path="$ROOT_DIR/.env"
    fi
  fi

  if [[ ! -f "$env_path" && -f "$legacy_env" ]]; then
    env_path="$legacy_env"
  fi

  if [[ -f "$env_path" ]]; then
    while IFS= read -r line; do
      [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
      if [[ "$line" == *"="* ]]; then
        local key="${line%%=*}"
        local value="${line#*=}"
        key="${key#${key%%[![:space:]]*}}"
        key="${key%${key##*[![:space:]]}}"
        value="${value#${value%%[![:space:]]*}}"
        value="${value%${value##*[![:space:]]}}"
        value="${value%$'\r'}"
        if [[ ${value:0:1} == '"' && ${value: -1} == '"' ]]; then
          value="${value:1:-1}"
        fi
        export "$key=$value"
      fi
    done < "$env_path"
    echo "Loaded env from $env_path"
  else
    echo "WARNING: env file $env_path not found; relying on shell environment."
  fi
}

ensure_requirements
load_env "$ENV_FILE"
if [[ -z "${COMPOSE_PROFILES:-}" ]]; then
  export COMPOSE_PROFILES="$DEFAULT_PROFILES"
fi

require_env() {
  local missing=()
  for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
      missing+=("$var")
    fi
  done
  if ((${#missing[@]} > 0)); then
    printf 'ERROR: env variables are required: %s\n' "${missing[*]}" >&2
    exit 1
  fi
}

wait_for_http() {
  local url="$1"
  local attempts="${2:-20}"
  local delay="${3:-3}"
  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$delay"
  done
  echo "WARNING: timed out waiting for $url" >&2
  return 1
}

bootstrap_keycloak() {
  local realm="${ID_KEYCLOAK_REALM:-intdata}"
  local base="${ID_KEYCLOAK_BOOTSTRAP_URL:-http://127.0.0.1:${ID_KEYCLOAK_HTTP_PORT_LEGACY:-8080}}"
  base="${base%/}"
  local admin_user="${ID_KEYCLOAK_ADMIN:-}"
  local admin_pass="${ID_KEYCLOAK_ADMIN_PASSWORD:-}"
  local admin_client="${ID_KEYCLOAK_ADMIN_CLIENT_ID:-admin-cli}"
  local admin_secret="${ID_KEYCLOAK_ADMIN_CLIENT_SECRET:-}"

  if [[ -z "$admin_user" || -z "$admin_pass" ]]; then
    echo "[bootstrap:keycloak] skipped (ID_KEYCLOAK_ADMIN/ID_KEYCLOAK_ADMIN_PASSWORD missing)"
    return
  fi

  wait_for_http "$base/realms/master/.well-known/openid-configuration" 30 2 || return

  local token_response
  token_response=$(curl -fsS \
    -d "grant_type=password" \
    -d "client_id=$admin_client" \
    ${admin_secret:+-d "client_secret=$admin_secret"} \
    -d "username=$admin_user" \
    -d "password=$admin_pass" \
    "$base/realms/master/protocol/openid-connect/token" 2>/dev/null) || {
      echo "[bootstrap:keycloak] failed to obtain admin token" >&2
      return
    }

  local token
  token=$(printf '%s' "$token_response" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))') || true
  if [[ -z "$token" ]]; then
    echo "[bootstrap:keycloak] access token is empty" >&2
    return
  fi

  local realm_status
  realm_status=$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $token" "$base/admin/realms/$realm")
  if [[ "$realm_status" == "404" ]]; then
    echo "[bootstrap:keycloak] creating realm $realm"
    curl -fsS -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" \
      -d "{\"realm\": \"$realm\", \"enabled\": true}" \
      "$base/admin/realms" || {
        echo "[bootstrap:keycloak] failed to create realm" >&2
        return
      }
  fi

  ensure_keycloak_clients "$token" "$base" "$realm"
  ensure_keycloak_realm_urls "$token" "$base" "$realm"
  ensure_keycloak_theme "$token" "$base" "$realm"
}

ensure_keycloak_clients() {
  python3 - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def env_first(prefixes, suffixes, default=None):
    for suffix in suffixes:
        for prefix in prefixes:
            name = f"{prefix}_{suffix}" if prefix else suffix
            value = os.getenv(name)
            if value:
                return value
    return default


def default_domain(env_names, fallback):
    for name in env_names:
        value = os.getenv(name)
        if value:
            return value.rstrip('/')
    return fallback.rstrip('/')


def build_spa(prefixes, *, default_id, domain, local_port=None, redirect_path='/auth/callback', name=None):
    client_id = env_first(prefixes, ['CLIENT_ID'], default_id)
    redirects = csv(env_first(prefixes, ['REDIRECT_URIS', 'REDIRECT_URI'], None))
    if not redirects:
        base_url = domain.rstrip('/')
        redirects = [f"{base_url}{redirect_path}"]
        if local_port:
            redirects.append(f"http://localhost:{local_port}{redirect_path}")
    origins = csv(env_first(prefixes, ['WEB_ORIGINS'], None))
    if not origins:
        base_url = domain.rstrip('/')
        origins = [base_url]
        if local_port:
            origins.append(f"http://localhost:{local_port}")
    logout = csv(env_first(prefixes, ['POST_LOGOUT_REDIRECT_URIS', 'POST_LOGOUT_REDIRECT_URI'], None))
    if not logout and redirects:
        logout = redirects[:1]
    payload = {
        'clientId': client_id,
        'name': name or client_id.replace('-', ' ').title(),
        'publicClient': True,
        'redirectUris': redirects,
        'webOrigins': origins,
        'attributes': {
            'pkce.code.challenge.method': 'S256',
            'post.logout.redirect.uris': ' '.join(logout or redirects),
        },
        'standardFlowEnabled': True,
        'implicitFlowEnabled': False,
        'directAccessGrantsEnabled': False,
        'serviceAccountsEnabled': False,
        'bearerOnly': False,
        'protocol': 'openid-connect',
        'authorizationServicesEnabled': False,
    }
    root_url = env_first(prefixes, ['ROOT_URL'], None)
    if root_url:
        payload['rootUrl'] = root_url.rstrip('/')
    return {'client_id': client_id, 'payload': payload, 'secret': '', 'summary': name or client_id}


def build_confidential(prefixes, *, default_id, default_redirects=None, default_origins=None,
                       name=None, default_secret='', service_account=False, code_flow=True):
    client_id = env_first(prefixes, ['CLIENT_ID'], default_id)
    secret = env_first(prefixes, ['CLIENT_SECRET', 'SECRET'], default_secret)
    redirects = csv(env_first(prefixes, ['REDIRECT_URIS', 'REDIRECT_URI'], None))
    if not redirects and default_redirects is not None:
        redirects = list(default_redirects)
    origins = csv(env_first(prefixes, ['WEB_ORIGINS'], None))
    if not origins and default_origins is not None:
        origins = list(default_origins)
    if not origins:
        origins = ['+']
    logout = csv(env_first(prefixes, ['POST_LOGOUT_REDIRECT_URIS', 'POST_LOGOUT_REDIRECT_URI'], None))
    if not logout and redirects:
        logout = redirects[:1]
    payload = {
        'clientId': client_id,
        'name': name or client_id.replace('-', ' ').title(),
        'publicClient': False,
        'redirectUris': redirects,
        'webOrigins': origins,
        'serviceAccountsEnabled': service_account,
        'standardFlowEnabled': bool(redirects) if code_flow else False,
        'directAccessGrantsEnabled': False,
        'implicitFlowEnabled': False,
        'bearerOnly': False,
        'protocol': 'openid-connect',
        'authorizationServicesEnabled': False,
    }
    if logout:
        payload.setdefault('attributes', {})['post.logout.redirect.uris'] = ' '.join(logout)
    root_url = env_first(prefixes, ['ROOT_URL'], None)
    if root_url:
        payload['rootUrl'] = root_url.rstrip('/')
    return {'client_id': client_id, 'payload': payload, 'secret': secret or '', 'summary': name or client_id, 'service_account': service_account}


realm = os.getenv('ID_KEYCLOAK_REALM', 'intdata')
admin_user = os.getenv('ID_KEYCLOAK_ADMIN')
admin_pass = os.getenv('ID_KEYCLOAK_ADMIN_PASSWORD')
admin_client = os.getenv('ID_KEYCLOAK_ADMIN_CLIENT_ID', 'admin-cli')
if not admin_user or not admin_pass:
    print('[bootstrap:keycloak] admin credentials missing (ID_KEYCLOAK_ADMIN[_PASSWORD])', file=sys.stderr)
    sys.exit(1)

port = os.getenv('ID_KEYCLOAK_HTTP_PORT_LEGACY', '8080')
base = f"http://127.0.0.1:{port}"

session = urllib.request.build_opener()

token_req = urllib.request.Request(
    urllib.parse.urljoin(base, '/realms/master/protocol/openid-connect/token'),
    data=urllib.parse.urlencode({
        'grant_type': 'password',
        'client_id': admin_client,
        'username': admin_user,
        'password': admin_pass,
    }).encode(),
    method='POST',
    headers={'Content-Type': 'application/x-www-form-urlencoded'},
)

try:
    with session.open(token_req, timeout=15) as resp:
        token_data = json.load(resp)
        access_token = token_data['access_token']
except urllib.error.HTTPError as exc:
    msg = exc.read().decode(errors='ignore')
    print(f'[bootstrap:keycloak] failed to obtain admin token: {exc.code} {msg}', file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f'[bootstrap:keycloak] failed to obtain admin token: {exc}', file=sys.stderr)
    sys.exit(1)

auth_headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
}

entries = []
nexus_domain = default_domain(['PUBLIC_URL'], 'https://dev.intdata.pro')
crm_domain = default_domain(['CRM_PUBLIC_URL'], 'https://crm.dev.intdata.pro')
bridge_domain = default_domain(['BRIDGE_PUBLIC_URL'], 'https://bridge.dev.intdata.pro')
suite_domain = default_domain(['SUITE_PUBLIC_URL'], 'https://suite.dev.intdata.pro')
id_admin_domain = default_domain(['ID_ADMIN_PUBLIC_URL'], 'https://id.dev.intdata.pro/admin')
bot_domain = default_domain(['BOT_PUBLIC_URL'], 'https://bot.dev.intdata.pro')
erp_domain = default_domain(['ERP_PUBLIC_URL', 'ODOO_PUBLIC_URL'], 'https://erp.intdata.pro')
erpnext_domain = default_domain(['ERPNEXT_PUBLIC_URL', 'ERP_DEV_PUBLIC_URL'], 'https://erp.dev.intdata.pro')

entries.append(build_confidential(['NEXUS_SSO', 'KEYCLOAK'], default_id='nexus-web',
                                   default_redirects=[f"{nexus_domain.rstrip('/')}/auth/callback"],
                                   default_origins=[nexus_domain.rstrip('/'), 'http://localhost:5801'],
                                   name='IntData Nexus Web'))
entries.append(build_spa(['NEXUS_ADMIN_SSO'], default_id='nexus-admin',
                         domain=nexus_domain, local_port='5801', redirect_path='/admin/callback',
                         name='IntData Nexus Admin'))
entries.append(build_confidential(['NEXUS_API_SSO'], default_id='nexus-api',
                                   default_redirects=[],
                                   default_origins=['+'],
                                   service_account=True, code_flow=False,
                                   name='IntData Nexus API'))

entries.append(build_spa(['CRM_SSO'], default_id='crm-frontend',
                         domain=crm_domain, local_port='3001',
                         name='CRM Frontend'))
entries.append(build_spa(['CRM_ADMIN_SSO'], default_id='crm-admin',
                         domain=crm_domain, local_port='3001', redirect_path='/admin/callback',
                         name='CRM Admin'))
entries.append(build_confidential(['CRM_API_SSO'], default_id='crm-api',
                                   default_redirects=[],
                                   default_origins=['+'],
                                   service_account=True, code_flow=False,
                                   name='CRM API'))

entries.append(build_spa(['BRIDGE_SSO'], default_id='bridge-web',
                         domain=bridge_domain, local_port='8081',
                         name='Bridge Web'))
entries.append(build_spa(['BRIDGE_ADMIN_SSO'], default_id='bridge-admin',
                         domain=bridge_domain, local_port='8081', redirect_path='/admin/callback',
                         name='Bridge Admin'))
entries.append(build_confidential(['BRIDGE_API_SSO'], default_id='bridge-api',
                                   default_redirects=[],
                                   default_origins=['+'],
                                   service_account=True, code_flow=False,
                                   name='Bridge API'))

entries.append(build_spa(['SUITE_SSO'], default_id='suite-web',
                         domain=suite_domain, local_port='15850',
                         name='Suite Web'))
entries.append(build_spa(['SUITE_ADMIN_SSO'], default_id='suite-admin',
                         domain=suite_domain, local_port='15850', redirect_path='/admin/callback',
                         name='Suite Admin'))
entries.append(build_confidential(['SUITE_API_SSO'], default_id='suite-api',
                                   default_redirects=[],
                                   default_origins=['+'],
                                   service_account=True, code_flow=False,
                                   name='Suite API'))

entries.append(build_spa(['ID_ADMIN_SSO'], default_id='id-admin',
                         domain=id_admin_domain, local_port='15820',
                         name='Identity Admin'))
entries.append(build_confidential(['ID_API_SSO'], default_id='id-api',
                                   default_redirects=[],
                                   default_origins=['+'],
                                   service_account=True, code_flow=False,
                                   name='Identity API'))

entries.append(build_spa(['BOT_ADMIN_SSO'], default_id='bot-admin',
                         domain=bot_domain, local_port=None, redirect_path='/admin/callback',
                         name='Bot Admin'))
entries.append(build_confidential(['BOT_API_SSO'], default_id='bot-api',
                                   default_redirects=[],
                                   default_origins=['+'],
                                   service_account=True, code_flow=False,
                                   name='Bot API'))

entries.append(build_confidential(
    ['ODOO_SSO', 'ODOO_KEYCLOAK'],
    default_id='odoo-web',
    default_redirects=[
        f"{erp_domain.rstrip('/')}/auth_oauth/signin",
        "http://localhost:8069/auth_oauth/signin",
    ],
    default_origins=[
        erp_domain.rstrip('/'),
        "http://localhost:8069",
    ],
    name='Odoo ERP Web',
))
entries.append(build_confidential(
    ['ERPNEXT_SSO', 'ERPNEXT_KEYCLOAK'],
    default_id='erpnext-web',
    default_redirects=[
        f"{erpnext_domain.rstrip('/')}/api/method/frappe.integrations.oauth2_logins.complete_login",
        "http://localhost:7080/api/method/frappe.integrations.oauth2_logins.complete_login",
    ],
    default_origins=[
        erpnext_domain.rstrip('/'),
        "http://localhost:7080",
    ],
    name='ERPNext Web',
))

clients_endpoint = urllib.parse.urljoin(base, f'/admin/realms/{realm}/clients')

created = []
updated = []
errors = False


def request(method, url, headers=None, data=None, timeout=20):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    return session.open(req, timeout=timeout)


for entry in entries:
    client_id = entry['client_id']
    payload = entry['payload']
    payload_json = json.dumps(payload, separators=(',', ':')).encode()
    try:
        with request('GET', f'{clients_endpoint}?clientId={urllib.parse.quote(client_id)}', headers=auth_headers) as resp:
            existing = json.load(resp)
    except urllib.error.HTTPError as exc:
        msg = exc.read().decode(errors='ignore')
        print(f'[bootstrap:keycloak] failed to query client {client_id}: {exc.code} {msg}', file=sys.stderr)
        errors = True
        continue
    except Exception as exc:
        print(f'[bootstrap:keycloak] failed to query client {client_id}: {exc}', file=sys.stderr)
        errors = True
        continue

    client_uuid = existing[0]['id'] if existing else None
    action = 'updated'
    if client_uuid:
        payload['id'] = client_uuid
        try:
            with request('PUT', f'{clients_endpoint}/{client_uuid}', headers=auth_headers, data=payload_json):
                pass
        except urllib.error.HTTPError as exc:
            msg = exc.read().decode(errors='ignore')
            print(f'[bootstrap:keycloak] failed to update {client_id}: {exc.code} {msg}', file=sys.stderr)
            errors = True
            continue
        except Exception as exc:
            print(f'[bootstrap:keycloak] failed to update {client_id}: {exc}', file=sys.stderr)
            errors = True
            continue
        updated.append(client_id)
    else:
        try:
            with request('POST', clients_endpoint, headers=auth_headers, data=payload_json) as resp:
                location = resp.headers.get('Location')
                if location:
                    client_uuid = location.rsplit('/', 1)[-1]
        except urllib.error.HTTPError as exc:
            msg = exc.read().decode(errors='ignore')
            print(f'[bootstrap:keycloak] failed to create {client_id}: {exc.code} {msg}', file=sys.stderr)
            errors = True
            continue
        except Exception as exc:
            print(f'[bootstrap:keycloak] failed to create {client_id}: {exc}', file=sys.stderr)
            errors = True
            continue
        if not client_uuid:
            # fetch again to determine id
            with request('GET', f'{clients_endpoint}?clientId={urllib.parse.quote(client_id)}', headers=auth_headers) as resp:
                refreshed = json.load(resp)
                client_uuid = refreshed[0]['id'] if refreshed else None
        created.append(client_id)
        action = 'created'

    secret = entry.get('secret')
    if secret and client_uuid:
        try:
            with request('POST', f'{clients_endpoint}/{client_uuid}/client-secret', headers=auth_headers,
                         data=json.dumps({'value': secret}).encode()):
                pass
        except urllib.error.HTTPError as exc:
            msg = exc.read().decode(errors='ignore')
            print(f'[bootstrap:keycloak] failed to set secret for {client_id}: {exc.code} {msg}', file=sys.stderr)
            errors = True
        except Exception as exc:
            print(f'[bootstrap:keycloak] failed to set secret for {client_id}: {exc}', file=sys.stderr)
            errors = True

    print(f"[bootstrap:keycloak] ensured {entry['summary']} ({action})")

summary = {'created': created, 'updated': updated}
print(json.dumps(summary))
sys.exit(1 if errors else 0)
PY
  local rc=$?
  if ((rc != 0)); then
    echo "[bootstrap:keycloak] client provisioning finished with errors"
  fi
  return $rc
}

ensure_keycloak_realm_urls() {
  local token="$1"
  local base="$2"
  local realm="$3"

  TOKEN="$token" BASE_URL="$base" REALM="$realm" python3 - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ['TOKEN']
base = os.environ['BASE_URL'].rstrip('/')
realm = os.environ['REALM']

def norm(value):
    return value.rstrip('/') if isinstance(value, str) else value

host_url = os.getenv('ID_KEYCLOAK_HOSTNAME_URL')
if not host_url:
    hostname = os.getenv('ID_KEYCLOAK_HOSTNAME', 'sso.intdata.pro')
    if hostname.startswith('http://') or hostname.startswith('https://'):
        host_url = hostname
    else:
        host_url = f'https://{hostname}'
host_url = host_url.rstrip('/')

admin_host = os.getenv('ID_KEYCLOAK_HOSTNAME_ADMIN_URL', host_url).rstrip('/')
frontend_url = os.getenv('ID_KEYCLOAK_FRONTEND_URL', host_url).rstrip('/')
admin_console = os.getenv('ID_KEYCLOAK_ADMIN_URL', f'{admin_host}/admin/{realm}/console').rstrip('/')

headers = {'Authorization': f'Bearer {token}'}
opener = urllib.request.build_opener()

def request(method, path, data=None, content_type='application/json'):
    url = urllib.parse.urljoin(f'{base}/', path.lstrip('/'))
    hdrs = dict(headers)
    if data is not None:
        hdrs['Content-Type'] = content_type
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    return opener.open(req, timeout=20)

try:
    with request('GET', f'/admin/realms/{realm}') as resp:
        representation = json.load(resp)
except urllib.error.HTTPError as exc:
    msg = exc.read().decode(errors='ignore')
    print(f'[bootstrap:keycloak] failed to fetch realm {realm}: {exc.code} {msg}', file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f'[bootstrap:keycloak] failed to fetch realm {realm}: {exc}', file=sys.stderr)
    sys.exit(1)

attrs = representation.get('attributes')
if not isinstance(attrs, dict):
    attrs = {}
    representation['attributes'] = attrs

changed = False
if norm(attrs.get('frontendUrl')) != norm(frontend_url):
    attrs['frontendUrl'] = frontend_url
    changed = True

if norm(attrs.get('adminUrl')) != norm(admin_console):
    attrs['adminUrl'] = admin_console
    changed = True

if not changed:
    print(f'[bootstrap:keycloak] realm URLs already set to {frontend_url}')
    sys.exit(0)

payload = json.dumps(representation, separators=(',', ':')).encode()
try:
    with request('PUT', f'/admin/realms/{realm}', data=payload):
        pass
except urllib.error.HTTPError as exc:
    msg = exc.read().decode(errors='ignore')
    print(f'[bootstrap:keycloak] failed to update realm URLs: {exc.code} {msg}', file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f'[bootstrap:keycloak] failed to update realm URLs: {exc}', file=sys.stderr)
    sys.exit(1)

print(f'[bootstrap:keycloak] updated realm URLs to {frontend_url}')
PY
}

ensure_keycloak_theme() {
  local token="$1"
  local base="$2"
  local realm="$3"

  TOKEN="$token" BASE_URL="$base" REALM="$realm" python3 - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ['TOKEN']
base = os.environ['BASE_URL'].rstrip('/')
realm = os.environ['REALM']

login_theme = os.getenv('ID_KEYCLOAK_LOGIN_THEME', 'intdata').strip()
display_name = os.getenv('ID_KEYCLOAK_DISPLAY_NAME', 'intData SSO').strip()
display_html = os.getenv('ID_KEYCLOAK_DISPLAY_NAME_HTML', 'intData SSO').strip()

headers = {'Authorization': f'Bearer {token}'}
opener = urllib.request.build_opener()

def request(method, path, data=None, content_type='application/json'):
    url = urllib.parse.urljoin(f'{base}/', path.lstrip('/'))
    hdrs = dict(headers)
    if data is not None:
        hdrs['Content-Type'] = content_type
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    return opener.open(req, timeout=20)

try:
    with request('GET', f'/admin/realms/{realm}') as resp:
        representation = json.load(resp)
except urllib.error.HTTPError as exc:
    msg = exc.read().decode(errors='ignore')
    print(f'[bootstrap:keycloak] failed to fetch realm {realm} for theme update: {exc.code} {msg}', file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f'[bootstrap:keycloak] failed to fetch realm {realm} for theme update: {exc}', file=sys.stderr)
    sys.exit(1)

attrs = representation.get('attributes')
if not isinstance(attrs, dict):
    attrs = {}
    representation['attributes'] = attrs

changed = False
if login_theme and representation.get('loginTheme') != login_theme:
    representation['loginTheme'] = login_theme
    changed = True

if display_name and representation.get('displayName') != display_name:
    representation['displayName'] = display_name
    changed = True
if display_name and attrs.get('displayName') != display_name:
    attrs['displayName'] = display_name
    changed = True

if display_html and representation.get('displayNameHtml') != display_html:
    representation['displayNameHtml'] = display_html
    changed = True
if display_html and attrs.get('displayNameHtml') != display_html:
    attrs['displayNameHtml'] = display_html
    changed = True

if not changed:
    print(f'[bootstrap:keycloak] realm theme already set to {login_theme}')
    sys.exit(0)

payload = json.dumps(representation, separators=(',', ':')).encode()
try:
    with request('PUT', f'/admin/realms/{realm}', data=payload):
        pass
except urllib.error.HTTPError as exc:
    msg = exc.read().decode(errors='ignore')
    print(f'[bootstrap:keycloak] failed to apply theme {login_theme}: {exc.code} {msg}', file=sys.stderr)
    sys.exit(1)
except Exception as exc:
    print(f'[bootstrap:keycloak] failed to apply theme {login_theme}: {exc}', file=sys.stderr)
    sys.exit(1)

print(f'[bootstrap:keycloak] applied theme {login_theme} (display: {display_name})')
PY
}

bootstrap_killbill() {
  local base="http://127.0.0.1:${ID_KILLBILL_HTTP_PORT:-8081}"
  local admin_key="${ID_KILLBILL_ADMIN_USER:-}"
  local admin_secret="${ID_KILLBILL_ADMIN_PASSWORD:-}"
  local tenant_key="${ID_KILLBILL_DEFAULT_API_KEY:-}"
  local tenant_secret="${ID_KILLBILL_DEFAULT_API_SECRET:-}"
  local tenant_name="${ID_KILLBILL_TENANT_NAME:-}"

  if [[ -z "$admin_key" || -z "$admin_secret" ]]; then
    echo "[bootstrap:killbill] skipped (admin credentials missing)"
    return
  fi

  wait_for_http "$base/1.0/healthcheck" 40 3 || return

  echo "[bootstrap:killbill] ensuring tenant $tenant_key"
  local payload="{\"apiKey\": \"$tenant_key\", \"apiSecret\": \"$tenant_secret\"}"
  local tmpfile
  tmpfile=$(mktemp)
  local status
  status=$(curl -sS -o "$tmpfile" -w '%{http_code}' \
    -X POST "$base/1.0/kb/tenants" \
    -u "$admin_key:$admin_secret" \
    -H "X-Killbill-CreatedBy: devops" \
    -H "X-Killbill-Reason: bootstrap" \
    -H "X-Killbill-Comment: setup_keycloak_killbill.sh" \
    -H "Content-Type: application/json" \
    -d "$payload" || true)
  if [[ "$status" == "201" ]]; then
    rm -f "$tmpfile"
    echo "[bootstrap:killbill] tenant $tenant_key created"
    return
  fi
  if [[ "$status" == "409" ]]; then
    rm -f "$tmpfile"
    echo "[bootstrap:killbill] tenant $tenant_key already exists"
    return
  fi
  echo "[bootstrap:killbill] failed to ensure tenant (status $status): $(cat "$tmpfile")" >&2
  rm -f "$tmpfile"
}

bootstrap_stack() {
  if [[ "${ID_BOOTSTRAP_DISABLED:-0}" == "1" ]]; then
    echo "[bootstrap] skipped (ID_BOOTSTRAP_DISABLED=1)"
    return
  fi
  bootstrap_keycloak
  bootstrap_killbill
}

clear_keycloak_theme_cache() {
  local container="${ID_KEYCLOAK_CONTAINER_NAME:-id-keycloak}"
  local cache_path="${KEYCLOAK_THEME_CACHE_PATH:-/opt/keycloak/data/tmp/kc-gzip-cache}"
  local attempts=6
  local delay=2

  if [[ -z "$cache_path" || "$cache_path" == "/" ]]; then
    echo "[theme-cache] invalid cache path: '$cache_path'" >&2
    return 1
  fi

  for ((i = 1; i <= attempts; i++)); do
    if docker ps --format '{{.Names}}' | grep -Fxq "$container"; then
      if docker exec "$container" sh -c "rm -rf \"$cache_path\" && mkdir -p \"$cache_path\"" >/dev/null 2>&1; then
        echo "[theme-cache] cleared $cache_path on $container"
        return 0
      fi
      echo "[theme-cache] attempt $i/$attempts failed, retrying..." >&2
    else
      echo "[theme-cache] container $container not ready (attempt $i/$attempts)" >&2
    fi
    sleep "$delay"
  done

  echo "[theme-cache] failed to clear cache on $container" >&2
  return 1
}

run_selenium_smoke() {
  local script="$SELENIUM_SMOKE_SCRIPT"
  if [[ ! -f "$script" ]]; then
    echo "[selenium-smoke] script not found: $script" >&2
    return 1
  fi
  if ! bash "$script"; then
    echo "[selenium-smoke] smoke tests failed" >&2
    return 1
  fi
  return 0
}

generate_killbill_overrides() {
  local dir="$ROOT_DIR/scripts/devops/killbill.overrides"
  local target="$dir/killbill.properties"
  local shiro_target="$dir/shiro.ini"

  mkdir -p "$dir"

  cat >"$target"<<EOF
org.killbill.server.db.provider=postgresql
org.killbill.server.jdbc.url=jdbc:postgresql://killbill-db:5432/${ID_KILLBILL_DB_NAME}
org.killbill.server.jdbc.user=${ID_KILLBILL_DB_USER}
org.killbill.server.jdbc.password=${ID_KILLBILL_DB_PASSWORD}

org.killbill.billing.util.security.shiroSecurityManager.adminUsername=${ID_KILLBILL_ADMIN_USER}
org.killbill.billing.util.security.shiroSecurityManager.adminPassword=${ID_KILLBILL_ADMIN_PASSWORD}
org.killbill.billing.util.security.shiroSecurityManager.apiKey=${ID_KILLBILL_DEFAULT_API_KEY}
org.killbill.billing.util.security.shiroSecurityManager.apiSecret=${ID_KILLBILL_DEFAULT_API_SECRET}

org.killbill.notificationq.inMemory=true
org.killbill.mail.disabled=true
EOF

  chmod 644 "$target"

  cat >"$shiro_target"<<EOF
[users]
${ID_KILLBILL_ADMIN_USER} = ${ID_KILLBILL_ADMIN_PASSWORD}, root

[roles]
root = *:*
EOF

  chmod 644 "$shiro_target"
}

case "$command" in
  start)
    require_env
    generate_killbill_overrides
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    if [[ "$CLEAR_THEME_CACHE" == true ]]; then
      if ! clear_keycloak_theme_cache; then
        echo "[theme-cache] warning: unable to clear cache" >&2
      fi
    fi
    bootstrap_stack
    if [[ "$RUN_SELENIUM_SMOKE" == true ]]; then
      if ! run_selenium_smoke; then
        echo "[selenium-smoke] warning: smoke finished with errors" >&2
      fi
    fi
    ;;
  stop)
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" stop
    ;;
  restart)
    require_env
    generate_killbill_overrides
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" up -d --force-recreate
    if [[ "$CLEAR_THEME_CACHE" == true ]]; then
      if ! clear_keycloak_theme_cache; then
        echo "[theme-cache] warning: unable to clear cache" >&2
      fi
    fi
    bootstrap_stack
    if [[ "$RUN_SELENIUM_SMOKE" == true ]]; then
      if ! run_selenium_smoke; then
        echo "[selenium-smoke] warning: smoke finished with errors" >&2
      fi
    fi
    ;;
  down)
    read -rp "This will stop and remove containers/volumes. Continue? [y/N] " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
      $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" down
    else
      echo "Aborted."
    fi
    ;;
  logs)
    svc="${EXTRA_ARGS[0]:-}"
    if [[ -n "$svc" ]]; then
      $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs -f "$svc"
    else
      $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" logs -f
    fi
    ;;
  status|ps)
    $DOCKER_COMPOSE_CMD -f "$COMPOSE_FILE" ps
    ;;
  ""|--help|-h)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage
    exit 1
    ;;
esac
