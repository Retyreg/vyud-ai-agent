import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ValidationError
import ast
import json
from openai import OpenAI
from scraper import WebScraper
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# 1. Загружаем системный промпт (наш "идеальный" CoT промпт)
def load_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "extractor_v1.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Ты эксперт по извлечению данных. Выведи JSON с полями company_name, tech_stack, found_signals, confidence_score."

# 2. Pydantic Модель (наша строгая схема данных)
class CompanyEnrichment(BaseModel):
    analysis_log: str = Field(description="Внутренний анализ и цепочка рассуждений (Chain of Thought)")
    company_name: Optional[str] = Field(None, description="Название компании")
    industry: Optional[str] = Field(None, description="Отрасль")
    found_signals: list[str] = Field(default_factory=list, description="Сигналы, найденные по запросу пользователя")
    tech_stack: list[str] = Field(default_factory=list, description="Список технологий")
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
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY не найден")
        
        self.client = OpenAI(api_key=self.api_key)
        self.system_prompt = load_prompt()
        self.scraper = WebScraper()

    def _parse_llm_json(self, llm_response: str) -> Optional[CompanyEnrichment]:
        try:
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}')
            if start_idx == -1 or end_idx == -1: return None
            json_str = llm_response[start_idx:end_idx+1]
            try:
                extracted_dict = ast.literal_eval(json_str)
            except:
                extracted_dict = json.loads(json_str)
            return CompanyEnrichment(**extracted_dict)
        except Exception as e:
            print(f"❌ Ошибка парсинга JSON: {e}")
            return None

    def analyze_company(self, text: str = None, url: str = None, research_keywords: str = "") -> Optional[CompanyEnrichment]:
        if url:
            text = self.scraper.scrape_url(url)
            if not text: return None
        if not text: return None
            
        print(f"🔍 Анализ с фокусом на: {research_keywords}")
        
        try:
            user_content = f"Проанализируй этот текст со страницы 'About Us':\n\n{text}"
            if research_keywords:
                user_content += f"\n\nОСОБЫЙ ФОКУС (найди информацию по этим темам): {research_keywords}"

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
            )
            return self._parse_llm_json(response.choices[0].message.content)
        except Exception as e:
            print(f"❌ Ошибка OpenAI: {e}")
            return None
