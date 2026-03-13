-- Demo dataset for specialist demo.manager90@punctb.test
-- Creates ~10 clients with 4-5 diagnostic results each so the new React UI can be demonstrated.
-- Usage (adjust connection string as needed):
--   psql postgresql://supabase_admin:***@localhost:5432/punctbpro -f backend/scripts/seed_demo_manager90.sql

BEGIN;

-- Ensure diagnostics catalogue contains the legacy identifiers used by the diagnostics bundle.
WITH payload AS (
  SELECT *
  FROM jsonb_to_recordset(
    '[
      {"id":0,"slug":"43-professions","title":"43 Профессии"},
      {"id":2,"slug":"10-favorite-things","title":"10 Любимых дел (Взрослый)"},
      {"id":4,"slug":"perfect-job","title":"Идеальная работа (Взрослый)"},
      {"id":6,"slug":"my-needs","title":"Мои потребности (Взрослый)"},
      {"id":8,"slug":"antirating-of-professions","title":"Антирейтинг профессий (Взрослый)"},
      {"id":10,"slug":"interview","title":"Интервью (Для всех возрастов)"},
      {"id":12,"slug":"8-frames","title":"8 Кадров (Взрослый)"},
      {"id":13,"slug":"exploring-values","title":"Исследование ценностей"},
      {"id":15,"slug":"viability","title":"Диагностика жизнестойкости"},
      {"id":17,"slug":"im-at-work","title":"Я на работе"}
    ]'::jsonb
  ) AS t(id int, slug text, title text)
)
INSERT INTO app.diagnostics (id, slug, title, created_at, updated_at)
SELECT p.id, p.slug, p.title, now(), now()
FROM payload p
ON CONFLICT (id) DO UPDATE
  SET slug = EXCLUDED.slug,
      title = EXCLUDED.title,
      updated_at = now();

