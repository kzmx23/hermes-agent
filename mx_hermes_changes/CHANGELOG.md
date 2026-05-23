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
