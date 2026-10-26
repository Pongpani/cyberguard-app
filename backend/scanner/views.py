from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import RuleSet, Scan, ScanFinding
from .engine import analyze_url, VERSION, REVISION, CONFIGURATION

def index(request):
    target = settings.FRONTEND_DIST / "index.html"
    if not target.exists():
        return JsonResponse({"detail": "Build frontend with npm run build, or open Vite on port 5173."})
    return FileResponse(target.open("rb"), content_type="text/html")

@api_view(["GET"])
def health(request):
    # Check database readiness, not just HTTP process liveness.
    Scan.objects.exists()
    return Response({"status": "ok", "version": VERSION})

class URLInput(serializers.Serializer):
    url = serializers.CharField(max_length=2048, trim_whitespace=True)
    request_key = serializers.UUIDField()

@api_view(["POST"])
def scan_url(request):
    form = URLInput(data=request.data)
    if not form.is_valid():
        return Response({"detail": "กรุณากรอก URL และรหัสคำขอให้ถูกต้อง", "errors": form.errors}, status=400)
    try:
        result = analyze_url(form.validated_data["url"])
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)
    with transaction.atomic():
        rules, _ = RuleSet.objects.get_or_create(version=VERSION, defaults={"configuration": CONFIGURATION, "code_revision": REVISION})
        scan, created = Scan.objects.get_or_create(request_key=form.validated_data["request_key"], defaults={
            "rule_set": rules, "input_type": "url", "score": result["score"], "risk_level": result["risk_level"]})
        if not created:
            # Never return an earlier request's result to a caller with its key.
            return Response({"detail": "คำขอนี้บันทึกแล้ว หากต้องการตรวจใหม่ให้กดเริ่มรายการใหม่", "code": "duplicate_request"}, status=409)
        ScanFinding.objects.bulk_create([ScanFinding(scan=scan, rule_code=f["rule_code"], points=f["points"]) for f in result["findings"]])
    return Response({**result, "recorded": True}, status=201)

@api_view(["GET"])
def statistics(request):
    today = timezone.localdate()
    try:
        start = date.fromisoformat(request.query_params.get("start", str(today - timedelta(days=6))))
        finish = date.fromisoformat(request.query_params.get("end", str(today)))
        if start > finish or (finish - start).days > 365:
            raise ValueError()
    except ValueError:
        return Response({"detail": "ช่วงวันที่ต้องถูกต้องและไม่เกิน 366 วัน"}, status=400)
    kind = request.query_params.get("type", "all")
    if kind not in ("all", "url", "message"):
        return Response({"detail": "ประเภทไม่ถูกต้อง"}, status=400)
    tz = ZoneInfo("Asia/Bangkok")
    scans = Scan.objects.filter(created_at__gte=datetime.combine(start, time.min, tz),
                                created_at__lt=datetime.combine(finish + timedelta(days=1), time.min, tz))
    if kind != "all":
        scans = scans.filter(input_type=kind)
    levels = {k: 0 for k in ["low", "medium", "high"]}
    levels.update({row["risk_level"]: row["count"] for row in scans.values("risk_level").annotate(count=Count("id"))})
    dates = {str(row["day"]): row["count"] for row in scans.annotate(day=TruncDate("created_at", tzinfo=tz)).values("day").annotate(count=Count("id"))}
    daily = [{"date": str(start + timedelta(days=i)), "count": dates.get(str(start + timedelta(days=i)), 0)}
             for i in range((finish-start).days+1)]
    findings = list(ScanFinding.objects.filter(scan__in=scans).values("rule_code").annotate(count=Count("id")).order_by("-count", "rule_code"))
    return Response({"total": sum(levels.values()), "levels": levels, "daily": daily, "findings": findings,
                     "start": str(start), "end": str(finish), "type": kind})

# Message assessment stores only its primary summary, never the input or child URLs.
MESSAGE_RULES = [
    ("urgency", 20, "เร่งให้ตัดสินใจ", ("ด่วน", "ทันที", "ภายในวันนี้", "urgent", "immediately")),
    ("secret", 30, "กล่าวถึงข้อมูลสำคัญ", ("รหัสผ่าน", "otp", "password", "เลขบัตร")),
    ("threat", 25, "ขู่ว่าจะระงับบริการ", ("ระงับ", "ปิดบัญชี", "suspend")),
    ("reward", 15, "อ้างรางวัลหรือสิทธิพิเศษ", ("รับรางวัล", "รับทุน", "ผู้โชคดี", "prize")),
]
@api_view(["POST"])
def scan_message(request):
    import re
    if not isinstance(request.data, dict):
        return Response({"detail":"รูปแบบข้อมูลไม่ถูกต้อง"}, status=400)
    text = request.data.get("message", "")
    if not isinstance(text, str) or not text.strip() or len(text) > 5000:
        return Response({"detail":"กรุณากรอกข้อความ 1–5,000 ตัวอักษร"}, status=400)
    try:
        import uuid
        key = uuid.UUID(str(request.data.get("request_key")))
    except ValueError:
        return Response({"detail":"รหัสคำขอไม่ถูกต้อง"}, status=400)
    text = text.strip()
    findings = []
    for code, points, title, words in MESSAGE_RULES:
        evidence = [word for word in words if word in text.lower()]
        if evidence:
            findings.append({"rule_code":code, "points":points, "title":title,
                "reason":"พบคำหรือรูปแบบ: " + ", ".join(evidence) + " — ต้องพิจารณาบริบทเพิ่มเติม"})
    score = min(100, sum(f["points"] for f in findings))
    level = "high" if score >= 65 else "medium" if score >= 35 else "low"
    links = []
    for url in dict.fromkeys(re.findall(r"https?://[^\s<>]+", text, flags=re.I)):
        url = url.rstrip(".,;!?)]}。、")
        try:
            links.append({"url":url, **analyze_url(url)})
        except ValueError:
            links.append({"url":url, "error":"รูปแบบลิงก์ไม่ถูกต้อง"})
    with transaction.atomic():
        rules, _ = RuleSet.objects.get_or_create(version="message-draft-1", defaults={
            "configuration":{"medium_at":35,"high_at":65,"rules":[{"code":c,"points":p,"title":t,"words":list(w)} for c,p,t,w in MESSAGE_RULES]},
            "code_revision":"cyberguard-message-v1"})
        scan, created = Scan.objects.get_or_create(request_key=key, defaults={
            "rule_set":rules,"input_type":"message","score":score,"risk_level":level})
        if not created:
            return Response({"detail":"คำขอนี้บันทึกแล้ว ให้เริ่มรายการใหม่", "code":"duplicate_request"}, status=409)
        ScanFinding.objects.bulk_create([ScanFinding(scan=scan, rule_code=f["rule_code"], points=f["points"]) for f in findings])
    return Response({"score":score,"risk_level":level,"findings":findings,"links":links,
        "recorded":True,"rule_version":"message-draft-1"},status=201)

