# IntAssess Browser Matrix

## Canonical role profiles

- `assess-client-diagnostics` -> `http://127.0.0.1:8081/`
- `assess-specialist-v1` -> `http://127.0.0.1:8080/`
- `assess-specialist-v2` -> `http://127.0.0.1:8080/v2/`
- `assess-specialist-admin` -> `http://127.0.0.1:8080/v2/`
- `assess-specialist-restricted` -> `http://127.0.0.1:8080/v2/`

## Семантика ролей

- `client-diagnostics` — anonymous diagnostics flow на `8081`
- `specialist-v1` — authenticated specialist без `v2`/admin capability
- `specialist-v2` — authenticated specialist с `v2` access
- `specialist-admin` — admin/elevated specialist contour
- `specialist-restricted` — authenticated specialist для deny/limited access proof

## Expected acceptance evidence

- `client-diagnostics`: ingress `/`, `testing-end`, `policy`, `v2` placeholders
- `specialist-v1`: login/profile/results/conclusion smoke на `v1`
- `specialist-v2`: `v2` root/login/profile/results smoke
- `specialist-admin`: admin-only surfaces или elevated navigation proof
- `specialist-restricted`: подтверждённый deny/limited behavior без ложного admin access

## Blockers

- role profile не стартует или не сохраняет login-state
- local host `8080`/`8081` не отвечает своим meta marker
- нужный role-path не воспроизводим без owner Chrome fallback
- отсутствуют snapshot/console/network evidence для handoff

## Session bootstrap policy

- первый bootstrap выполняется вручную в visible mode
- логин делается один раз на profile
- пароли не сохраняются в git и не автоматизируются через scripts
- reset одного profile не затрагивает остальные role directories
