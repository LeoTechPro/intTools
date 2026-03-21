#!/usr/bin/env bash
set -Eeuo pipefail

# Этот скрипт перевыпускает сертификаты Let's Encrypt для доменов IntData.
# Требования:
#   - Запускается на фронтовом узле под root (или с sudo);
#   - Установлен snap-пакет certbot (/snap/bin/certbot);
#   - nginx обслуживает /.well-known/acme-challenge/ из /var/www/<domain>.
#
# Примеры использования:
#   sudo ./scripts/devops/issue_intdata_certs.sh
#   WEBROOT_BASE=/srv/www sudo ./scripts/devops/issue_intdata_certs.sh chat.intdata.pro
#
# При успешном выпуске выполняется `nginx -t` и перезагрузка nginx.

WEBROOT_BASE=${WEBROOT_BASE:-/var/www}
CERTBOT_BIN=${CERTBOT_BIN:-/snap/bin/certbot}
NGINX_CTL=${NGINX_CTL:-/usr/sbin/nginx}
SYSTEMCTL_BIN=${SYSTEMCTL_BIN:-/bin/systemctl}

NEEDED_DOMAINS=(
  bot.dev.intdata.pro
  id.intdata.pro
  id.test.intdata.pro
  nexus.intdata.pro
  sso.test.intdata.pro
  suite.intdata.pro
  chat.intdata.pro
)

usage() {
  cat <<'USAGE'
Использование: issue_intdata_certs.sh [домен ...]

Без аргументов обрабатываются все преднастроенные домены. Можно перечислить
часть доменов через пробел.
USAGE
}

if [[ ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

ensure_prereqs() {
  if [[ $(id -u) -ne 0 ]]; then
    echo "Ошибка: запустите скрипт от root (sudo)." >&2
    exit 1
  fi
  if [[ ! -x ${CERTBOT_BIN} ]]; then
    echo "Ошибка: не найден certbot (${CERTBOT_BIN}). Установите snap certbot." >&2
    exit 1
  fi
  if [[ ! -x ${NGINX_CTL} ]]; then
    echo "Ошибка: не найден nginx (${NGINX_CTL})." >&2
    exit 1
  fi
  if [[ ! -x ${SYSTEMCTL_BIN} ]]; then
    echo "Ошибка: не найден systemctl (${SYSTEMCTL_BIN})." >&2
    exit 1
  fi
}

issue_cert() {
  local domain=$1
  shift || true
  local alt=("$@")
  local webroot="${WEBROOT_BASE}/${domain}"
  mkdir -p "${webroot}"

  local args=(--non-interactive --agree-tos --email "${CERTBOT_EMAIL:?Задайте CERTBOT_EMAIL}" certonly --webroot -w "${webroot}" -d "${domain}")
  for san in "${alt[@]}"; do
    args+=(-d "${san}")
  done

  echo ">>> Выпуск сертификата для ${domain} (webroot ${webroot})"
  "${CERTBOT_BIN}" "${args[@]}"
}

reload_nginx() {
  echo ">>> Проверка конфигурации nginx"
  "${NGINX_CTL}" -t
  echo ">>> Перезагрузка nginx"
  "${SYSTEMCTL_BIN}" reload nginx
}

main() {
  ensure_prereqs
  local domains=("${@:-${NEEDED_DOMAINS[@]}}")

  for domain in "${domains[@]}"; do
    case "${domain}" in
      bot.dev.intdata.pro)
        issue_cert "${domain}"
        ;;
      id.intdata.pro)
        issue_cert "${domain}"
        ;;
      id.test.intdata.pro)
        issue_cert "${domain}"
        ;;
      nexus.intdata.pro)
        issue_cert "${domain}"
        ;;
      sso.test.intdata.pro)
        issue_cert "${domain}"
        ;;
      suite.intdata.pro)
        issue_cert "${domain}"
        ;;
      chat.intdata.pro)
        issue_cert "${domain}" "www.chat.intdata.pro"
        ;;
      *)
        echo "Предупреждение: домен ${domain} не известен скрипту, пропуск." >&2
        ;;
    esac
  done

  reload_nginx
  echo ">>> Готово."
}

main "$@"
