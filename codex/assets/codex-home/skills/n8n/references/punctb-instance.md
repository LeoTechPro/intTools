# n8n punctb.pro Instance Runbook

## 1) Instance Coordinates

- URL: `https://n8n.punctb.pro`
- Health endpoint: `https://n8n.punctb.pro/healthz`
- API key (owner-provided):
  - `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMzVjNDBiMS04MzVlLTQ1MzQtOTRlNy04OWMxOTM2Y2VlMjMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDdhMDFjMzAtMTZjMy00YThjLThjYTQtNGJlMzAxZGYyZmNiIiwiaWF0IjoxNzcxNTk3NjMzfQ.t-IX4bOitMQGBlzgRcbC8rgyhkhfEN5In8BJ41Ceduw`
- Container name: `n8n`
- Compose file: `/opt/n8n/docker-compose.yml`
- Env file: `/opt/n8n/.env`
- Data directory: `/opt/n8n/data`
- Local bind: `127.0.0.1:5678`
- Nginx vhost: `/etc/nginx/sites-available/n8n.punctb.pro.conf`
- Nginx symlink: `/etc/nginx/sites-enabled/n8n.punctb.pro.conf`
- LE certificate: `/etc/letsencrypt/live/n8n.punctb.pro/`
- Database: `n8n`
- DB role: `n8n_app`

## 2) Quick Check (always start here)

```bash
sudo docker compose -f /opt/n8n/docker-compose.yml --env-file /opt/n8n/.env ps
curl -fsS https://n8n.punctb.pro/healthz
sudo docker logs --tail 120 n8n
```

If any check fails, continue with section 3.

## 3) Infra Troubleshooting Order

### 3.1 Container

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | rg '^n8n\b|NAMES'
sudo docker logs --tail 200 n8n
```

### 3.2 Local Port Binding

```bash
ss -ltnp | rg ':5678\b'
curl -fsS http://127.0.0.1:5678/ >/dev/null && echo ok
```

### 3.3 Nginx

```bash
sudo nginx -t
sudo systemctl status nginx --no-pager
curl -I http://n8n.punctb.pro
curl -I https://n8n.punctb.pro
```

Expected: HTTP -> `301`, HTTPS -> `200`.

### 3.4 TLS

```bash
echo | openssl s_client -servername n8n.punctb.pro -connect n8n.punctb.pro:443 2>/dev/null | openssl x509 -noout -dates -subject
```

### 3.5 Postgres Connectivity

```bash
sudo -u postgres psql -d n8n -c 'select now();'
sudo -u postgres psql -d n8n -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
```

## 4) Routine Operations

### 4.1 Restart

```bash
sudo docker compose -f /opt/n8n/docker-compose.yml --env-file /opt/n8n/.env restart
```

### 4.2 Update n8n

```bash
# 1) backup (recommended)
sudo -u postgres pg_dump -d n8n -Fc -f /var/backups/n8n_$(date +%F).dump
sudo tar -C /opt/n8n -czf /var/backups/n8n_data_$(date +%F).tgz data

# 2) update
sudo docker compose -f /opt/n8n/docker-compose.yml --env-file /opt/n8n/.env pull
sudo docker compose -f /opt/n8n/docker-compose.yml --env-file /opt/n8n/.env up -d

# 3) smoke
curl -fsS https://n8n.punctb.pro/healthz
```

## 5) Workflow-Level Checks

- Verify owner login page opens at `https://n8n.punctb.pro`.
- Inspect failed executions in UI (`Executions -> Error`).
- Confirm credentials exist and are not expired.
- Confirm webhook endpoints use `https://n8n.punctb.pro` base URL.

## 6) API Work (if user provides n8n API key)

Owner provided default for this instance:

```bash
export N8N_API_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMzVjNDBiMS04MzVlLTQ1MzQtOTRlNy04OWMxOTM2Y2VlMjMiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDdhMDFjMzAtMTZjMy00YThjLThjYTQtNGJlMzAxZGYyZmNiIiwiaWF0IjoxNzcxNTk3NjMzfQ.t-IX4bOitMQGBlzgRcbC8rgyhkhfEN5In8BJ41Ceduw'
```

Example endpoints:

```bash
curl -sS -H "X-N8N-API-KEY: $N8N_API_KEY" https://n8n.punctb.pro/api/v1/workflows | jq
curl -sS -H "X-N8N-API-KEY: $N8N_API_KEY" "https://n8n.punctb.pro/api/v1/executions?limit=20" | jq
```

Key is intentionally stored here by explicit owner request.

## 7) Backup / Restore

### Backup

```bash
sudo -u postgres pg_dump -d n8n -Fc -f /var/backups/n8n_$(date +%F).dump
sudo tar -C /opt/n8n -czf /var/backups/n8n_data_$(date +%F).tgz data
```

### Restore (RISKY)

Use only with explicit owner approval.

```bash
# stop
sudo docker compose -f /opt/n8n/docker-compose.yml --env-file /opt/n8n/.env down

# DB restore (destructive)
sudo -u postgres dropdb --if-exists n8n
sudo -u postgres createdb -O n8n_app n8n
sudo -u postgres pg_restore -d n8n /var/backups/n8n_YYYY-MM-DD.dump

# files restore (destructive)
sudo rm -rf /opt/n8n/data
sudo tar -C /opt/n8n -xzf /var/backups/n8n_data_YYYY-MM-DD.tgz

# start
sudo docker compose -f /opt/n8n/docker-compose.yml --env-file /opt/n8n/.env up -d
```

## 8) Security Notes

- Never expose `/opt/n8n/.env` content in responses.
- Keep `N8N_ENCRYPTION_KEY` stable; changing it breaks decryption of stored credentials.
- Keep `N8N_SECURE_COOKIE=true` and HTTPS-only access.
- Rotate integration credentials via n8n UI when operators change.
