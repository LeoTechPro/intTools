# Конфигурации nginx (reverse proxy перед Apache)

Каталог содержит итоговые конфиги `nginx`, сформированные на основе действующих `apache2` vhost'ов.
Исключение: [`api.intdata.pro.conf`](/int/tools/data/configs/nginx/api.intdata.pro.conf) ведётся отдельно как host-level custom vhost для Supabase API и не генерируется из Apache.

### Назначение

- nginx принимает внешние HTTP/HTTPS-подключения (80/443), выполняет TLS-терминацию, безопасные заголовки и лимиты.
- Apache остаётся backend-сервером и слушает только на `127.0.0.1:8080` / `127.0.0.1:8443`.
- Конфиги генерируются скриптом `scripts/devops/generate_nginx_from_apache.py`, который подтягивает `ServerName`, `ServerAlias`, TLS-сертификаты и формирует пару `server {}` блоков (HTTP/HTTPS) для каждого vhost'а.

### Процесс обновления

1. Убедитесь, что `/etc/apache2/sites-available/` содержит актуальные конфиги.
2. Запустите генератор из корня репозитория:
   ```bash
   python3 scripts/devops/generate_nginx_from_apache.py
   ```
   Файлы появятся в `configs/nginx/generated/`.
3. Примените конфиги на хосте:
   ```bash
    sudo cp configs/nginx/generated/*.conf /etc/nginx/sites-available/
    sudo ln -sf /etc/nginx/sites-available/<vhost>.conf /etc/nginx/sites-enabled/<vhost>.conf
    sudo nginx -t
    sudo systemctl reload nginx
   ```
4. После выпуска/продления сертификатов `certbot` необходимо выполнить `systemctl reload nginx`.

### Дополнительно

- Общие сниппеты (`/etc/nginx/snippets/ssl-params.conf`) должны содержать жёсткие TLS-настройки и заголовки безопасности.
- Временное использование портов и сервисов фиксируйте в issue/worklog и сопровождайте machine-wide `lockctl` lease по изменяемым файлам. При оффлайне допускается запись в `AGENTS/issues.json` (`offline_queue`); после синхронизации с GitHub удалите черновик и отметьте время `Synced on <UTC>`. Постоянные изменения инфраструктуры отражайте в паспорте объектов `AGENTS/object_passport.yaml`.

### Перевыпуск сертификатов через snap `certbot`

1. Убедитесь, что установлен snap-пакет:
   ```bash
   sudo snap install core; sudo snap refresh core
   sudo snap install --classic certbot
   sudo ln -sf /snap/bin/certbot /usr/bin/certbot
   ```
2. Для каждого нового домена пропишите webroot (см. конфиги — `/var/www/<domain>`):
   ```bash
   sudo mkdir -p /var/www/bot.dev.intdata.pro
   sudo mkdir -p /var/www/id.intdata.pro
   sudo mkdir -p /var/www/id.test.intdata.pro
   sudo mkdir -p /var/www/nexus.intdata.pro
   sudo mkdir -p /var/www/sso.test.intdata.pro
   sudo mkdir -p /var/www/suite.intdata.pro
   sudo mkdir -p /var/www/chat.intdata.pro
   ```
3. Выпустите сертификаты (пример для одного домена, перечислите нужные `-d`; переменная `CERTBOT_EMAIL` обязательна). Проще всего использовать автоматизированный скрипт:
   ```bash
   export CERTBOT_EMAIL=ops@intdata.pro
   sudo scripts/devops/issue_intdata_certs.sh
   ```
   Либо вызвать вручную:
   ```bash
   sudo certbot certonly --webroot -w /var/www/bot.dev.intdata.pro -d bot.dev.intdata.pro
   sudo certbot certonly --webroot -w /var/www/id.intdata.pro -d id.intdata.pro
   sudo certbot certonly --webroot -w /var/www/id.test.intdata.pro -d id.test.intdata.pro
   sudo certbot certonly --webroot -w /var/www/nexus.intdata.pro -d nexus.intdata.pro
   sudo certbot certonly --webroot -w /var/www/sso.test.intdata.pro -d sso.test.intdata.pro
   sudo certbot certonly --webroot -w /var/www/suite.intdata.pro -d suite.intdata.pro
   sudo certbot certonly --webroot -w /var/www/chat.intdata.pro -d chat.intdata.pro -d www.chat.intdata.pro
   ```
4. После успешного выпуска перезагрузите nginx:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

При необходимости можно объединять несколько доменов в один сертификат (`-d` через пробел), однако удобно поддерживать отдельные связки, чтобы разграничить сроки продления.
