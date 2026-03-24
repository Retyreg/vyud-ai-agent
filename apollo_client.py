import os
import requests
import json
from typing import Optional, Dict, List
from dotenv import load_dotenv

load_dotenv()

class ApolloClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")
        self.base_url = "https://api.apollo.io/v1"
        self.headers = {
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key
        }

    def search_person(self, domain: str, role_title: str) -> Optional[Dict]:
        """
        Ищет человека в конкретной компании по домену и должности.
        """
        if not self.api_key:
            print("⚠️ APOLLO_API_KEY не найден.")
            return None

        url = f"{self.base_url}/people/search"
        
        # Очищаем домен от протокола
        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

        payload = {
            "api_key": self.api_key,
            "q_organization_domains": clean_domain,
            "person_titles": [role_title],
            "page": 1,
            "display_mode": "regular"
        }

        try:
            print(f"🚀 Apollo: Ищу {role_title} в {clean_domain}...")
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            people = data.get('people', [])
            
            if not people:
                # Если точно по должности не нашли, попробуем чуть шире (по ключевому слову)
                print(f"🔄 Никого не нашли по точному титулу, пробуем поиск по ключевому слову...")
                payload["q_person_title_keywords"] = [role_title]
                payload.pop("person_titles")
                response = requests.post(url, headers=self.headers, json=payload)
                people = response.json().get('people', [])

            if not people:
                return None

            # Берем первого самого подходящего
            p = people[0]
            
            return {
                "name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
                "title": p.get('title'),
                "linkedin_url": p.get('linkedin_url'),
                "email": p.get('email'), # Внимание: email может быть скрыт в зависимости от тарифа
                "relevance_reason": "Найдено в официальной базе Apollo.io"
            }

        except Exception as e:
            print(f"❌ Ошибка Apollo API: {str(e)}")
            return None

if __name__ == "__main__":
    # Тест
    client = ApolloClient()
    res = client.search_person("hubspot.com", "Head of Marketing")
    print(res)
