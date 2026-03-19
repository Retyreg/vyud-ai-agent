import os
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class VyudWriter:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        
        # Загружаем промпт писателя
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "writer_v1.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            self.system_prompt = "Напиши персонализированное холодное письмо на основе данных компании."

    def generate_email(self, enrichment_data: dict) -> str:
        """
        Принимает словарь с данными компании и генерирует на его основе письмо.
        """
        print(f"✍️ Генерирую персонализированное письмо для {enrichment_data.get('company_name', 'клиента')}...")
        
        try:
            # Превращаем данные в JSON-строку для промпта
            import json
            data_str = json.dumps(enrichment_data, ensure_ascii=False, indent=2)

            response = self.client.chat.completions.create(
                model="gpt-4o", # Здесь мы используем дорогую и "умную" модель для качества текста
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Сгенерируй письмо на основе этих данных:\n\n{data_str}"}
                ],
                temperature=0.7, # Чуть выше температура для креативности в тексте
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ Ошибка при генерации письма: {str(e)}")
            return ""

# ==========================================
# Тестовый запуск вместе с Агентом
# ==========================================
if __name__ == "__main__":
    from agent import VyudAgent
    
    try:
        agent = VyudAgent()
        writer = VyudWriter()
        
        # 1. Анализируем сайт
        target_url = "https://www.hubspot.com/our-story"
        result = agent.analyze_company(url=target_url)
        
        if result:
            # 2. Генерируем письмо на основе данных
            email = writer.generate_email(result.model_dump())
            
            print("\n" + "="*50)
            print("🚀 ГОТОВОЕ ПЕРСОНАЛИЗИРОВАННОЕ ПИСЬМО:")
            print("="*50)
            print(email)
            print("="*50)
            
    except Exception as e:
        print(f"⚠️ Ошибка: {str(e)}")
