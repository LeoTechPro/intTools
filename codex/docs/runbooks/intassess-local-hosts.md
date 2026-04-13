# IntAssess Local Hosts

## Canonical hosts

- `http://127.0.0.1:8080/` — `specialist`
- `http://127.0.0.1:8081/` — `client/diagnostics`

## Contract

- оба хоста считаются always-on local sign-off contour
- lifecycle управляется только через `pwsh -File D:/int/assess/scripts/devops/local_runtime.ps1`
- по завершении обычной задачи агенты не останавливают эти хосты
- обновления frontend подхватываются через `restart -Build specialist|client|all`

## Workflow

- старт already-built dist host-ов:
  - `pwsh -File D:/int/assess/scripts/devops/local_runtime.ps1 start`
- rebuild + controlled restart:
  - `pwsh -File D:/int/assess/scripts/devops/local_runtime.ps1 restart -Build specialist`
  - `pwsh -File D:/int/assess/scripts/devops/local_runtime.ps1 restart -Build client`
  - `pwsh -File D:/int/assess/scripts/devops/local_runtime.ps1 restart -Build all`
- статус:
  - `pwsh -File D:/int/assess/scripts/devops/local_runtime.ps1 status`
- manual stop only:
  - `pwsh -File D:/int/assess/scripts/devops/local_runtime.ps1 stop`

## Marker expectations

- specialist marker: `intassess-specialist-serve-dist`
- client marker: `intassess-client-serve-dist`
- meta endpoint path: `/__intassess/serve-dist-meta`

## Safety

- если порт занят чужим сервисом, takeover запрещён
- owned-process restart разрешён только для того же marker
- `check:dist` должен уметь использовать уже работающий owned host без финального stop
