import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('schedule', ROOT / 'custom_components/energy_ua_poltava/schedule.py')
schedule = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = schedule
spec.loader.exec_module(schedule)
TZ = timezone(timedelta(hours=2))
NOW = datetime(2026, 11, 20, 8, 59, tzinfo=TZ)

# Segments supplied from EnergyUA's redesigned 3.1 page.
HTML = '''<div class="timeline-inner" id="timelineInner">
<div class="timeline-track" id="timelineTrack" aria-label="Графік на 24 години">
<div class="timeline-segment status-green" title="00:00–04:00: Є світло" style="width: 16.6667%;"></div>
<div class="timeline-segment status-red" title="04:00–05:30: Немає світла" style="width: 6.25%;"></div>
<div class="timeline-segment status-green" title="05:30–10:00: Є світло" style="width: 18.75%;"></div>
<div class="timeline-segment status-red" title="10:00–12:00: Немає світла" style="width: 8.33333%;"></div>
<div class="timeline-segment status-green" title="12:00–16:00: Є світло" style="width: 16.6667%;"></div>
<div class="timeline-segment status-red" title="16:00–19:00: Немає світла" style="width: 12.5%;"></div>
<div class="timeline-segment status-green" title="19:00–22:00: Є світло" style="width: 12.5%;"></div>
<div class="timeline-segment status-red" title="22:00–24:00: Немає світла" style="width: 8.33333%;"></div>
</div><div id="timeMarker"><span>Зараз 08:59</span></div></div>'''

class ScheduleTests(unittest.TestCase):
    def test_supplied_timeline(self):
        periods = schedule.parse_schedule(HTML, NOW)
        self.assertEqual([(p.start.astimezone(TZ).strftime('%H:%M'), p.end.astimezone(TZ).strftime('%H:%M')) for p in periods], [('04:00','05:30'), ('10:00','12:00'), ('16:00','19:00'), ('22:00','00:00')])
        self.assertEqual(periods[-1].end.astimezone(TZ).day, 21)
        data = schedule.compute(periods, NOW, 10)
        self.assertEqual(data['countdown_hm'], '01:01')
        self.assertEqual(data['next_change_type'], 'off')
        self.assertFalse(data['in_outage'])

    def test_outage_and_pretrigger(self):
        periods = schedule.parse_schedule(HTML, NOW)
        data = schedule.compute(periods, NOW.replace(hour=11, minute=55), 10)
        self.assertTrue(data['in_outage'])
        self.assertTrue(data['pretrigger'])
        self.assertEqual(data['countdown_hm'], '00:05')
        self.assertEqual(data['next_change_type'], 'on')

    def test_date_from_page(self):
        html = '<p>Завтра 22.11.2026</p><p>Дата графіка <span>Сб. 21.11.2026</span></p>' + HTML
        self.assertEqual(schedule.parse_schedule(html, NOW)[0].start.astimezone(TZ).day, 21)

    def test_invalid_date(self):
        with self.assertRaises(schedule.ScheduleParseError):
            schedule.parse_schedule('<p>Дата графіка 31.11.2026</p>' + HTML, NOW)

    def test_empty_and_challenge_are_not_clear_days(self):
        for html in ['<div id="timelineTrack"></div>', '<title>Just a moment...</title>']:
            with self.subTest(html=html), self.assertRaises(schedule.ScheduleParseError):
                schedule.parse_schedule(html, NOW)

    def test_malformed_segment_is_not_silently_dropped(self):
        with self.assertRaises(schedule.ScheduleParseError):
            schedule.parse_schedule(HTML.replace('04:00–05:30:', 'broken:'), NOW)

    def test_all_green(self):
        self.assertEqual(schedule.parse_schedule(HTML.replace('status-red', 'status-green'), NOW), [])

    def test_empty_legacy_js_does_not_hide_timeline(self):
        self.assertEqual(len(schedule.parse_schedule('<script>const periods = [];</script>' + HTML, NOW)), 4)

    def test_legacy_js_today_and_tomorrow(self):
        import json
        start = NOW.replace(hour=22, minute=0)
        end = start + timedelta(hours=2)
        today = [{'time_from': start.timestamp(), 'time_to': end.timestamp(), 'status': 'red'}]
        tomorrow = [{'time_from': end.timestamp(), 'time_to': (end + timedelta(hours=2)).timestamp(), 'status': 'red'}]
        html = f'<script>const periods = {json.dumps(today)}; tomorrowPeriods = Object.values({json.dumps(tomorrow)});</script>'
        periods = schedule.parse_schedule(html, NOW)
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0].end - periods[0].start, timedelta(hours=4))

    def test_legacy_html(self):
        html = '<h4 class="ch_day_title">Відключення завтра</h4><div class="periods_items"><span>З <b>10:00</b> до <b>12:00</b></span></div>'
        periods = schedule.parse_schedule(html, NOW)
        self.assertEqual(periods[0].start.astimezone(TZ), NOW.replace(day=21, hour=10, minute=0))

if __name__ == '__main__':
    unittest.main()
