#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Resolve logical SSH target for /int transport layer.

Usage:
  int_ssh_host.sh --logical <dev-intdata|dev-codex|dev-openclaw|prod-leon> [--mode auto|tailnet|public]

Environment:
  INT_SSH_MODE=auto|tailnet|public
  INT_SSH_PROBE_TIMEOUT_SEC=4
  INT_SSH_TAILNET_SUFFIX=tailf0f164.ts.net
  INT_SSH_DEV_PUBLIC_HOST=vds.intdata.pro
  INT_SSH_PROD_PUBLIC_HOST=vds.punkt-b.pro
  INT_SSH_DEV_TAILNET_NODE=vds-intdata-pro
  INT_SSH_PROD_TAILNET_NODE=vds-punkt-b-pro
  INT_SSH_DEV_TAILNET_HOST (optional full host override)
  INT_SSH_PROD_TAILNET_HOST (optional full host override)

Output:
  USER@HOST (single line to stdout)
  selection details to stderr
USAGE
}

logical=""
mode="${INT_SSH_MODE:-auto}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --logical)
      logical="${2:-}"
      shift 2
      ;;
    --mode)
      mode="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "int_ssh_host.sh: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$logical" ]]; then
  echo "int_ssh_host.sh: --logical is required" >&2
  exit 2
fi

mode="$(echo "$mode" | tr '[:upper:]' '[:lower:]')"
if [[ "$mode" != "auto" && "$mode" != "tailnet" && "$mode" != "public" ]]; then
  mode="auto"
fi

timeout_sec="${INT_SSH_PROBE_TIMEOUT_SEC:-4}"
if ! [[ "$timeout_sec" =~ ^[0-9]+$ ]]; then
  timeout_sec=4
fi
if [[ "$timeout_sec" -lt 1 ]]; then
  timeout_sec=1
fi

tail_suffix="${INT_SSH_TAILNET_SUFFIX:-tailf0f164.ts.net}"

case "$logical" in
  dev-intdata)
    user="intdata"
    identity="${INT_SSH_DEV_INTDATA_KEY:-$HOME/.ssh/id_ed25519_vds_intdata_intdata}"
    public_host="${INT_SSH_DEV_PUBLIC_HOST:-vds.intdata.pro}"
    tail_node="${INT_SSH_DEV_TAILNET_NODE:-vds-intdata-pro}"
    tail_host="${INT_SSH_DEV_TAILNET_HOST:-$tail_node.$tail_suffix}"
    ;;
  dev-codex)
    user="codex"
    identity="${INT_SSH_DEV_CODEX_KEY:-$HOME/.ssh/id_ed25519_vds_intdata_codex}"
    public_host="${INT_SSH_DEV_PUBLIC_HOST:-vds.intdata.pro}"
    tail_node="${INT_SSH_DEV_TAILNET_NODE:-vds-intdata-pro}"
    tail_host="${INT_SSH_DEV_TAILNET_HOST:-$tail_node.$tail_suffix}"
    ;;
  dev-openclaw)
    user="openclaw"
    identity="${INT_SSH_DEV_OPENCLAW_KEY:-$HOME/.ssh/id_ed25519_vds_intdata_openclaw}"
    public_host="${INT_SSH_DEV_PUBLIC_HOST:-vds.intdata.pro}"
    tail_node="${INT_SSH_DEV_TAILNET_NODE:-vds-intdata-pro}"
    tail_host="${INT_SSH_DEV_TAILNET_HOST:-$tail_node.$tail_suffix}"
    ;;
  prod-leon)
    user="leon"
    identity="${INT_SSH_PROD_LEON_KEY:-$HOME/.ssh/id_ed25519}"
    public_host="${INT_SSH_PROD_PUBLIC_HOST:-vds.punkt-b.pro}"
    tail_node="${INT_SSH_PROD_TAILNET_NODE:-vds-punkt-b-pro}"
    tail_host="${INT_SSH_PROD_TAILNET_HOST:-$tail_node.$tail_suffix}"
    ;;
  *)
    echo "int_ssh_host.sh: unsupported logical host: $logical" >&2
    exit 2
    ;;
esac

probe_tailnet() {
  ssh \
    -o BatchMode=yes \
    -o ConnectTimeout="$timeout_sec" \
    -o StrictHostKeyChecking=accept-new \
    -i "$identity" \
    "$user@$tail_host" "true" >/dev/null 2>&1
}

selected_transport="public"
selected_host="$public_host"
probe_ok="n/a"
fallback_used="false"

if [[ "$mode" == "tailnet" ]]; then
  selected_transport="tailnet"
  selected_host="$tail_host"
elif [[ "$mode" == "public" ]]; then
  selected_transport="public"
  selected_host="$public_host"
else
  if probe_tailnet; then
    selected_transport="tailnet"
    selected_host="$tail_host"
    probe_ok="true"
  else
    selected_transport="public"
    selected_host="$public_host"
    probe_ok="false"
    fallback_used="true"
  fi
fi

echo "$user@$selected_host"
echo "int_ssh_host.sh: logical=$logical mode=$mode transport=$selected_transport probe_ok=$probe_ok fallback=$fallback_used host=$selected_host" >&2
