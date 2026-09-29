import datetime as dt
import json

import pytest

from analytics.export import load_messages
from analytics.llm_label import label_dialog, summarize
from analytics.metrics import daily_activity, dialog_profile, function_outcomes, transcript
from sample.make_sample_export import build

D = dt.date(2099, 6, 1)


def msg(dialog, minute, role, text="", day=D):
    return {"dialog_id": dialog, "at": dt.datetime.combine(day, dt.time(10, minute)), "role": role, "text": text}


def test_function_result_is_matched_to_its_call():
    messages = [
        msg("1", 0, "function_call", "save_appointment_details {}"),
        msg("1", 1, "function_result", json.dumps({"status": "busy"})),
        msg("1", 2, "function_call", "check_time {}"),
        msg("1", 3, "function_result", json.dumps({"status": "free"})),
        msg("1", 4, "function_call", "save_appointment_details {}"),
        msg("1", 5, "function_result", json.dumps({"status": "success"})),
        msg("2", 0, "function_call", "save_appointment_details {}"),
        msg("2", 1, "function_result", "Ошибка при выполнении кода"),
    ]
    result = function_outcomes(messages, "save_appointment_details", D, D)
    assert result == {"counts": {"busy": 1, "success": 1, "unknown": 1}, "success_dialogs": 1}


def test_daily_activity_counts_dialogs_where_client_wrote():
    messages = [msg("1", 0, "user"), msg("1", 1, "assistant"), msg("2", 0, "assistant"), msg("3", 5, "user")]
    assert daily_activity(messages, D, D) == [{"date": D, "dialogs": 2, "user": 2, "assistant": 2, "operator": 0}]


def test_night_dialogs():
    late = {"dialog_id": "9", "at": dt.datetime(2099, 6, 1, 23, 10), "role": "user", "text": ""}
    early = {"dialog_id": "8", "at": dt.datetime(2099, 6, 1, 9, 0), "role": "user", "text": ""}
    assert dialog_profile([late, early], D, D)["night"] == 1


def test_sample_export_roundtrip(tmp_path):
    path = build(tmp_path / "export.xlsx", days=2)
    messages = load_messages(path)
    days = daily_activity(messages, D, D + dt.timedelta(days=1))
    assert len(days) == 2
    assert all(d["dialogs"] > 0 for d in days)
    assert "Клиент" not in json.dumps([m["text"] for m in messages], ensure_ascii=False)


def test_transcript_hides_function_payloads():
    messages = [msg("1", 0, "user", "Хочу к врачу"), msg("1", 1, "function_result", '{"status": "success", "patient": "секрет"}')]
    text = transcript(messages, "1")
    assert "секрет" not in text and "function_result: success" in text


@pytest.mark.parametrize("raw, category", [
    ('{"category": "A", "reason": "записал", "failed_step": null}', "A"),
    ('{"category": "Z"}', None),
    ("не json", None),
])
def test_label_dialog_parsing(raw, category):
    assert label_dialog("user: привет", lambda prompt: raw)["category"] == category


def test_automation_rate_ignores_not_judged():
    labels = [{"category": "A"}] * 7 + [{"category": "B"}] * 3 + [{"category": "C"}] * 10 + [{"category": None}]
    assert summarize(labels) == {"A": 7, "B": 3, "C": 10, "unlabeled": 1, "automation_rate": 0.7}
