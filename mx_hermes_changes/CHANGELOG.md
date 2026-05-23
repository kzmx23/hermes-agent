# Журнал изменений форка Hermes Agent (kzmx23/hermes-agent)

---

## Сессия: 23 мая 2026 г.

**Контекст:** Рабочая сессия по развитию форка Hermes Agent. Восемь коммитов в `origin/main` поверх `upstream/main`. Форк: `origin=https://github.com/kzmx23/hermes-agent.git`, `upstream=https://github.com/NousResearch/hermes-agent.git`. Шлюз перезапущен с PID 2705847.

**Итого:** 15 файлов изменено, 1078 добавлений, 18 удалений.

---

### Коммиты

#### 1. `a09f26626` — local: reapply NeuralDeep STT and update hook after Hermes update

**Изменённые файлы:**
- `hermes_cli/main.py` — добавлена функция `_run_local_post_update_hooks`
- `tools/transcription_tools.py` — добавлен провайдер NeuralDeep STT

**Назначение:** Восстановление локальных кастомизаций (STT-провайдер NeuralDeep и post-update hook) после того, как автообновление Hermes их перезаписало.

---

#### 2. `216b2f760` — fix: preserve new Telegram topic sessions

**Изменённые файлы:**
- `gateway/run.py` — исправление в `_recover_telegram_topic_thread_id`
- `tests/gateway/test_telegram_topic_mode.py`

**Назначение:** Исправление регрессии: неизвестный thread_id, не являющийся General, ошибочно восстанавливался, что приводило к режиму «Все сообщения» вместо корректного топика.

---

#### 3. `e405a2c5a` — feat: clamp compression live tail budget with tail_min/max_tokens

**Изменённые файлы:**
- `agent/context_compressor.py` — параметры `tail_min`/`tail_max_tokens`, метод `_compute_tail_token_budget`
- `agent/agent_init.py` — проброс конфигурации
- `hermes_cli/config.py` — значения по умолчанию: threshold 0.78, target_ratio 0.15, protect_last_n 6, tail_min 8000, tail_max 30000, hygiene limit 300
- `tests/agent/test_context_compressor.py` — 4 новых теста

**Назначение:** Предотвращение чрезмерного сохранения «хвоста» контекста на моделях с большим контекстом (200K–1M токенов). Сжатие начинается раньше и действует агрессивнее.

---

#### 4. `42fff8ee1` — feat: add durable session handoff module (LLM-driven + extractive fallback)

**Изменённые файлы:**
- `agent/handoff.py` — **новый файл** (из коммита 3f0a32427)
- `tests/agent/test_handoff.py` — **новый файл** (19 тестов)

**Назначение:** Создание долговечных Markdown-файлов handoff для обеспечения непрерывности сессии после компакции/перезапуска. LLM заполняет структурированный шаблон с контекстом git; экстрактивный fallback используется, когда LLM недоступен.

---

#### 5. `4b017b77b` — feat: write handoff during context compression + plugin hooks

**Изменённые файлы:**
- `agent/conversation_compression.py` — hook `pre_context_compress`, генерация handoff перед сжатием, инъекция `[HANDOFF]` после сжатия
- `hermes_cli/plugins.py` — добавлены `pre_context_compress`, `post_context_compress` в `VALID_HOOKS`

**Назначение:** Перед отбрасыванием средней части контекста handoff записывается на диск. После сжатия в контекст внедряется указатель `[HANDOFF]`.

---

#### 6. `28111e05c` — feat: inject session handoff into system prompt via HERMES_HANDOFF_PATH

**Изменённые файлы:**
- `agent/system_prompt.py` — функция `read_handoff_excerpt`, активируется при наличии переменной окружения

**Назначение:** При установленной переменной окружения `HERMES_HANDOFF_PATH` содержимое handoff внедряется в волатильную часть системного промпта для бесшовного продолжения после перезапуска.

---

#### 7. `8065e20b5` — feat: add /handoff-session command (CLI + gateway)

**Изменённые файлы:**
- `hermes_cli/commands.py` — регистрация команды
- `cli.py` — диспетчеризация + `_manual_handoff_session` с `llm_summarize=True`
- `gateway/run.py` — диспетчеризация + `_handle_handoff_session_command`

**Назначение:** Ручная команда для записи LLM-суммаризованного handoff без сжатия контекста. Альтернативное имя: `/handoff-snap`.

---

#### 8. `1a601f5f4` — feat: best-effort LLM handoff for active agents during gateway shutdown

**Изменённые файлы:**
- `gateway/run.py` — цикл handoff в `_stop_impl` после `_notify_active_sessions_of_shutdown`

**Назначение:** Запись LLM-handoff файлов для всех активных агентов перед drain/остановкой шлюза. Агенты регистрируются в `gateway-active.json`.

---

### Сводка изменений по файлам

| Файл | Коммиты | Тип изменения |
|---|---|---|
| `agent/context_compressor.py` | e405a2c5a | модификация |
| `agent/agent_init.py` | e405a2c5a | модификация |
| `agent/conversation_compression.py` | 4b017b77b | модификация |
| `agent/handoff.py` | 42fff8ee1 | **новый** |
| `agent/system_prompt.py` | 28111e05c | модификация |
| `hermes_cli/commands.py` | 8065e20b5 | модификация |
| `hermes_cli/config.py` | e405a2c5a | модификация |
| `hermes_cli/main.py` | a09f26626 | модификация |
| `hermes_cli/plugins.py` | 4b017b77b | модификация |
| `cli.py` | 8065e20b5 | модификация |
| `gateway/run.py` | 216b2f760, 8065e20b5, 1a601f5f4 | модификация |
| `tools/transcription_tools.py` | a09f26626 | модификация |
| `tests/agent/test_context_compressor.py` | e405a2c5a | модификация (+4 теста) |
| `tests/agent/test_handoff.py` | 42fff8ee1 | **новый** (19 тестов) |
| `tests/gateway/test_telegram_topic_mode.py` | 216b2f760 | модификация |

