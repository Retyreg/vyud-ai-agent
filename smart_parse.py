from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List, Optional
import json
import ast

# 1. Описываем схему данных с помощью Pydantic
class CompanyInfo(BaseModel):
    company_name: str = Field(description="Название компании")
    found_tools: List[str] = Field(default_factory=list, description="Найденные инструменты/технологии")
    confidence_score: float = Field(description="Уверенность модели в правильности извлеченных данных (от 0 до 1)")

    # Валидатор для проверки корректности confidence_score
    @field_validator('confidence_score')
    @classmethod
    def check_score(cls, v):
        if not (0 <= v <= 1):
            raise ValueError('Score must be between 0 and 1')
        return v

def smart_parse(llm_string: str) -> Optional[CompanyInfo]:
    """
    Извлекает JSON из текста ответа LLM и валидирует его с помощью Pydantic.
    """
    try:
        # 1. Извлекаем JSON из строки
        start_idx = llm_string.find('{')
        end_idx = llm_string.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("JSON не найден в строке")
            
        json_str = llm_string[start_idx:end_idx+1]
        
        # Используем ast.literal_eval для безопасного парсинга одинарных кавычек, 
        # которые LLM часто генерирует вместо двойных (как в test_input)
        try:
            extracted_dict = ast.literal_eval(json_str)
        except (ValueError, SyntaxError):
            # Fallback на стандартный json.loads, если кавычки нормальные
            extracted_dict = json.loads(json_str)

        # 2. Передаем словарь в модель Pydantic для валидации и создания объекта
        result = CompanyInfo(**extracted_dict)
        return result
        
    except ValidationError as e:
        print("\n❌ Ошибка валидации данных (Pydantic):")
        for error in e.errors():
            print(f"- Поле {error['loc'][0]}: {error['msg']}")
        return None
    except Exception as e:
        print(f"\n❌ Ошибка парсинга: {str(e)}")
        return None

if __name__ == "__main__":
    # Тестовая строка, имитирующая ответ LLM
    test_input = "Результат: { 'company_name': 'Shopware', 'found_tools': ['PHP', 'React'], 'confidence_score': 0.98 }"
    
    print("--- Тестируем smart_parse ---")
    parsed = smart_parse(test_input)
    if parsed:
        print(f"✅ Успех: Компания {parsed.company_name} использует {parsed.found_tools} (уверенность AI: {parsed.confidence_score})")

    print("\n--- Проверка встроенной валидации Pydantic ---")
    bad_input = "Результат: { 'company_name': 'Shopware', 'found_tools': ['PHP'], 'confidence_score': 1.5 }"
    smart_parse(bad_input)
