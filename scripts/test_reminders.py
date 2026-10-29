#!/usr/bin/env python3
"""Exercise MAIKA reminder payload and response helpers without a cloud account."""

from __future__ import annotations

import ast
import io
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_reminders() -> dict:
    path = ROOT / "custom_components/maika/reminders.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node
        for node in tree.body
        if not (isinstance(node, ast.ImportFrom) and node.level > 0)
    ]
    namespace = {
        "__name__": "maika_reminders_test",
        "APP_EXECUTOR": "vn_south",
        "APP_TIMEZONE": "Asia/Ho_Chi_Minh",
    }
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.module = load_reminders()
        self.build = self.module["build_reminder_payload"]
        self.update = self.module["build_reminder_update_payload"]
        self.flatten = self.module["flatten_reminders"]
        self.error = self.module["ReminderValidationError"]

    def future(self, minutes: int = 30) -> str:
        return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()

    def test_build_uses_snake_case_and_app_timezone(self):
        start = "2026-11-01T00:00:00Z"
        payload = self.build(
            event="  Uống thuốc  ",
            start_at=start,
            serial_number=" speaker-one ",
            frequency="daily",
            alert_prior=15,
        )
        self.assertEqual(payload["event"], "Uống thuốc")
        self.assertEqual(payload["start_date"], "2026-11-01")
        self.assertEqual(payload["start_time"], "07:00:00")
        self.assertEqual(payload["timezone"], "Asia/Ho_Chi_Minh")
        self.assertEqual(payload["alert_prior"], 900)
        self.assertEqual(payload["devices"], ["speaker-one"])
        self.assertEqual(payload["executor"], "vn_south")
        self.assertEqual(payload["custom_tts"], "Uống thuốc")
        self.assertEqual(payload["alarm_type"], 1)
        self.assertEqual(payload["reminder_type"], 1)
        self.assertEqual(payload["frequency"], "daily")

    def test_build_accepts_naive_local_time_and_custom_tts(self):
        payload = self.build(
            event="Họp",
            start_at="2026-11-01T08:30",
            serial_number="speaker-one",
            custom_tts="Sắp đến giờ họp",
        )
        self.assertEqual(payload["start_date"], "2026-11-01")
        self.assertEqual(payload["start_time"], "08:30:00")
        self.assertEqual(payload["custom_tts"], "Sắp đến giờ họp")

    def test_build_rejects_bad_input_with_stable_codes(self):
        cases = [
            (
                {"event": "", "start_at": self.future(), "serial_number": "s"},
                "reminder_event_required",
            ),
            (
                {
                    "event": "x" * 201,
                    "start_at": self.future(),
                    "serial_number": "s",
                },
                "reminder_event_too_long",
            ),
            (
                {
                    "event": "ok",
                    "start_at": self.future(),
                    "serial_number": "s",
                    "frequency": "hourly",
                },
                "invalid_reminder_frequency",
            ),
            (
                {"event": "ok", "start_at": self.future(), "serial_number": " "},
                "reminder_device_required",
            ),
            (
                {
                    "event": "ok",
                    "start_at": self.future(),
                    "serial_number": "s",
                    "alert_prior": -1,
                },
                "invalid_reminder_alert_prior",
            ),
            (
                {
                    "event": "ok",
                    "start_at": self.future(),
                    "serial_number": "s",
                    "alert_prior": 1441,
                },
                "invalid_reminder_alert_prior",
            ),
            (
                {
                    "event": "ok",
                    "start_at": "2020-01-01T00:00:00+07:00",
                    "serial_number": "s",
                },
                "reminder_start_in_past",
            ),
            (
                {"event": "ok", "start_at": "", "serial_number": "s"},
                "reminder_start_required",
            ),
            (
                {"event": "ok", "start_at": "not-a-date", "serial_number": "s"},
                "invalid_reminder_start",
            ),
            (
                {
                    "event": "ok",
                    "start_at": self.future(),
                    "serial_number": "s",
                    "custom_tts": "x" * 501,
                },
                "reminder_speech_too_long",
            ),
        ]
        for kwargs, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(self.error) as error:
                    self.build(**kwargs)
                self.assertEqual(error.exception.code, code)

    def test_update_builds_partial_payload(self):
        payload = self.update(
            event="  Họp  ",
            start_at=self.future(60),
            frequency="weekly",
            alert_prior=5,
            custom_tts="Sắp họp",
        )
        self.assertEqual(payload["event"], "Họp")
        self.assertEqual(payload["frequency"], "weekly")
        self.assertEqual(payload["alert_prior"], 300)
        self.assertEqual(payload["custom_tts"], "Sắp họp")
        self.assertEqual(payload["timezone"], "Asia/Ho_Chi_Minh")
        self.assertEqual(payload["executor"], "vn_south")
        self.assertIn("start_date", payload)
        self.assertIn("start_time", payload)
        self.assertNotIn("devices", payload)

    def test_update_accepts_status_only_and_rejects_empty_update(self):
        self.assertEqual(self.update(status="2"), {"executor": "vn_south", "status": 2})
        with self.assertRaises(self.error) as error:
            self.update()
        self.assertEqual(error.exception.code, "invalid_reminder_update")
        with self.assertRaises(self.error) as error:
            self.update(status=9)
        self.assertEqual(error.exception.code, "invalid_reminder_status")

    def test_flatten_reads_camel_case_list_and_sorts(self):
        groups = [
            {
                "date": "2026-11-02",
                "listReminders": [
                    {
                        "id": "9",
                        "event": "Sau",
                        "start_date": "2026-11-02",
                        "start_time": "09:00:00",
                        "timezone": "Asia/Ho_Chi_Minh",
                        "frequency": "once",
                        "completed": 0,
                        "status": 1,
                        "alert_prior": 600,
                        "custom_tts": "Sau",
                        "devices": ["speaker-one", 7],
                    },
                    {"id": None, "event": "bỏ"},
                ],
            },
            {
                "listReminders": [
                    {
                        "id": 3,
                        "reminder": "Trước",
                        "start_date": "2026-11-01",
                        "start_time": "08:30:00",
                    }
                ]
            },
            {"date": "2026-11-03"},
        ]
        result = self.flatten(groups)
        self.assertEqual([item["id"] for item in result], [3, 9])
        self.assertEqual(result[0]["event"], "Trước")
        self.assertEqual(result[0]["frequency"], "once")
        self.assertEqual(result[0]["start_at"], "2026-11-01T08:30:00+07:00")
        self.assertEqual(result[1]["devices"], ["speaker-one"])
        self.assertEqual(result[1]["alert_prior_minutes"], 10)

    def test_flatten_ignores_invalid_start_but_keeps_record(self):
        result = self.flatten(
            [{"listReminders": [{"id": 1, "event": "x", "start_date": "bad"}]}]
        )
        self.assertEqual(result[0]["start_at"], None)


def validate_reminders() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReminderTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    return [] if result.wasSuccessful() else [output.getvalue()]


if __name__ == "__main__":
    unittest.main()
