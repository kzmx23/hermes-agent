"""Durable session handoff files for compaction and gateway restarts.

Handoffs are an operational continuity layer separate from the in-context
compression summary: they are written to disk before context is discarded so a
future continuation can recover goals, decisions, next steps, and changed files.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

HANDOFFS_DIRNAME = "handoffs"
_DEFAULT_EXCERPT_CHARS_PER_TOKEN = 4


def _safe_session_id(session_id: str | None) -> str:
    raw = str(session_id or "unknown-session")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-._")
    return safe or "unknown-session"


def _handoffs_dir(hermes_home: str | Path | None = None) -> Path:
    root = Path(hermes_home) if hermes_home is not None else get_hermes_home()
    return root / HANDOFFS_DIRNAME


def _stringify_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except Exception:
        return str(content)


def _message_excerpt(messages: Iterable[dict[str, Any]], *, max_messages: int = 40, max_chars: int = 12_000) -> str:
    """Return an extractive transcript excerpt suitable for fallback handoffs."""
    items = list(messages or [])
    if len(items) > max_messages:
        head = items[: max_messages // 4]
        tail = items[-(max_messages - len(head)) :]
        items = head + [{"role": "system", "content": "... middle messages omitted ..."}] + tail

    lines: list[str] = []
    used = 0
    for msg in items:
        role = msg.get("role", "unknown") if isinstance(msg, dict) else "unknown"
        content = _stringify_content(msg.get("content") if isinstance(msg, dict) else msg).strip()
        if not content and isinstance(msg, dict) and msg.get("tool_calls"):
            content = f"tool_calls: {_stringify_content(msg.get('tool_calls'))}"
        if not content:
            continue
        block = f"- **{role}:** {content}"
        remaining = max_chars - used
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[: max(0, remaining - 20)] + "… [truncated]"
        lines.append(block)
        used += len(block) + 1
    return "\n".join(lines) or "- Нет доступного текстового контекста."


def _write_latest_pointer(handoffs_dir: Path, target: Path) -> None:
    latest = handoffs_dir / "latest.md"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(target.name)
    except Exception:
        latest.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")


def _update_index(handoffs_dir: Path, entry: dict[str, Any]) -> None:
    index_path = handoffs_dir / "index.json"
    data: list[dict[str, Any]] = []
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            data = [x for x in raw if isinstance(x, dict)]
    except Exception:
        data = []

    data = [x for x in data if x.get("session_id") != entry.get("session_id")]
    data.append(entry)
    index_path.write_text(
        json.dumps(data[-500:], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _gather_git_context(hermes_home: str | Path | None = None) -> str:
    """Collect git log and status from the hermes_home config repo.

    Returns a combined string of recent commits and status, or an empty
    string on any failure.
    """
    home = Path(hermes_home) if hermes_home is not None else get_hermes_home()
    parts: list[str] = []

    try:
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True,
            text=True,
            cwd=str(home),
            timeout=10,
        )
        if log_result.returncode == 0 and log_result.stdout.strip():
            parts.append("=== git log --oneline -20 ===")
            parts.append(log_result.stdout.strip())
    except Exception:
        pass

    try:
        status_result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=str(home),
            timeout=10,
        )
        if status_result.returncode == 0 and status_result.stdout.strip():
            parts.append("=== git status --short ===")
            parts.append(status_result.stdout.strip())
    except Exception:
        pass

    return "\n".join(parts)


def _build_llm_handoff_prompt(
    *,
    safe_id: str,
    now: str,
    source_info: str,
    model: str | None,
    session_id: str | None,
    reason: str,
    git_context: str,
    transcript_excerpt: str,
) -> str:
    """Build the LLM prompt for generating a structured handoff summary."""
    return f"""Проанализируй приведённый транскрипт сессии и git-контекст. Заполни ВСЕ секции ниже на основе того, что реально произошло. Не пиши общие фразы — только конкретные факты.

# Handoff: {safe_id}

**Дата:** {now}
**Источник:** {source_info}
**Модель:** {model or ''}
**Session ID:** {session_id or ''}
**Причина:** {reason}

## Цель
[1-2 предложения: что пытался сделать пользователь]

## Выполнено
- [x] [конкретная задача — что было сделано]

## В работе / Следующие шаги
- [ ] [задача с путями к файлам и конкретными областями]
- [ ] [заблокированные задачи с объяснением]

## Ключевые решения
- **[Решение]**: [Что выбрано] — [Почему, включая отвергнутые альтернативы]

## Тупиковые пути (не повторять)
- [Подход который не сработал] — [Почему]

## Изменённые файлы
- `путь/к/файлу` — [что изменено, 1 строка]

## Текущее состояние
- **Тесты/проверки:** [статус]
- **Ручная проверка:** [что проверено]

## Контекст для следующей сессии
[2-4 предложения: самое важное для следующего агента]

## Рекомендуемое первое действие
[Точная команда или шаг]

---
Git log:
{git_context}

