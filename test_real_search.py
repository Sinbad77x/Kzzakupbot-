import unittest
import json
from bot import app

class RealSearchTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_search_returns_no_fake_data_without_token(self):
        # Проверяем, что при отсутствии GOSZAKUP_TOKEN система НЕ выводит фиктивные лоты 2026-10101
        response = self.client.get('/api/search?q=бумага')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Гарантируем, что success == False и список лотов пуст
        self.assertFalse(data['success'])
        self.assertEqual(len(data['data']), 0)
        self.assertIn('official_url', data)

    def test_samruk_query_returns_direct_link(self):
        # Проверяем статус прямого перехода для Самрук-Казына
        response = self.client.get('/api/search?q=самрук')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertFalse(data['success'])
        self.assertEqual(data['status'], 'samruk_direct_only')
        self.assertEqual(len(data['data']), 0)

if __name__ == '__main__':
    unittest.main()
  
