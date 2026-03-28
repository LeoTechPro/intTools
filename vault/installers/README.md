# Vault Installers / Sanitize

## `vault_sanitize.py`

Idempotent cleanup script that keeps Obsidian vault content in `/2brain` (or `D:\Yandex.Disk\2brain`) and moves operational artifacts into `int/brain` runtime and canonical installer paths in `int/tools`.

### Local

```powershell
python d:\int\tools\vault\installers\vault_sanitize.py --dry-run
python d:\int\tools\vault\installers\vault_sanitize.py --apply
```

### VDS

```bash
python3 /int/tools/vault/installers/vault_sanitize.py --vault-root /2brain --brain-root /int/brain --tools-root /int/tools --dry-run
python3 /int/tools/vault/installers/vault_sanitize.py --vault-root /2brain --brain-root /int/brain --tools-root /int/tools --apply
```

### Whitelist profile

```powershell
python d:\int\tools\vault\installers\vault_sanitize.py --profile strict --dry-run
python d:\int\tools\vault\installers\vault_sanitize.py --profile strict --apply
```

`--enforce-whitelist` is kept as a deprecated alias for `--profile strict`.

## `runtime_vault_gc.py`

Archives and resets generated runtime vault artifacts.

```powershell
python d:\int\tools\vault\installers\runtime_vault_gc.py --dry-run
python d:\int\tools\vault\installers\runtime_vault_gc.py --apply
```

VDS:

```bash
python3 /int/tools/vault/installers/runtime_vault_gc.py --brain-root /int/brain --archive-root /int/.tmp --dry-run
python3 /int/tools/vault/installers/runtime_vault_gc.py --brain-root /int/brain --archive-root /int/.tmp --apply
```
