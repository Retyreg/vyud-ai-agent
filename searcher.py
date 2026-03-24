import os
import requests
import json
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

class PersonSearcher:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.url = "https://google.serper.dev/search"

    def find_decision_maker(self, company_name: str, role: str) -> Optional[Dict]:
        """
        Ищет профиль человека в LinkedIn через Google Serper API.
        """
        if not self.api_key:
            print("⚠️ SERPER_API_KEY не найден. Пропускаем поиск человека.")
            return None

        # Формируем точный запрос для Google
        query = f'site:linkedin.com/in/ "{company_name}" "{role}"'
        
        payload = json.dumps({
            "q": query,
            "num": 1 # Нам нужен только самый релевантный результат
        })
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            print(f"🔍 Ищу ЛПР: {role} в {company_name}...")
            response = requests.request("POST", self.url, headers=headers, data=payload)
            response.raise_for_status()
            
            results = response.json().get('organic', [])
            
            if not results:
                return None
                
            first_result = results[0]
            
            # Извлекаем имя из заголовка (обычно: "Имя Фамилия - Должность - Компания")
            title = first_result.get('title', '')
            name = title.split(' - ')[0].split(' | ')[0]
            
            return {
                "name": name,
                "title": role,
                "linkedin_url": first_result.get('link'),
                "relevance_reason": f"Наиболее релевантный профиль по запросу в LinkedIn"
            }

        except Exception as e:
            print(f"❌ Ошибка при поиске человека: {str(e)}")
            return None

if __name__ == "__main__":
    # Тест
    searcher = PersonSearcher()
    res = searcher.find_decision_maker("HubSpot", "Head of Marketing")
    print(res)
