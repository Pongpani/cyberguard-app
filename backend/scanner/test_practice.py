import json
import uuid
from unittest.mock import patch
from django.test import TestCase
from django.core.cache import cache
from django.core import signing
from .models import Scan, ScanFinding, RuleSet


class MessagePracticeTests(TestCase):
    def setUp(self):
        cache.clear()

    def post(self, path, data):
        return self.client.post('/api/' + path + '/', data, content_type='application/json')

    def test_message_summary_privacy_and_no_child_double_count(self):
        raw = 'PRIVATE-TEXT ด่วน ระงับ รหัสผ่าน https://example.com https://192.0.2.1'
        response = self.post('scans/message', {'message': raw, 'request_key': str(uuid.uuid4())})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['score'], 75)
        self.assertEqual(len(response.json()['links']), 2)
        self.assertEqual(Scan.objects.count(), 1)
        self.assertEqual(ScanFinding.objects.count(), 3)
        stored = json.dumps(list(Scan.objects.values()), default=str)
        self.assertNotIn('PRIVATE-TEXT', stored)
        self.assertNotIn('example.com', stored)

    def test_message_duplicate_does_not_count_twice(self):
        data = {'message': 'ด่วน', 'request_key': str(uuid.uuid4())}
        self.assertEqual(self.post('scans/message', data).status_code, 201)
        self.assertEqual(self.post('scans/message', data).status_code, 409)
        self.assertEqual(Scan.objects.count(), 1)

    def test_invalid_message(self):
        for value in ['', ' ', 123, 'x' * 5001]:
            self.assertEqual(self.post('scans/message', {'message': value, 'request_key': str(uuid.uuid4())}).status_code, 400)

    def test_practice_answers_hidden_until_submit(self):
        round = self.post('practice/start', {}).json()
        self.assertEqual(round['total'], 5)
        self.assertNotIn('answer', round['questions'][0])
        response = self.post('practice/submit', {'token': round['token'], 'answers': [1, 1, 2, 1, 0]})
        self.assertEqual(response.json()['score'], 5)
        self.assertEqual(Scan.objects.count(), 0)

    def test_incomplete_and_invalid_answers(self):
        token = self.post('practice/start', {}).json()['token']
        for answers in [[1], [1, 1, 2, 1, True], [1, 1, 2, 1, 9]]:
            self.assertEqual(self.post('practice/submit', {'token': token, 'answers': answers}).status_code, 400)

    def test_forged_and_expired_tokens(self):
        token = self.post('practice/start', {}).json()['token']
        self.assertEqual(self.post('practice/submit', {'token': token + 'bad', 'answers': [1]*5}).status_code, 400)
        with patch('django.core.signing.loads', side_effect=signing.SignatureExpired()):
            self.assertEqual(self.post('practice/submit', {'token': token, 'answers': [1]*5}).status_code, 400)

    def test_bank_change_invalidates_round(self):
        token = self.post('practice/start', {}).json()['token']
        with patch('scanner.views.practice_fingerprint', return_value='new-bank'):
            self.assertEqual(self.post('practice/submit', {'token': token, 'answers': [1]*5}).status_code, 400)

    def test_json_arrays_are_rejected(self):
        for path in ['scans/message', 'practice/submit']:
            self.assertEqual(self.post(path, []).status_code, 400)
