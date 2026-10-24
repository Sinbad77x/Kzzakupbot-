import unittest
import json
from unittest.mock import patch
from bot import app

class RealSearchTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_anonymous_search_returns_official_link(self):
        """Проверяет, что при отсутствии токена формируется корректный URL для перехода без поддельных лотов"""
        response = self.client.get('/api/search?q=бумага')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['status'], 'anonymous_mode')
        self.assertEqual(len(data['data']), 0)
        self.assertIn('zakup.gov.kz/ru/search/announce?search=%D0%B1%D1%83%D0%BC%D0%B0%D0%B3%D0%B0', data['official_url'])

    def test_samruk_search_returns_direct_portal_link(self):
        """Проверяет формирование ссылки на портал Самрук-Қазына"""
        response = self.client.get('/api/search?q=самрук')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['status'], 'samruk_direct')
        self.assertEqual(data['official_url'], 'https://zakup.sk.kz/#/ext/search')

    @patch('bot.GOSZAKUP_TOKEN', 'mock_valid_token')
    @patch('requests.post')
    def test_authenticated_search_with_mock_api(self, mock_post):
        """Тест взаимодействия с GraphQL API при наличии токена (используется mock)"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "data": {
                "TrdBuy": [
                    {
                        "id": 1001,
                        "numberAnno": "2026-99001",
                        "nameRu": "Поставка тестового оборудования",
                        "totalSum": 5000000.0,
                        "organizerNameRu": "Тестовый Заказчик РК",
                        "endDate": "2026-11-01"
                    }
                ]
            }
        }

        response = self.client.get('/api/search?q=оборудование')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']), 1)
        self.assertEqual(data['data'][0]['number'], '2026-99001')
        self.assertEqual(data['data'][0]['amount'], 5000000.0)

if __name__ == '__main__':
    unittest.main()