Transcript:
{transcript_excerpt}"""


def _call_auxiliary_llm(prompt: str, *, main_runtime: dict[str, Any] | None = None) -> str | None:
    """Call the auxiliary LLM with a handoff prompt.

    Returns the LLM response text, or None on any failure.
    """
    try:
        from agent.auxiliary_client import call_llm

        response = call_llm(
            task="compression",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.3,
            main_runtime=main_runtime,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str):
            content = str(content) if content else ""
        return content.strip() if content else None
    except Exception:
        logger.debug("LLM handoff summarization failed, falling back to extractive mode", exc_info=True)
        return None


def generate_handoff(
    *,
    session_id: str | None,
    messages: Iterable[dict[str, Any]] | None,
    reason: str,
    platform: str | None = None,
    model: str | None = None,
    parent_session_id: str | None = None,
    current_session_id: str | None = None,
    focus_topic: str | None = None,
    hermes_home: str | Path | None = None,
    extra_metadata: dict[str, Any] | None = None,
    llm_summarize: bool = False,
    session_name: str | None = None,
    gateway_name: str | None = None,
    main_runtime: dict[str, Any] | None = None,
) -> Path:
    """Write a durable markdown handoff and return its path.

    The implementation is deliberately extractive and dependency-free. It must
    keep working when auxiliary LLMs are unavailable during shutdown or while a
    compression failure is already in progress.

    When *llm_summarize* is True, an auxiliary LLM is used to produce a
    structured summary of the session. If the LLM call fails, the function
    falls back to the extractive (non-LLM) handoff automatically.
    """

    safe_id = _safe_session_id(session_id)
    handoffs_dir = _handoffs_dir(hermes_home)
    handoffs_dir.mkdir(parents=True, exist_ok=True)
    path = handoffs_dir / f"handoff-{safe_id}.md"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    current = current_session_id or session_id or ""

    # --- LLM summarization path ---
    if llm_summarize:
        source_info = (
            f"{session_name or 'unnamed'} | "
            f"{'Gateway: ' + gateway_name if gateway_name else 'Terminal'} | "
            f"Session: {session_id or ''}"
        )
        git_context = _gather_git_context(hermes_home)
        transcript_excerpt = _message_excerpt(
            messages or [],
            max_messages=80,
            max_chars=25_000,
        )
        prompt = _build_llm_handoff_prompt(
            safe_id=safe_id,
            now=now,
            source_info=source_info,
            model=model,
            session_id=session_id,
            reason=reason,
            git_context=git_context,
            transcript_excerpt=transcript_excerpt,
        )
        llm_content = _call_auxiliary_llm(prompt, main_runtime=main_runtime)

        if llm_content:
            path.write_text(llm_content, encoding="utf-8")
            _write_latest_pointer(handoffs_dir, path)
            _update_index(
                handoffs_dir,
                {
                    "session_id": session_id,
                    "safe_session_id": safe_id,
                    "path": str(path),
                    "created_at": now,
                    "reason": reason,
                    "platform": platform,
                    "model": model,
                    "parent_session_id": parent_session_id,
                    "current_session_id": current,
                    "llm_summarized": True,
                },
            )
            return path
        # LLM failed — fall through to extractive path below
        logger.info("LLM handoff summarization failed, using extractive fallback")

    # --- Extractive (default / fallback) path ---
    excerpt = _message_excerpt(messages or [])

    metadata_lines = [
        f"Дата: {now}",
        f"Платформа: {platform or ''}",
        f"Модель: {model or ''}",
        f"Parent session: {parent_session_id or ''}",
        f"Текущая session: {current}",
        f"Reason: {reason}",
    ]
    if focus_topic:
        metadata_lines.append(f"Focus: {focus_topic}")
    if extra_metadata:
        for key, value in sorted(extra_metadata.items()):
            if value is not None:
                metadata_lines.append(f"{key}: {value}")

    content = f"""# Handoff: {safe_id}

{chr(10).join(metadata_lines)}

## Цель

См. извлечённый контекст ниже. Если пользовательская цель не очевидна, сначала уточнить её по последним сообщениям.

## Выполнено

- Зафиксирован handoff по причине `{reason}`.

## В работе / Следующие шаги

- Восстановить текущую цель из раздела «Контекст для следующей сессии» и последних сообщений.
- Проверить фактическое состояние инструментами перед утверждениями о сервисах, файлах или конфигурации.

## Ключевые решения

- Handoff создан как durable continuity artifact; он дополняет compact summary и не заменяет проверку текущего состояния.

## Тупиковые пути — не повторять

- Не полагаться только на старый transcript после compact/restart; использовать этот handoff как стартовую карту состояния.

## Изменённые файлы / внешние артефакты

- Не определено автоматически. См. transcript excerpt и git/status проверки.

## Проверки

- Не выполнялись автоматически при создании handoff.

## Контекст для следующей сессии

{excerpt}

## Рекомендуемое первое действие

Прочитать этот handoff, затем проверить живое состояние через инструменты перед продолжением.
"""
    path.write_text(content, encoding="utf-8")
    _write_latest_pointer(handoffs_dir, path)
    _update_index(
        handoffs_dir,
        {
            "session_id": session_id,
            "safe_session_id": safe_id,
            "path": str(path),
            "created_at": now,
            "reason": reason,
            "platform": platform,
            "model": model,
            "parent_session_id": parent_session_id,
            "current_session_id": current,
        },
    )
    return path


def read_handoff_excerpt(path: str | Path, *, max_tokens: int = 12_000) -> str:
    """Read a handoff file with a rough token budget cap."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    max_chars = max(1, int(max_tokens) * _DEFAULT_EXCERPT_CHARS_PER_TOKEN)
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 80)] + "\n\n[... handoff truncated to configured max_tokens budget ...]\n"


def write_gateway_active_handoff(entry: dict[str, Any], *, hermes_home: str | Path | None = None) -> Path:
    """Append/update gateway-active handoff mapping."""
    handoffs_dir = _handoffs_dir(hermes_home)
    handoffs_dir.mkdir(parents=True, exist_ok=True)
    path = handoffs_dir / "gateway-active.json"
    data: list[dict[str, Any]] = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            data = [x for x in raw if isinstance(x, dict)]
    except Exception:
        data = []

    key = entry.get("session_key") or entry.get("session_id") or entry.get("handoff_path")
    if key:
        data = [x for x in data if (x.get("session_key") or x.get("session_id") or x.get("handoff_path")) != key]
    data.append({**entry, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    path.write_text(json.dumps(data[-500:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
