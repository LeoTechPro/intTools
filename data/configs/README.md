# intdata host configs

Этот каталог хранит внешний host-config слой для `intdata` и соседних family-сервисов.

## Что находится здесь

- apache/nginx/systemd/fail2ban/docker helper configs
- generated vhost templates и ops reference files

## Что не находится здесь

- canonical backend migrations/contracts/functions
- runtime-state и живые секреты

Если конфиг обслуживает хост, reverse proxy, systemd или внешний rollout path, его место здесь, а не в `/int/data`.