DO $$
DECLARE
  v_specialist_email constant text := 'demo.manager90@punctb.test';
  v_specialist_id uuid;
  v_clients jsonb := $_clients$[
    {
      "name": "Анна Карева",
      "email": "demo.client01@punctb.test",
      "phone": "+7 (999) 100-01-01",
      "contact_permission": true,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.64, "investigative": 0.52, "artistic": 0.71, "social": 0.58, "enterprising": 0.49, "conventional": 0.36}, "top_professions": ["UX-дизайнер", "Продуктовый аналитик", "Арт-директор"]}, "open_answer": "В ближайший год хочу усилить аналитическую команду и запустить новый курс."},
        {"id": 2, "payload": {"favorites": ["Писать статьи", "Работать с данными", "Наставничество", "Фотография", "Путешествия"], "energy_index": 0.83}, "open_answer": "Наибольший драйв дают проекты с ощутимым пользовательским эффектом."},
        {"id": 4, "payload": {"ideal_day": {"morning": "Созвон с командой", "day": "Проектирование новых функций", "evening": "Спортивная тренировка"}, "key_values": ["Гибкость", "Рост", "Командность"]}},
        {"id": 13, "payload": {"values": {"creativity": 36, "independence": 31, "status": 18, "altruism": 27, "stability": 22}, "priority": "creativity"}},
        {"id": 17, "payload": {"satisfaction": {"team": 4.6, "tasks": 4.2, "pace": 4.8}, "focus_zones": ["Делегирование", "Найм middle-специалистов"]}}
      ]
    },
    {
      "name": "Борис Лоскутов",
      "email": "demo.client02@punctb.test",
      "phone": "+7 (999) 100-01-02",
      "contact_permission": true,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.42, "investigative": 0.63, "artistic": 0.28, "social": 0.51, "enterprising": 0.55, "conventional": 0.40}, "top_professions": ["Продакт-менеджер", "Бизнес-аналитик", "Фасилитатор"]}},
        {"id": 6, "payload": {"needs": {"autonomy": 9, "service": 5, "challenge": 8, "stability": 6, "influence": 7}, "career_vector": "product-lead"}},
        {"id": 8, "payload": {"red_flags": ["Жёсткий микроменеджмент", "Отсутствие стратегии", "Закрытая коммуникация"], "tolerance_level": 2}},
        {"id": 13, "payload": {"values": {"creativity": 24, "independence": 34, "status": 21, "altruism": 29, "stability": 31}, "priority": "independence"}},
        {"id": 15, "payload": {"resilience_index": 0.71, "stress_triggers": ["Неопределённые цели", "Избыточная бюрократия"], "recovery_tools": ["Планирование недели", "Физическая активность"]}}
      ]
    },
    {
      "name": "Виктория Нестерова",
      "email": "demo.client03@punctb.test",
      "phone": "+7 (999) 100-01-03",
      "contact_permission": false,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.29, "investigative": 0.68, "artistic": 0.66, "social": 0.47, "enterprising": 0.41, "conventional": 0.35}, "top_professions": ["UX-исследователь", "Проджект-дизайнер", "Сервис-дизайнер"]}},
        {"id": 2, "payload": {"favorites": ["Полевые интервью", "Иллюстрация", "Наставничество студентов", "Разработка гайдов"], "energy_index": 0.79}},
        {"id": 10, "payload": {"interview_notes": {"start": "Занималась графическим дизайном, затем перешла в продуктовые исследования", "success_story": "За полгода подняла NPS продукта на 18 пунктов", "support_system": ["Сообщество дизайнеров", "Ментор"]}}},
        {"id": 12, "payload": {"scenes": [{"title": "Рабочий день", "description": "Анализ обратной связи пользователей и дизайн-спринт"}, {"title": "Командная встреча", "description": "Совместная ideation-сессия с разработчиками"}], "vision_score": 4.4}},
        {"id": 17, "payload": {"satisfaction": {"team": 4.9, "tasks": 4.7, "pace": 4.1}, "focus_zones": ["Развитие лидерских навыков"]}, "open_answer": "Хочу стать ведущим дизайнером исследовательского направления."}
      ]
    },
    {
      "name": "Глеб Савинов",
      "email": "demo.client04@punctb.test",
      "phone": "+7 (999) 100-01-04",
      "contact_permission": true,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.55, "investigative": 0.61, "artistic": 0.34, "social": 0.44, "enterprising": 0.62, "conventional": 0.38}, "top_professions": ["Продакт-менеджер", "Руководитель акселератора", "Стратегический консультант"]}},
        {"id": 6, "payload": {"needs": {"autonomy": 8, "service": 6, "challenge": 9, "stability": 4, "influence": 8}, "career_vector": "venture-builder"}},
        {"id": 8, "payload": {"red_flags": ["Отсутствие данных для решений", "Закрытая культура", "Медленные согласования"], "tolerance_level": 1}},
        {"id": 13, "payload": {"values": {"creativity": 30, "independence": 33, "status": 28, "altruism": 19, "stability": 17}, "priority": "independence"}},
        {"id": 15, "payload": {"resilience_index": 0.68, "stress_triggers": ["Долгие циклы согласования"], "recovery_tools": ["Анализ рисков", "Коуч-сессии"]}}
      ]
    },
    {
      "name": "Дарья Селиванова",
      "email": "demo.client05@punctb.test",
      "phone": "+7 (999) 100-01-05",
      "contact_permission": true,
      "is_phone_adult": false,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.21, "investigative": 0.47, "artistic": 0.74, "social": 0.69, "enterprising": 0.32, "conventional": 0.28}, "top_professions": ["Креативный продюсер", "Педагог по театру", "Контент-стратег"]}},
        {"id": 2, "payload": {"favorites": ["Выступать на сцене", "Вести подкаст", "Арт-проекты с подростками"], "energy_index": 0.88}},
        {"id": 4, "payload": {"ideal_day": {"morning": "Подготовка сценария", "day": "Запись образовательного контента", "evening": "Наставничество подростков"}, "key_values": ["Служение", "Творчество", "Гибкость"]}},
        {"id": 10, "payload": {"interview_notes": {"start": "С 15 лет ведёт подростковый театр", "support_system": ["Семья", "Сообщество педагогов"], "achievements": ["Лауреат фестиваля молодёжного театра"]}}},
        {"id": 13, "payload": {"values": {"creativity": 39, "independence": 27, "status": 12, "altruism": 33, "stability": 24}, "priority": "creativity"}, "open_answer": "Нужен проект, где можно совмещать творчество и наставничество."}
      ]
    },
    {
      "name": "Егор Матвеев",
      "email": "demo.client06@punctb.test",
      "phone": "+7 (999) 100-01-06",
      "contact_permission": true,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.48, "investigative": 0.66, "artistic": 0.31, "social": 0.42, "enterprising": 0.57, "conventional": 0.39}, "top_professions": ["Data Product Manager", "Руководитель аналитики", "Growth-менеджер"]}},
        {"id": 6, "payload": {"needs": {"autonomy": 7, "service": 4, "challenge": 9, "stability": 5, "influence": 8}, "career_vector": "growth-lead"}},
        {"id": 12, "payload": {"scenes": [{"title": "Discovery-день", "description": "Интервью с пользователями и анализ воронки"}, {"title": "Запуск эксперимента", "description": "Планирование A/B теста и синхронизация с командой"}], "vision_score": 4.2}},
        {"id": 13, "payload": {"values": {"creativity": 25, "independence": 35, "status": 22, "altruism": 18, "stability": 26}, "priority": "independence"}},
        {"id": 15, "payload": {"resilience_index": 0.75, "stress_triggers": ["Отложенные решения", "Несогласованные метрики"], "recovery_tools": ["Аналитический журнал", "Плавание"]}}
      ]
    },
    {
      "name": "Жанна Лазарева",
      "email": "demo.client07@punctb.test",
      "phone": "+7 (999) 100-01-07",
      "contact_permission": true,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.33, "investigative": 0.45, "artistic": 0.69, "social": 0.63, "enterprising": 0.47, "conventional": 0.32}, "top_professions": ["Контент-директор", "Руководитель комьюнити", "PR-менеджер"]}},
        {"id": 2, "payload": {"favorites": ["Интервью с экспертами", "Организация событий", "Сторителлинг"], "energy_index": 0.81}},
        {"id": 4, "payload": {"ideal_day": {"morning": "Планирование контент-стратегии", "day": "Работа с командой авторов", "evening": "Комьюнити-ивент"}, "key_values": ["Команда", "Развитие", "Свобода"]}},
        {"id": 13, "payload": {"values": {"creativity": 33, "independence": 28, "status": 24, "altruism": 31, "stability": 21}, "priority": "creativity"}},
        {"id": 17, "payload": {"satisfaction": {"team": 4.3, "tasks": 4.6, "pace": 4.0}, "focus_zones": ["Структурирование процессов", "Передача знаний"]}}
      ]
    },
    {
      "name": "Зоя Полянская",
      "email": "demo.client08@punctb.test",
      "phone": "+7 (999) 100-01-08",
      "contact_permission": false,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.37, "investigative": 0.58, "artistic": 0.41, "social": 0.62, "enterprising": 0.44, "conventional": 0.47}, "top_professions": ["HR BP", "Организационный коуч", "People Partner"]}},
        {"id": 6, "payload": {"needs": {"autonomy": 6, "service": 9, "challenge": 7, "stability": 7, "influence": 6}, "career_vector": "people-partner"}},
        {"id": 10, "payload": {"interview_notes": {"start": "Начинала в рекрутинге, затем развивала программы адаптации", "support_system": ["HR-сообщества", "Супервизор"], "success_story": "Снизила текучесть стажёров на 35% за год"}}},
        {"id": 13, "payload": {"values": {"creativity": 21, "independence": 26, "status": 17, "altruism": 36, "stability": 28}, "priority": "altruism"}},
        {"id": 15, "payload": {"resilience_index": 0.77, "stress_triggers": ["Эмоционально тяжёлые кейсы"], "recovery_tools": ["Супервизия", "Йога"]}}
      ]
    },
    {
      "name": "Илья Романов",
      "email": "demo.client09@punctb.test",
      "phone": "+7 (999) 100-01-09",
      "contact_permission": true,
      "is_phone_adult": true,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.59, "investigative": 0.54, "artistic": 0.26, "social": 0.38, "enterprising": 0.66, "conventional": 0.43}, "top_professions": ["Руководитель продаж B2B", "Операционный директор", "Product Ops"]}},
        {"id": 6, "payload": {"needs": {"autonomy": 7, "service": 5, "challenge": 8, "stability": 6, "influence": 9}, "career_vector": "ops-lead"}},
        {"id": 8, "payload": {"red_flags": ["Нечёткие KPI", "Неустойчивый кэшфлоу", "Неопределённая продуктовая стратегия"], "tolerance_level": 2}},
        {"id": 13, "payload": {"values": {"creativity": 20, "independence": 29, "status": 30, "altruism": 18, "stability": 26}, "priority": "status"}},
        {"id": 17, "payload": {"satisfaction": {"team": 4.1, "tasks": 4.4, "pace": 4.3}, "focus_zones": ["Стандартизация процессов", "Развитие middle менеджеров"]}}
      ]
    },
    {
      "name": "Кира Шевцова",
      "email": "demo.client10@punctb.test",
      "phone": "+7 (999) 100-01-10",
      "contact_permission": true,
      "is_phone_adult": false,
      "diagnostics": [
        {"id": 0, "payload": {"summary": {"realistic": 0.24, "investigative": 0.49, "artistic": 0.73, "social": 0.65, "enterprising": 0.31, "conventional": 0.27}, "top_professions": ["Сценарист", "Продюсер образовательного контента", "Наставник подростков"]}},
        {"id": 2, "payload": {"favorites": ["Съёмка короткометражек", "Создание образовательных сценариев", "Волонтёрство на фестивалях"], "energy_index": 0.87}},
        {"id": 4, "payload": {"ideal_day": {"morning": "Подготовка сценария", "day": "Съёмочная площадка", "evening": "Обсуждение результатов с подростками"}, "key_values": ["Творчество", "Влияние", "Свобода"]}},
        {"id": 12, "payload": {"scenes": [{"title": "Продакшен-подготовка", "description": "Подбор команды и распределение ролей"}, {"title": "День съёмки", "description": "Работа с актёрами и техниками"}], "vision_score": 4.5}},
        {"id": 13, "payload": {"values": {"creativity": 40, "independence": 30, "status": 15, "altruism": 29, "stability": 18}, "priority": "creativity"}, "open_answer": "Ищу наставника для развития в продюсировании образовательных проектов."}
      ]
    }
  ]$_clients$::jsonb;
  v_client jsonb;
  v_diag jsonb;
  v_contact boolean;
  v_is_adult boolean;
  v_diag_counter integer;
  v_client_id uuid;
  v_email text;
  v_metadata jsonb;
  v_slug text;
  v_now timestamptz;