# Short practice module: signed round pins the bank fingerprint. Answers stay server-side.
PRACTICE = [
    {"id":1,"prompt":"HTTPS ยืนยันได้หรือไม่ว่าเว็บไซต์ไม่ใช่เว็บหลอกลวง?",
     "options":["ได้ เว็บไซต์ HTTPS ปลอดภัยเสมอ","ไม่ได้ เว็บหลอกลวงก็ใช้ HTTPS ได้","ได้ ถ้ามีรูปแม่กุญแจ"],"answer":1,
     "explanation":"HTTPS เข้ารหัสการเชื่อมต่อ แต่ไม่ได้รับรองความซื่อสัตย์ของเจ้าของเว็บไซต์"},
    {"id":2,"prompt":"https://university.example.com มีโดเมนหลักใด?",
     "options":["university","example.com","university.example"],"answer":1,
     "explanation":"ในตัวอย่างนี้ example.com เป็นโดเมนหลัก ส่วน university เป็น subdomain"},
    {"id":3,"prompt":"ได้รับข้อความขู่ว่าจะปิดบัญชีและขอรหัสผ่าน ควรทำอย่างไร?",
     "options":["ส่งรหัสผ่านทันที","ส่งต่อให้เพื่อนกดลิงก์","ตรวจสอบผ่านช่องทางทางการที่รู้จัก"],"answer":2,
     "explanation":"ความเร่งด่วนเป็นสัญญาณที่ควรระวัง ให้ตรวจผ่านแอปหรือช่องทางที่รู้จักโดยตรง"},
    {"id":4,"prompt":"เมื่อไม่พบลิงก์ในรายชื่อฟิชชิง หมายความว่าอย่างไร?",
     "options":["ปลอดภัยแน่นอน","ยังสรุปไม่ได้ ต้องตรวจสอบเพิ่มเติม","เป็นเว็บไซต์ของรัฐบาล"],"answer":1,
     "explanation":"ข้อมูลอาจยังไม่ครอบคลุมลิงก์ใหม่ การไม่พบในรายการไม่รับรองความปลอดภัย"},
    {"id":5,"prompt":"ถ้าเผลอกรอกรหัสผ่านในเว็บปลอม ควรทำอย่างไร?",
     "options":["เปลี่ยนรหัสผ่านผ่านช่องทางจริงและตรวจสอบบัญชี","กรอกรหัสผ่านซ้ำอีกครั้ง","รอจนเกิดความเสียหาย"],"answer":0,
     "explanation":"เข้าแอปหรือเว็บจริงที่รู้จักเพื่อเปลี่ยนรหัสผ่าน ตรวจ session และติดต่อผู้ให้บริการเมื่อจำเป็น"},
]

@api_view(["POST"])
def practice_start(request):
    from django.core import signing
    import secrets
    token = signing.dumps({"version":1,"bank":practice_fingerprint(),"nonce":secrets.token_hex(16)}, salt="practice-v1")
    return Response({"token":token,"questions":[{k:q[k] for k in ("id","prompt","options")} for q in PRACTICE],
        "total":len(PRACTICE),"expires_in":3600})

def practice_fingerprint():
    import hashlib
    import json
    return hashlib.sha256(json.dumps(PRACTICE, sort_keys=True).encode()).hexdigest()


@api_view(["POST"])
def practice_submit(request):
    from django.core import signing
    if not isinstance(request.data, dict):
        return Response({"detail":"รูปแบบข้อมูลไม่ถูกต้อง"}, status=400)
    try:
        token = request.data.get("token", "")
        if not isinstance(token, str) or len(token) > 1000:
            raise signing.BadSignature()
        payload = signing.loads(token, salt="practice-v1", max_age=3600)
        if payload.get("version") != 1 or payload.get("bank") != practice_fingerprint():
            raise signing.BadSignature()
    except signing.BadSignature:
        return Response({"detail":"รอบฝึกหมดอายุหรือไม่ถูกต้อง กรุณาเริ่มใหม่"},status=400)
    answers = request.data.get("answers")
    if not isinstance(answers, list) or len(answers)!=len(PRACTICE) or any(
        type(a) is not int or a < 0 or a >= len(q["options"]) for a,q in zip(answers, PRACTICE)):
        return Response({"detail":"กรุณาตอบให้ครบทุกข้อ"},status=400)
    review = [{**q,"selected":a,"correct":a==q["answer"]} for a,q in zip(answers,PRACTICE)]
    return Response({"score":sum(q["correct"] for q in review),"total":len(review),"review":review})


