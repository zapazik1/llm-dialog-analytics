"""Синтетическая выгрузка в формате NextBot для демонстрации и тестов. Все данные выдуманы."""
import datetime
import json
import pathlib
import random

import openpyxl

HEADER = ["ID диалога", "Имя пользователя", "Дата", "Автор", "Тип", "Сообщение",
          "Сообщение (часть 2)", "Сообщение (часть 3)", "Сообщение (часть 4)", "Сообщение (часть 5)", "Вложения", "Теги"]


def row(dialog_id, at, author, kind, text):
    return [dialog_id, "Клиент", at.strftime("%d.%m.%Y, %H:%M"), author, kind, text, None, None, None, None, None, None]


def build(path, days=6, start=datetime.datetime(2099, 6, 1, 8, 0), seed=3):
    rnd = random.Random(seed)
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Сообщения"
    sheet.append(HEADER)
    dialog_id = 1000
    for day in range(days):
        for _ in range(rnd.randint(40, 70)):
            dialog_id += 1
            at = start + datetime.timedelta(days=day, minutes=rnd.randint(0, 16 * 60))
            sheet.append(row(dialog_id, at, "Пользователь", None, "Здравствуйте, хочу записаться к терапевту"))
            sheet.append(row(dialog_id, at, "Ассистент", None, "Подскажите удобный день и время"))
            if rnd.random() < 0.6:
                at += datetime.timedelta(minutes=2)
                sheet.append(row(dialog_id, at, "Пользователь", None, "Завтра в 10"))
                sheet.append(row(dialog_id, at, "Вызов функции", "Вызов функции", "save_appointment_details {}"))
                status = rnd.choices(["success", "busy", "error"], weights=[80, 15, 5])[0]
                sheet.append(row(dialog_id, at, "Инструмент", "Результат функции", json.dumps({"status": status})))
                reply = "Записала вас" if status == "success" else "Это время занято, есть 11:00"
                sheet.append(row(dialog_id, at, "Ассистент", None, reply))
            if rnd.random() < 0.05:
                sheet.append(row(dialog_id, at, "Ассистент", "Сообщение оператора", "Подключился администратор"))
    book.save(path)
    return path


if __name__ == "__main__":
    print(build(pathlib.Path(__file__).with_name("sample_export.xlsx")))
