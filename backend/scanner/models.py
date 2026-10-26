import uuid
from django.db import models
from django.db.models import Q, F

class RuleSet(models.Model):
    version = models.CharField(max_length=40, unique=True)
    configuration = models.JSONField()
    code_revision = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

class Scan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_key = models.UUIDField(unique=True)
    rule_set = models.ForeignKey(RuleSet, on_delete=models.PROTECT)
    input_type = models.CharField(max_length=10)
    score = models.PositiveSmallIntegerField()
    risk_level = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["created_at"]), models.Index(fields=["input_type", "created_at"])]
        constraints = [
            models.CheckConstraint(condition=Q(score__lte=100), name="scan_score_range"),
            models.CheckConstraint(condition=Q(input_type__in=["url", "message"]), name="scan_type"),
            models.CheckConstraint(condition=Q(risk_level__in=["low", "medium", "high"]), name="scan_level"),
        ]

class ScanFinding(models.Model):
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name="findings")
    rule_code = models.CharField(max_length=80)
    points = models.PositiveSmallIntegerField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["scan", "rule_code"], name="unique_scan_rule")]

class Lesson(models.Model):
    slug = models.SlugField(unique=True, max_length=100)
    title = models.CharField(max_length=200)
    content = models.TextField()
    sources = models.JSONField(default=list)
    version = models.PositiveIntegerField(default=1)
    display_order = models.PositiveIntegerField(unique=True)
    is_published = models.BooleanField(default=False)

class Question(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.PROTECT)
    prompt = models.TextField()
    options = models.JSONField()
    correct_key = models.CharField(max_length=1)
    explanation = models.TextField()
    sources = models.JSONField(default=list)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(correct_key__in=list("ABCD")), name="question_key")]

class QuizRound(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access_token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, default="in_progress")
    total_questions = models.PositiveSmallIntegerField(default=10)
    score = models.PositiveSmallIntegerField(null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField(db_index=True)
    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(total_questions=10), name="quiz_ten_questions"),
            models.CheckConstraint(condition=Q(score__isnull=True) | Q(score__lte=F("total_questions")), name="quiz_score_range"),
            models.CheckConstraint(condition=Q(expires_at__gt=F("started_at")), name="quiz_expiry"),
            models.CheckConstraint(condition=(Q(status="in_progress", score__isnull=True, submitted_at__isnull=True) | Q(status="submitted", score__isnull=False, submitted_at__isnull=False)), name="quiz_status"),
        ]

class QuizRoundItem(models.Model):
    round = models.ForeignKey(QuizRound, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    position = models.PositiveSmallIntegerField()
    question_version = models.PositiveIntegerField()
    question_snapshot = models.JSONField()
    selected_key = models.CharField(max_length=1, null=True)
    is_correct = models.BooleanField(null=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["round", "position"], name="unique_round_position"),
            models.UniqueConstraint(fields=["round", "question"], name="unique_round_question"),
            models.CheckConstraint(condition=Q(position__gte=1, position__lte=10), name="quiz_position"),
            models.CheckConstraint(condition=Q(selected_key__isnull=True) | Q(selected_key__in=list("ABCD")), name="quiz_selected_key"),
        ]

