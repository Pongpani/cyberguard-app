import json
import uuid
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase
from django.utils import timezone
from .engine import analyze_url
from .models import Scan, ScanFinding, RuleSet

class EngineTests(SimpleTestCase):
    def test_real_host_after_at(self):
        result = analyze_url("https://account.example@192.0.2.10/login")
        self.assertEqual(result["host"], "192.0.2.10")
        self.assertEqual(result["score"], 55)
        self.assertEqual(result["risk_level"], "medium")
    def test_at_in_query_and_path_does_not_hide_host(self):
        for url in ["https://example.com/?email=a@b.example", "https://example.com/a@b"]:
            self.assertNotIn("userinfo", [f["rule_code"] for f in analyze_url(url)["findings"]])
    def test_missing_scheme_not_penalized_as_http(self):
        result = analyze_url("example.com")
        self.assertFalse(result["scheme_supplied"])
        self.assertEqual(result["score"], 0)
    def test_http_is_not_implicit(self):
        self.assertEqual(analyze_url("http://example.com")["score"], 10)
    def test_idn_not_automatically_phishing(self):
        self.assertEqual(analyze_url("https://ตัวอย่าง.ไทย")["score"], 0)
    def test_reject_invalid_urls(self):
        for raw in ["", "hello", "javascript:alert(1)", "ftp://example.com", "https://",
                    "https://999.999.1.1", "https://bad..example", "https://example.com:99999",
                    "https://example.com\\@evil.example", "//example.com", "https://exam ple.com"]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                analyze_url(raw)
    def test_ipv6(self):
        self.assertEqual(analyze_url("https://[2001:db8::1]/")["score"], 30)

class APITests(TestCase):
    def send(self, url="https://account.example@192.0.2.10/login", key=None):
        return self.client.post("/api/scans/url/", {"url":url, "request_key":str(key or uuid.uuid4())}, content_type="application/json")
    def test_valid_scan_and_privacy(self):
        response = self.send()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Scan.objects.count(), 1)
        self.assertEqual(ScanFinding.objects.count(), 2)
        stored = json.dumps(list(Scan.objects.values()), default=str)
        self.assertNotIn("192.0.2.10", stored)
        self.assertNotIn("account.example", stored)
        self.assertNotIn("url", [f.name for f in Scan._meta.fields])
    def test_invalid_input_does_not_count(self):
        self.assertEqual(self.send("not a url").status_code, 400)
        self.assertEqual(Scan.objects.count(), 0)
    def test_repeated_request_does_not_count(self):
        key = uuid.uuid4()
        self.assertEqual(self.send(key=key).status_code, 201)
        self.assertEqual(self.send(key=key).status_code, 409)
        self.assertEqual(self.send(url="https://different.example", key=key).status_code, 409)
        self.assertEqual(Scan.objects.count(), 1)
    def test_new_request_for_same_url_counts(self):
        self.send(); self.send()
        self.assertEqual(Scan.objects.count(), 2)
    def test_transaction_rolls_back_if_findings_fail(self):
        with patch("scanner.views.ScanFinding.objects.bulk_create", side_effect=RuntimeError("test failure")):
            with self.assertRaises(RuntimeError):
                self.send()
        self.assertEqual(Scan.objects.count(), 0)
        self.assertEqual(RuleSet.objects.count(), 0)
    def test_empty_statistics(self):
        data = self.client.get("/api/statistics/").json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["daily"]), 7)
        self.assertEqual(data["findings"], [])
    def test_statistics_filter_and_no_join_overcount(self):
        self.send()
        self.send("https://example.com")
        data = self.client.get("/api/statistics/?type=url").json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["levels"]["medium"], 1)
        self.assertEqual(sum(row["count"] for row in data["daily"]), 2)
        self.assertEqual(self.client.get("/api/statistics/?type=message").json()["total"], 0)
    def test_date_validation(self):
        for query in ["start=bad", "start=2026-10-10&end=2026-10-01", "start=2020-01-01&end=2026-10-01", "type=bad"]:
            self.assertEqual(self.client.get("/api/statistics/?" + query).status_code, 400)
    def test_bangkok_day_boundary(self):
        self.send()
        from datetime import datetime, timezone as dtz
        Scan.objects.update(created_at=datetime(2026,10,8,18,0,tzinfo=dtz.utc))
        data = self.client.get("/api/statistics/?start=2026-10-09&end=2026-10-09").json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["daily"][0]["count"], 1)

