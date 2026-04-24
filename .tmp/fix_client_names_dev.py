import subprocess
remote = r'''sudo -u postgres psql -d intdata -v ON_ERROR_STOP=1 <<'SQL'
WITH normalized AS (
  SELECT
    user_id,
    first_name,
    family_name,
    patronymic,
    regexp_split_to_array(regexp_replace(btrim(COALESCE(first_name, '')), '\s+', ' ', 'g'), ' ') AS fio_parts,
    array_length(regexp_split_to_array(regexp_replace(btrim(COALESCE(first_name, '')), '\s+', ' ', 'g'), ' '), 1) AS fio_len
  FROM assess.clients
), parsed AS (
  SELECT
    user_id,
    CASE
      WHEN NULLIF(btrim(family_name), '') IS NOT NULL OR NULLIF(btrim(patronymic), '') IS NOT NULL THEN first_name
      WHEN fio_len = 3 AND lower(fio_parts[2]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[1]
      WHEN fio_len = 3 AND lower(fio_parts[1]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[3]
      WHEN fio_len = 2 AND lower(fio_parts[2]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[1]
      WHEN fio_len = 2 AND lower(fio_parts[1]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[2]
      WHEN fio_len = 2 THEN fio_parts[2]
      ELSE first_name
    END AS parsed_first_name,
    CASE
      WHEN NULLIF(btrim(family_name), '') IS NOT NULL THEN family_name
      WHEN fio_len = 3 AND lower(fio_parts[2]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[3]
      WHEN fio_len = 3 AND lower(fio_parts[1]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[2]
      WHEN fio_len = 3 THEN fio_parts[1]
      WHEN fio_len = 2 AND lower(fio_parts[2]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN NULL
      WHEN fio_len = 2 AND lower(fio_parts[1]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN NULL
      WHEN fio_len = 2 THEN fio_parts[1]
      ELSE family_name
    END AS parsed_family_name,
    CASE
      WHEN NULLIF(btrim(patronymic), '') IS NOT NULL THEN patronymic
      WHEN fio_len = 3 AND lower(fio_parts[2]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[2]
      WHEN fio_len = 3 AND lower(fio_parts[1]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[1]
      WHEN fio_len = 3 THEN fio_parts[3]
      WHEN fio_len = 2 AND lower(fio_parts[2]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[2]
      WHEN fio_len = 2 AND lower(fio_parts[1]) ~ '(ович|евич|вич|ич|овна|евна|ична|вна|чна|оглы|кызы)$' THEN fio_parts[1]
      ELSE patronymic
    END AS parsed_patronymic
  FROM normalized
)
UPDATE assess.clients c
SET first_name = NULLIF(btrim(p.parsed_first_name), ''),
    family_name = NULLIF(btrim(p.parsed_family_name), ''),
    patronymic = NULLIF(btrim(p.parsed_patronymic), ''),
    updated_at = now()
FROM parsed p
WHERE c.user_id = p.user_id
  AND (
    c.first_name IS DISTINCT FROM NULLIF(btrim(p.parsed_first_name), '') OR
    c.family_name IS DISTINCT FROM NULLIF(btrim(p.parsed_family_name), '') OR
    c.patronymic IS DISTINCT FROM NULLIF(btrim(p.parsed_patronymic), '')
  );

select count(*) from assess.clients where nullif(btrim(family_name),'') is not null;
select to_char(updated_at,'YYYY-MM-DD HH24:MI') || '|' || coalesce(first_name,'') || '|' || coalesce(family_name,'') || '|' || coalesce(patronymic,'') || '|' || coalesce(email,'') from assess.clients order by updated_at desc nulls last limit 15;
SQL'''
r = subprocess.run(['ssh','-o','BatchMode=yes','agents@vds.intdata.pro', remote], capture_output=True, text=True, encoding='utf-8', errors='replace')
print('RC=' + str(r.returncode))
print(r.stdout[:5000])
print(r.stderr[:1200])
