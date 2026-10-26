"""Offline URL-only assessment. Draft weights, not a calibrated probability."""
import ipaddress
import re
from urllib.parse import urlsplit
from .vendor.phishdetect.features import extract_features

VERSION = "url-draft-1"
REVISION = "cyberguard-local-v1"
RULES = [
    ("ip_host", 30, "ใช้ IP เป็นโฮสต์", "ตรวจสอบว่า IP นี้เป็นปลายทางที่คุณตั้งใจใช้งานหรือไม่"),
    ("userinfo", 25, "มีข้อมูลก่อน @ ในส่วนโฮสต์", "ปลายทางจริงอยู่หลัง @ ไม่ใช่ชื่อที่ปรากฏก่อนหน้า"),
    ("shortener", 15, "เป็นบริการย่อลิงก์", "ยังไม่ทราบปลายทางจริง ระบบไม่ได้เปิดหรือขยายลิงก์นี้"),
    ("long_url", 10, "URL ยาวตั้งแต่ 100 ตัวอักษร", "ลิงก์ยาวอาจอ่านยาก แต่ไม่ได้ยืนยันว่าเป็นฟิชชิง"),
    ("http", 10, "ระบุการเชื่อมต่อแบบ HTTP", "ข้อมูลในการเชื่อมต่อนี้ไม่ได้รับการเข้ารหัสด้วย HTTPS"),
]
CONFIGURATION = {"status": "draft", "medium_at": 35, "high_at": 65,
                 "rules": [{"code": c, "points": p, "title": t, "reason": r} for c, p, t, r in RULES]}

def analyze_url(raw):
    raw = raw.strip()
    if not raw or len(raw) > 2048:
        raise ValueError("กรุณากรอก URL ที่มีความยาวไม่เกิน 2,048 ตัวอักษร")
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 for ch in raw) or "\\" in raw:
        raise ValueError("URL ต้องไม่มีช่องว่าง อักขระควบคุม หรือ backslash")
    explicit = bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", raw))
    if raw.startswith("//"):
        raise ValueError("กรุณาระบุชื่อโฮสต์ หรือใช้ http:// หรือ https://")
    candidate = raw if explicit else "https://" + raw
    try:
        parts = urlsplit(candidate)
        if parts.scheme.lower() not in ("http", "https"):
            raise ValueError()
        host = parts.hostname
        if not host:
            raise ValueError()
        _ = parts.port
        host = host.rstrip(".")
        try:
            ipaddress.ip_address(host)
            is_ip = True
        except ValueError:
            is_ip = False
            if re.fullmatch(r"[0-9.]+", host):
                raise ValueError()
            ascii_host = host.encode("idna").decode("ascii")
            labels = ascii_host.split(".")
            if len(ascii_host) > 253 or len(labels) < 2:
                raise ValueError()
            if any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label) for label in labels):
                raise ValueError()
            if labels[-1].isdigit():
                raise ValueError()
    except (ValueError, UnicodeError):
        raise ValueError("รูปแบบ URL ไม่ถูกต้อง กรุณาตรวจชื่อเว็บไซต์และพอร์ต") from None
    # Upstream features are reusable; validation and scoring are ours.
    features = extract_features(candidate)
    signals = {"ip_host": is_ip, "userinfo": parts.username is not None,
               "shortener": bool(features["is_shortener"]),
               "long_url": len(raw) >= 100,
               "http": explicit and parts.scheme.lower() == "http"}
    findings = [{"rule_code": c, "points": p, "title": t, "reason": r}
                for c, p, t, r in RULES if signals[c]]
    score = min(100, sum(hit["points"] for hit in findings))
    level = "high" if score >= 65 else "medium" if score >= 35 else "low"
    return {"host": host, "scheme_supplied": explicit, "score": score,
            "risk_level": level, "findings": findings, "rule_version": VERSION,
            "advice": "เปิดบริการผ่านช่องทางที่รู้จัก และตรวจสอบปลายทางก่อนกรอกข้อมูล",
            "notice": "คะแนนตามกฎรุ่นทดลอง ไม่ใช่เปอร์เซ็นต์ และไม่รับรองความปลอดภัย"}

