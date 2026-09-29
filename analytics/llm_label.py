"""Разметка диалогов через LLM: справился ли агент.

Категории:
  A  агент закрыл запрос сам: ответил, записал, перенёс, отменил, дал следующий шаг;
  B  реальная ошибка или ограничение агента: неверный ответ, не нашёл, запутал клиента;
  C  не оцениваем: рассылки, напоминания, спам, пустые диалоги, чаты без участия агента.

Уровень автоматизации = A / (A + B). Диалоги C в знаменатель не входят:
если агент ответил верно, а клиент ушёл, это не ошибка агента.
"""
import json

PROMPT = """Ты проверяешь работу ИИ-агента по одному диалогу.
Верни JSON: {{"category": "A" | "B" | "C", "reason": "одно предложение", "failed_step": "шаг, где агент ошибся, или null"}}.
A — агент сам закрыл запрос клиента или дал верный следующий шаг.
B — агент ошибся или не смог: неверные данные, не нашёл запись, запутал клиента, ответ противоречит результату функции.
C — диалог не оценивается: рассылка, напоминание, спам, пустой диалог, агент не должен был отвечать.
Если клиент перестал отвечать после верного ответа агента, это A.

Диалог:
{transcript}"""

VALID = {"A", "B", "C"}


def label_dialog(transcript, complete):
    """complete(prompt) -> строка ответа модели. Возвращает разметку или category=None при сбое."""
    raw = complete(PROMPT.format(transcript=transcript))
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {"category": None, "reason": "ответ модели не JSON", "failed_step": None}
    if data.get("category") not in VALID:
        return {"category": None, "reason": "неизвестная категория", "failed_step": None}
    return {"category": data["category"], "reason": data.get("reason", ""), "failed_step": data.get("failed_step")}


def summarize(labels):
    counts = {k: sum(1 for x in labels if x["category"] == k) for k in ("A", "B", "C")}
    unlabeled = sum(1 for x in labels if x["category"] is None)
    judged = counts["A"] + counts["B"]
    return {
        **counts,
        "unlabeled": unlabeled,
        "automation_rate": round(counts["A"] / judged, 3) if judged else None,
    }


def openai_complete(api_key, model="gpt-4o-mini"):
    """Функция complete для OpenAI Chat Completions с ответом строго в JSON."""
    import requests

    def complete(prompt):
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    return complete
