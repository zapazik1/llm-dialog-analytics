"""Отчёт по выгрузке: python -m analytics export.xlsx --from 2026-09-23 --to 2026-09-28 --booking save_appointment_details"""
import argparse
import datetime

from analytics.export import load_messages
from analytics.metrics import daily_activity, dialog_profile, function_outcomes


def pct(part, whole):
    return f"{part / whole:.1%}" if whole else "н/д"


def main():
    parser = argparse.ArgumentParser(description="Метрики ИИ-агента по выгрузке диалогов")
    parser.add_argument("export")
    parser.add_argument("--from", dest="start", required=True, type=datetime.date.fromisoformat)
    parser.add_argument("--to", dest="end", required=True, type=datetime.date.fromisoformat)
    parser.add_argument("--booking", help="имя функции целевого действия, например save_appointment_details")
    args = parser.parse_args()

    messages = load_messages(args.export)
    days = daily_activity(messages, args.start, args.end)
    profile = dialog_profile(messages, args.start, args.end)

    print(f"# Работа агента {args.start} — {args.end}\n")
    print("| День | Диалогов | Сообщений клиентов | Ответов агента | Сообщений оператора |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for d in days:
        print(f"| {d['date']} | {d['dialogs']} | {d['user']} | {d['assistant']} | {d['operator']} |")
    if days:
        avg = sum(d["dialogs"] for d in days) / len(days)
        print(f"\nДиалогов в день в среднем: {avg:.0f}.")
    print(f"Диалогов за период: {profile['dialogs']}; с участием оператора: "
          f"{profile['with_operator']} ({pct(profile['with_operator'], profile['dialogs'])}); "
          f"начаты ночью: {profile['night']} ({pct(profile['night'], profile['dialogs'])}).")
    if args.booking:
        outcome = function_outcomes(messages, args.booking, args.start, args.end)
        print(f"\nФункция {args.booking}: {outcome['counts']}; диалогов с успешным результатом: {outcome['success_dialogs']}.")


if __name__ == "__main__":
    main()
