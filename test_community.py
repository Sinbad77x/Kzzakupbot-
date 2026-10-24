import unittest
import json
from bot import app
import database

class CommunityTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        database.init_db()

    def test_get_topics_empty(self):
        response = self.client.get('/api/community/topics')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('topics', data)

    def test_post_topic_validation_error(self):
        # Короткий заголовок
        response = self.client.post('/api/community/topics', json={
            "title": "Короткий",
            "content": "Достаточно длинный текст для прохождения валидации содержимого темы.",
            "category": "Госзакупки"
        })
        self.assertEqual(response.status_code, 400)

    def test_post_topic_success(self):
        response = self.client.post('/api/community/topics', json={
            "title": "Успешное обсуждение налогов 2026",
            "content": "Обсуждаем применение пониженной ставки СНР 2% в Шымкенте.",
            "category": "Налоги и бухгалтерия"
        })
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('topic_id', data)

    def test_report_nonexistent_topic(self):
        response = self.client.post('/api/community/report/999999', json={
            "reason": "Спам в несуществующей теме"
        })
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