---

### Семантические группы изменений

1. **Локальные кастомизации (post-update hook):** Коммит 1 — восстановление STT-провайдера и хука обновления.
2. **Исправление регрессии Telegram:** Коммит 2 — корректное восстановление thread_id топиков.
3. **Оптимизация сжатия контекста:** Коммит 3 — ограничение tail-бюджета для больших контекстных окон.
4. **Модуль session handoff (ядро):** Коммиты 4–6 — создание, запись при сжатии, инъекция в системный промпт.
5. **Управление handoff (CLI/gateway):** Коммиты 7–8 — ручная команда, автоматический handoff при остановке шлюза.

---

## Сессия: 23 мая 2026 г. — UX/Provider/Limit fixes

**Дата:** 2026-05-23 02:47 CDT  
**Модель:** OpenAI Codex / gpt-5.5  
**Цель:** перенести ранее отложенные локальные фиксы, убрать мусорные провайдеры из gateway/CLI picker, исправить `/resume`, добавить `/limit` как честный alias/report по usage/limits.

### Изменённые файлы

- `gateway/run.py`
  - `/resume` теперь сортирует список сессий по последней активности (`order_by_last_active=True`).
  - STT transcript теперь сохраняется в компактном формате `🎤 [Voice] ...`.

- `hermes_cli/models.py`
  - Добавлен allowlist активных built-in providers для видимого каталога:
    - `zai`
    - `openai-codex`
    - `gemini`
    - `kimi-coding`
    - `minimax`
    - `deepseek`
  - Цель: убрать мусорные/неиспользуемые providers из CLI/gateway picker.

- `hermes_cli/model_switch.py`
  - Добавлен фильтр `_filter_to_canonical_providers()`.
  - Built-in rows фильтруются по `CANONICAL_PROVIDERS`, но user-defined providers сохраняются (`cliproxy`, `neuraldeep`).

- `agent/auxiliary_client.py`
  - Исправлена поддержка `minimax-oauth` для auxiliary/title/compression.
  - OpenAI SDK использует converted `/v1` URL, а Anthropic wrapper получает оригинальный `/anthropic` URL для корректного transport detection.

- `hermes_cli/browser_connect.py`
  - Добавлен Chrome flag `--no-sandbox` для debug browser launch.

- `hermes_cli/commands.py`
  - `/limit` добавлен как alias команды `/usage`.

- `agent/rate_limit_tracker.py`
  - Добавлен parser OpenAI-compatible reset duration strings: `1s`, `500ms`, `6m0s`, `1h2m3s`.

- `agent/account_usage.py`
  - Добавлен OpenAI account usage snapshot/caveat.
  - Честно указывается, что standard OpenAI inference API не раскрывает day/week/month token budgets; live RPM/TPM показываются через headers после API call.

- `cli.py`
  - `/usage` больше не делает ранний return при `session_api_calls == 0`; provider/account limits теперь можно показать до первого API call.

### Новые/изменённые тесты

- `tests/gateway/test_resume_command.py`
  - Regression для сортировки `/resume` по last activity.

- `tests/hermes_cli/test_provider_filtering.py`
  - Проверяет visible provider allowlist и сохранение custom providers.

- `tests/agent/test_auxiliary_client.py`
  - Regression для MiniMax OAuth auxiliary wrapping.

- `tests/hermes_cli/test_browser_connect.py`
  - Проверяет наличие `--no-sandbox`.

- `tests/gateway/test_voice_transcription_enrichment.py`
  - Проверяет формат `🎤 [Voice] ...`.

- `tests/hermes_cli/test_usage_limit_command.py`
  - Проверяет `/limit` alias → `usage`.

- `tests/agent/test_rate_limit_tracker_openai.py`
  - Проверяет OpenAI reset duration parsing.

- `tests/agent/test_account_usage_openai.py`
  - Проверяет OpenAI account caveat.

### Документы

- `mx_hermes_changes/mx_limit_command_research.md`
  - Исследование `/limit`: что доступно точно, что недоступно через standard OpenAI inference API, и план следующего этапа для local Hermes day/week/month usage totals.

### Суть и цель изменений

1. Убрать мусорные providers из `/model` в gateway и terminal.
2. Исправить `/resume`, чтобы самые свежие по последнему сообщению сессии были сверху.
3. Перенести MiniMax OAuth auxiliary fix, чтобы title/compression/handoff не ломались на 401 из-за неверного transport.
4. Добавить browser `--no-sandbox`, чтобы Chrome debug launch работал на системах с restricted sandbox/user namespaces.
5. Сделать voice transcripts явно отличимыми от текстовых сообщений.
6. Добавить `/limit` и честно показать ограничения OpenAI: live short-window через headers, а day/week/month budgets — недоступны через standard inference API.

---

## Сессия: 23 мая 2026 г. — /rename alias

**Дата:** 2026-05-23 03:00 CDT  
**Модель:** gemini-3.5-flash via Google  
**Цель:** Добавить `/rename` как alias для команды `/title` (переименование текущей сессии), поскольку пользователь привык к `/rename`.

### Изменённые файлы

- `hermes_cli/commands.py`
  - Добавлен `aliases=("rename",)` для `CommandDef("title")`.

### Новые/изменённые тесты

- `tests/hermes_cli/test_rename_command.py`
  - Проверяет корректное разрешение команды `rename` и `/rename` в canonical `title`.

