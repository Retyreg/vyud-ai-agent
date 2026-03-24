import os
import requests
import json
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

class PersonSearcher:
    def __init__(self, api_key: str = None, openai_client = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.url = "https://google.serper.dev/search"
        self.client = openai_client # Передаем клиент OpenAI для проверки

    def find_decision_maker(self, company_name: str, role: str, company_context: str = "") -> Optional[Dict]:
        """
        Ищет профили в LinkedIn и использует LLM, чтобы выбрать наиболее подходящего человека.
        """
        if not self.api_key:
            return None

        # Расширяем запрос для лучшего покрытия
        query = f'site:linkedin.com/in/ "{company_name}" "{role}"'
        
        payload = json.dumps({
            "q": query,
            "num": 8 # Берем топ-8 результатов для выбора
        })
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", self.url, headers=headers, data=payload)
            results = response.json().get('organic', [])
            
            if not results:
                return None

            # Если у нас есть клиент OpenAI, просим его выбрать лучшего кандидата
            if self.client:
                return self._verify_with_llm(results, company_name, role, company_context)
            
            # Если нет ИИ под рукой - берем первого (старый метод)
            first = results[0]
            return {
                "name": first.get('title', '').split(' - ')[0].split(' | ')[0],
                "title": role,
                "linkedin_url": first.get('link'),
                "relevance_reason": "Выбран автоматически (первый результат)"
            }

        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return None

    def _verify_with_llm(self, search_results: list, company_name: str, role: str, context: str) -> Optional[Dict]:
        """
        Отправляет результаты поиска ИИ, чтобы он выбрал живого и релевантного человека.
        """
        simplified_results = []
        for r in search_results:
            simplified_results.append({
                "title": r.get('title'),
                "link": r.get('link'),
                "snippet": r.get('snippet')
            })

        prompt = f"""
        Ты — эксперт по поиску талантов и Sales Intelligence.
        У нас есть компания "{company_name}" и мы ищем там человека на роль "{role}".
        
        Контекст компании: {context[:500]}
        
        Вот результаты поиска из LinkedIn:
        {json.dumps(simplified_results, ensure_ascii=False)}
        
        Твоя задача:
        1. Выбери наиболее подходящего и "живого" человека, который СЕЙЧАС работает в этой компании.
        2. Игнорируй вакансии, списки людей или бывших сотрудников (если в сниппете написано "was", "past", "ex-").
        3. Если никто не подходит на 100%, выбери ближайшего по смыслу (напр. Marketing Manager вместо Head of Marketing).
        
        Ответь ТОЛЬКО в формате JSON:
        {{
            "name": "Имя Фамилия",
            "title": "Точная должность из LinkedIn",
            "linkedin_url": "URL профиля",
            "relevance_reason": "Почему ты выбрал именно его (кратко)"
        }}
        Если никто не подходит совсем, верни null.
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={{ "type": "json_object" }}
            )
            return json.loads(response.choices[0].message.content)
        except:
            return None

if __name__ == "__main__":
    # Тест
    searcher = PersonSearcher()
    res = searcher.find_decision_maker("HubSpot", "Head of Marketing")
    print(res)
