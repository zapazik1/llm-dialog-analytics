"""Чтение выгрузки диалогов NextBot (xlsx, лист «Сообщения»).

Имена пользователей при чтении отбрасываются: для метрик они не нужны,
а в отчёт не должны попасть персональные данные.
"""
import datetime

import openpyxl

SHEET = "Сообщения"
TEXT_COLUMNS = ["Сообщение", "Сообщение (часть 2)", "Сообщение (часть 3)", "Сообщение (часть 4)", "Сообщение (часть 5)"]

# Автор в выгрузке -> роль в метриках
ROLES = {
    "Пользователь": "user",
    "Ассистент": "assistant",
    "Вызов функции": "function_call",
    "Инструмент": "function_result",
    "Ошибка": "error",
}


def parse_time(value):
    if isinstance(value, datetime.datetime):
        return value
    return datetime.datetime.strptime(str(value), "%d.%m.%Y, %H:%M")


def load_messages(path):
    book = openpyxl.load_workbook(path, read_only=True)
    sheet = book[SHEET]
    rows = sheet.iter_rows(values_only=True)
    header = list(next(rows))
    index = {name: header.index(name) for name in header if name}
    messages = []
    for row in rows:
        author = row[index["Автор"]]
        kind = row[index["Тип"]]
        role = ROLES.get(author, "service")
        if role == "assistant" and kind and "оператора" in str(kind):
            role = "operator"
        text = "".join(str(row[index[c]]) for c in TEXT_COLUMNS if c in index and row[index[c]])
        messages.append({
            "dialog_id": str(row[index["ID диалога"]]),
            "at": parse_time(row[index["Дата"]]),
            "role": role,
            "text": text,
        })
    return messages
