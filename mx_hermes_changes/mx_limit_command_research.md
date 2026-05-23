# Исследование и доработка команды /limit

Дата: 2026-05-23 02:47 CDT
Сессия: OpenAI Codex / gpt-5.5
Контекст: пользователь попросил доработать `/limit`, потому что команда не показывает OpenAI provider и не показывает реальные остатки токенов на сессию/день/неделю/месяц.

## Текущее состояние до изменений

В Hermes фактически была команда `/usage`, а `/limit` не была зарегистрирована как alias.

Текущий `/usage` показывал:
- usage текущей сессии;
- последние rate-limit headers, если они были захвачены после API call;
- account usage только для отдельных провайдеров: `openai-codex`, `anthropic`, `openrouter`.

OpenAI provider через обычный inference API key не был представлен в `agent/account_usage.py`.

## Root cause

1. `/limit` не существовал в `hermes_cli/commands.py`, поэтому gateway/CLI не резолвили его как команду usage.
2. `agent/account_usage.py::fetch_account_usage()` не обрабатывал `openai`.
3. `agent/rate_limit_tracker.py` парсил reset headers только как float, а OpenAI часто возвращает duration strings: `1s`, `500ms`, `6m0s`, `1h2m3s`.
4. CLI `_show_usage()` делал ранний return при `session_api_calls == 0`, из-за чего account/provider limits не показывались до первого API call.

## Что можно показать честно

### Точно доступно

- Текущее usage Hermes-сессии: input/output/cache/reasoning tokens и API calls, если provider вернул usage.
- Short-window rate limits OpenAI-compatible API: RPM/TPM и reset из `x-ratelimit-*` headers последнего ответа.
- OpenAI Codex subscription windows: Session/Weekly remaining percent через существующий Codex usage endpoint, если OAuth доступен.
- OpenRouter credits/key quota и Anthropic OAuth windows — уже поддерживались.

### Недоступно честно через standard OpenAI inference key

OpenAI API не раскрывает day/week/month account token budget remaining через обычный inference API key. Такие данные требуют других billing/admin/project APIs и не являются универсальным live quota для текущей inference-сессии.

Поэтому для OpenAI добавлен честный caveat: показывать short-window headers после API call, а day/week/month account budgets помечать как недоступные через standard inference API.

## Внесённые изменения

- `hermes_cli/commands.py`
  - `/limit` добавлен как alias команды `/usage`.

- `agent/rate_limit_tracker.py`
  - добавлен parser duration reset headers для OpenAI-compatible APIs:
    - `1s` → 1.0
    - `500ms` → 0.5
    - `6m0s` → 360.0
    - `1h2m3s` → 3723.0

- `agent/account_usage.py`
  - добавлен OpenAI snapshot/caveat для `provider == openai` и custom `base_url == api.openai.com`.
  - snapshot объясняет, что day/week/month token budgets недоступны через standard inference API.

- `cli.py`
  - `/usage` больше не скрывает provider/account limits до первого API call; при нуле calls показывает предупреждение и продолжает строить report.

## Тесты

Добавлены tests:

- `tests/hermes_cli/test_usage_limit_command.py`
  - `/limit` и `/limit` со slash резолвятся в canonical `usage`.

- `tests/agent/test_rate_limit_tracker_openai.py`
  - проверяет parsing OpenAI reset duration strings.

- `tests/agent/test_account_usage_openai.py`
  - проверяет OpenAI account usage caveat.

## Ограничения и следующий этап

Если нужно показывать day/week/month именно как local Hermes-recorded usage, это отдельный этап:

1. Добавить в `hermes_state.py` агрегатор usage totals за today/week/month.
2. В `/usage`/`/limit` выводить два разных блока:
   - Provider/API live limits — headers/account APIs.
   - Local Hermes usage — сколько Hermes потратил в текущей сессии/день/неделю/месяц.
3. Если пользователь задаст локальные бюджеты в config, можно считать `remaining = budget - local_used`, но это будет local configured budget, а не provider quota.
