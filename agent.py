import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ValidationError
import ast
import json
from openai import OpenAI

# 1. Загружаем системный промпт (наш "идеальный" CoT промпт)
def load_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "extractor_v1.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Ты эксперт по извлечению данных. Выведи JSON с полями company_name, tech_stack, crm_detected, confidence_score."

# 2. Pydantic Модель (наша строгая схема данных)
class CompanyEnrichment(BaseModel):
    analysis_log: str = Field(description="Внутренний анализ и цепочка рассуждений (Chain of Thought)")
    company_name: Optional[str] = Field(None, description="Название компании")
    industry: Optional[str] = Field(None, description="Отрасль")
    tech_stack: list[str] = Field(default_factory=list, description="Список технологий")
    crm_detected: Optional[str] = Field(None, description="Найденная CRM")
    personalization_hooks: list[str] = Field(default_factory=list, description="Зацепки для письма")
    confidence_score: float = Field(description="Уверенность от 0.0 до 1.0")

    @field_validator('confidence_score')
    @classmethod
    def check_score(cls, v):
        if not (0 <= v <= 1):
            raise ValueError('Score must be between 0 and 1')
        return v

# 3. Основной класс Агента
class VyudAgent:
    def __init__(self, api_key: str = None):
        """
        Инициализируем агента. Ключ API берем из аргументов или переменных окружения.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY не найден. Передайте его в конструктор или задайте в .env")
        
        self.client = OpenAI(api_key=self.api_key)
        self.system_prompt = load_prompt()

    def _parse_llm_json(self, llm_response: str) -> Optional[CompanyEnrichment]:
        """
        Безопасно извлекает JSON из ответа модели и валидирует через Pydantic.
        """
        try:
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                print("❌ Ошибка: LLM не вернула JSON.")
                return None
                
            json_str = llm_response[start_idx:end_idx+1]
            
            # Пробуем ast (для одинарных кавычек), затем стандартный json
            try:
                extracted_dict = ast.literal_eval(json_str)
            except (ValueError, SyntaxError):
                extracted_dict = json.loads(json_str)

            # Валидация Pydantic
            return CompanyEnrichment(**extracted_dict)
            
        except ValidationError as e:
            print("\n❌ Ошибка валидации данных (Pydantic):")
            for error in e.errors():
                print(f"- Поле {error['loc'][0]}: {error['msg']}")
            return None
        except Exception as e:
            print(f"\n❌ Ошибка парсинга: {str(e)}")
            return None

    def analyze_company_text(self, text: str) -> Optional[CompanyEnrichment]:
        """
        Отправляет текст в OpenAI и возвращает структурированный объект.
        """
        print(f"🔍 Анализирую текст ({len(text)} символов)...")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", # Используем быструю и дешевую модель для MVP
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Проанализируй этот текст со страницы 'About Us':\n\n{text}"}
                ],
                temperature=0.1, # Низкая температура для предсказуемости
            )
            
            llm_output = response.choices[0].message.content
            print("✅ Ответ от LLM получен. Парсим...")
            
            return self._parse_llm_json(llm_output)

        except Exception as e:
            print(f"❌ Ошибка API OpenAI: {str(e)}")
            return None

# ==========================================
# Пример использования
# ==========================================
if __name__ == "__main__":
    # Для теста подставьте свой ключ сюда или в переменную окружения OPENAI_API_KEY
    # os.environ["OPENAI_API_KEY"] = "sk-proj-..."
    
    # Имитация текста "About Us", спарсенного с сайта
    sample_website_text = '''
    Welcome to DataFlow Logistics! We are a leading supply chain optimization company.
    We believe in data-driven decisions. Our team uses powerful tools like AWS for scalable 
    infrastructure and we have recently integrated our custom tracking dashboard with Salesforce 
    to better manage our enterprise client relationships. We are actively hiring Python developers 
    to improve our internal routing algorithms.
    '''
    
    # Попробуем запустить агента (если нет ключа, он выдаст понятную ошибку)
    try:
        agent = VyudAgent()
        result = agent.analyze_company_text(sample_website_text)
        
        if result:
            print("\n" + "="*40)
            print("🎯 РЕЗУЛЬТАТ РАБОТЫ VYUD AGENT:")
            print("="*40)
            print(f"🏢 Компания: {result.company_name}")
            print(f"💼 Отрасль: {result.industry}")
            print(f"🛠 Стек: {', '.join(result.tech_stack)}")
            print(f"📊 CRM: {result.crm_detected}")
            print(f"🪝 Зацепки: {result.personalization_hooks}")
            print(f"📈 Уверенность: {result.confidence_score}")
            print("\n🧠 Как мыслил агент (Chain of Thought):")
            print(result.analysis_log)
    except ValueError as e:
        print(f"\n⚠️ {e}")
        print("💡 Чтобы запустить тест по-настоящему, установите OPENAI_API_KEY.")