BEGIN
  SELECT up.id
    INTO v_specialist_id
    FROM app.user_profiles up
    LEFT JOIN auth.users au ON au.id = up.id
   WHERE up.type = 'specialist'
     AND up.active
     AND lower(COALESCE(up.email, au.email)) = lower(v_specialist_email)
   LIMIT 1;

  IF v_specialist_id IS NULL THEN
    RAISE EXCEPTION 'Специалист % не найден или не активен — создайте профиль и повторите операцию.', v_specialist_email;
  END IF;

  -- Remove existing demo clients to keep seeding idempotent.
  DELETE FROM auth.users u
  USING (
    SELECT lower(value->>'email') AS email
    FROM jsonb_array_elements(v_clients) value
  ) demo
  WHERE lower(u.email) = demo.email;

  FOR v_client IN
    SELECT value
    FROM jsonb_array_elements(v_clients) AS value
  LOOP
    v_contact := COALESCE((v_client->>'contact_permission')::boolean, true);
    v_is_adult := COALESCE((v_client->>'is_phone_adult')::boolean, true);
    v_now := clock_timestamp();

    v_email := NULLIF(btrim(lower(COALESCE(v_client->>'email', ''))), '');
    IF v_email IS NULL THEN
      RAISE EXCEPTION 'client email is required for demo seed (client: %)', v_client->>'name';
    END IF;

    SELECT id
      INTO v_client_id
      FROM auth.users
     WHERE lower(email) = v_email
     LIMIT 1;

    IF v_client_id IS NULL THEN
      v_client_id := gen_random_uuid();
      INSERT INTO auth.users (
          id, instance_id, aud, role, email,
          raw_app_meta_data, raw_user_meta_data,
          created_at, updated_at, email_confirmed_at,
          is_sso_user, is_anonymous
      )
      VALUES (
          v_client_id,
          '00000000-0000-0000-0000-000000000000'::uuid,
          'authenticated',
          'authenticated',
          v_email,
          jsonb_build_object('provider', 'email', 'providers', jsonb_build_array('email')),
          jsonb_strip_nulls(jsonb_build_object('name', v_client->>'name', 'phone', v_client->>'phone')),
          v_now,
          v_now,
          v_now,
          false,
          false
      );
    ELSE
      UPDATE auth.users
         SET raw_user_meta_data = coalesce(raw_user_meta_data, '{}'::jsonb)
                                  || jsonb_strip_nulls(jsonb_build_object('name', v_client->>'name', 'phone', v_client->>'phone')),
             updated_at = v_now
       WHERE id = v_client_id;
    END IF;

    v_metadata := jsonb_strip_nulls(jsonb_build_object(
      'name', v_client->>'name',
      'phone', v_client->>'phone',
      'email', v_email
    ));
    v_slug := app.generate_slug(v_client_id, ARRAY[v_email, v_client->>'name']);

    INSERT INTO app.user_profiles (
        id, rls, email, phone, first_name, family_name, patronymic, type, status, slug,
        country, city, active, supervisor_id,
        contact_permission, is_phone_adult, is_blocked_royalty,
        first_result_at, last_result_at, metadata,
        created_at, created_by, updated_at, updated_by, removed_at, removed_by
    )
    VALUES (
        v_client_id,
        'client',
        v_email,
        NULLIF(v_client->>'phone', ''),
        NULLIF(v_client->>'name', ''),
        NULL,
        NULL,
        'diagnostic',
        'new',
        v_slug,
        NULL,
        NULL,
        true,
        v_specialist_id,
        v_contact,
        v_is_adult,
        false,
        NULL,
        NULL,
        v_metadata,
        v_now,
        NULL,
        v_now,
        NULL,
        NULL,
        NULL
    )
    ON CONFLICT (id) DO UPDATE
      SET email = EXCLUDED.email,
          phone = COALESCE(EXCLUDED.phone, app.user_profiles.phone),
          first_name = COALESCE(EXCLUDED.first_name, app.user_profiles.first_name),
          type = COALESCE(EXCLUDED.type, app.user_profiles.type),
          status = COALESCE(EXCLUDED.status, app.user_profiles.status),
          slug = COALESCE(EXCLUDED.slug, app.user_profiles.slug),
          supervisor_id = COALESCE(app.user_profiles.supervisor_id, EXCLUDED.supervisor_id),
          contact_permission = COALESCE(EXCLUDED.contact_permission, app.user_profiles.contact_permission),
          is_phone_adult = COALESCE(EXCLUDED.is_phone_adult, app.user_profiles.is_phone_adult),
          metadata = jsonb_strip_nulls(app.user_profiles.metadata || v_metadata),
          active = true,
          updated_at = v_now,
          updated_by = NULL;

    v_diag_counter := 0;
    FOR v_diag IN
      SELECT value
      FROM jsonb_array_elements(v_client->'diagnostics') AS value
    LOOP
      v_diag_counter := v_diag_counter + 1;
      INSERT INTO app.user_diag (
        target_id,
        supervisor_id,
        diagnostic_id,
        payload,
        open_answer,
        created_at,
        updated_at
      )
      SELECT
        v_client_id,
        v_specialist_id,
        (v_diag->>'id')::int,
        COALESCE(v_diag->'payload', '{}'::jsonb),
        NULLIF(v_diag->>'open_answer', ''),
        v_now - (v_diag_counter * interval '2 days'),
        v_now - (v_diag_counter * interval '2 days');
    END LOOP;
  END LOOP;
END;
$$;

COMMIT;
