"""Метрики по сообщениям. Вход: список словарей из analytics.export.load_messages."""
import collections
import json
import re

STATUS_RE = re.compile(r'"status"\s*:\s*"(\w+)"')
FUNCTION_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def in_period(message, start, end):
    return start <= message["at"].date() <= end


def daily_activity(messages, start, end):
    """По дням: диалоги, где клиент писал в этот день, и число сообщений по ролям."""
    days = collections.defaultdict(lambda: {"dialogs": set(), "user": 0, "assistant": 0, "operator": 0})
    for m in messages:
        if not in_period(m, start, end):
            continue
        day = days[m["at"].date()]
        if m["role"] == "user":
            day["dialogs"].add(m["dialog_id"])
        if m["role"] in ("user", "assistant", "operator"):
            day[m["role"]] += 1
    return [
        {"date": d, "dialogs": len(v["dialogs"]), "user": v["user"], "assistant": v["assistant"], "operator": v["operator"]}
        for d, v in sorted(days.items())
    ]


def function_outcomes(messages, function_name, start, end):
    """Результаты вызовов функции по полю status в ответе: success, busy, error и т.д.

    Результат относится к последнему вызову этой функции в том же диалоге.
    Возвращает счётчик статусов и множество диалогов с успешным результатом.
    """
    waiting = {}
    counts = collections.Counter()
    success_dialogs = set()
    for m in sorted(messages, key=lambda x: x["at"]):
        if m["role"] == "function_call":
            match = FUNCTION_NAME_RE.search(m["text"])
            if match and match.group(0) == function_name:
                waiting[m["dialog_id"]] = m["at"]
            continue
        if m["role"] != "function_result" or m["dialog_id"] not in waiting:
            continue
        called_at = waiting.pop(m["dialog_id"])
        if not (start <= called_at.date() <= end):
            continue
        status = STATUS_RE.search(m["text"])
        key = status.group(1) if status else "unknown"
        counts[key] += 1
        if key == "success":
            success_dialogs.add(m["dialog_id"])
    return {"counts": dict(counts), "success_dialogs": len(success_dialogs)}


def dialog_profile(messages, start, end, night=(22, 8)):
    """Доли по диалогам периода: с участием оператора и начатые ночью."""
    first_user = {}
    with_operator = set()
    for m in messages:
        if not in_period(m, start, end):
            continue
        if m["role"] == "user" and (m["dialog_id"] not in first_user or m["at"] < first_user[m["dialog_id"]]):
            first_user[m["dialog_id"]] = m["at"]
        if m["role"] == "operator":
            with_operator.add(m["dialog_id"])
    total = len(first_user)
    night_count = sum(1 for at in first_user.values() if at.hour >= night[0] or at.hour < night[1])
    return {
        "dialogs": total,
        "with_operator": len(with_operator & set(first_user)),
        "night": night_count,
    }


def transcript(messages, dialog_id, max_chars=6000):
    """Текст диалога для LLM-разметки: только реплики клиента, агента и оператора."""
    lines = []
    for m in sorted((x for x in messages if x["dialog_id"] == dialog_id), key=lambda x: x["at"]):
        if m["role"] in ("user", "assistant", "operator"):
            lines.append(f"{m['role']}: {m['text']}")
        elif m["role"] == "function_result":
            status = STATUS_RE.search(m["text"])
            lines.append(f"function_result: {status.group(1) if status else 'no_status'}")
    text = "\n".join(lines)
    return text[-max_chars:]


def to_json(value):
    return json.dumps(value, ensure_ascii=False, default=str, indent=2)
