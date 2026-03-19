import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from agent import VyudAgent
from writer import VyudWriter

load_dotenv()

class LeadProcessor:
    def __init__(self, input_file: str = "leads.txt", output_file: str = "results.csv", max_workers: int = 3):
        self.input_file = input_file
        self.output_file = output_file
        self.max_workers = max_workers
        self.agent = VyudAgent()
        self.writer = VyudWriter()
        
        # Подготавливаем CSV файл (если его нет)
        if not os.path.exists(self.output_file):
            with open(self.output_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "URL", "Company Name", "Industry", "Tech Stack", 
                    "CRM Detected", "Confidence Score", "Email Draft"
                ])

    def get_urls(self) -> list[str]:
        """Читает список URL из файла, игнорируя пустые строки."""
        if not os.path.exists(self.input_file):
            print(f"⚠️ Файл {self.input_file} не найден.")
            return []
            
        with open(self.input_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def process_single_url(self, url: str) -> dict:
        """Полный цикл для одного лида: Парсинг -> Анализ -> Написание письма."""
        print(f"\n🚀 Начинаю работу с: {url}")
        
        # 1. Анализируем компанию (Извлекаем факты)
        enrichment = self.agent.analyze_company(url=url)
        
        if not enrichment:
            return {"url": url, "status": "failed", "error": "Не удалось проанализировать сайт"}
            
        # 2. Генерируем письмо (Превращаем факты в текст)
        email_draft = self.writer.generate_email(enrichment.model_dump())
        
        return {
            "url": url,
            "status": "success",
            "enrichment": enrichment,
            "email": email_draft
        }

    def save_result(self, result: dict):
        """Сохраняет один успешный результат в CSV."""
        if result["status"] == "success":
            e = result["enrichment"]
            
            with open(self.output_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    result["url"],
                    e.company_name or "Unknown",
                    e.industry or "Unknown",
                    ", ".join(e.tech_stack),
                    e.crm_detected or "None",
                    e.confidence_score,
                    result["email"]
                ])
            print(f"✅ Результат для {result['url']} сохранен в {self.output_file}")
        else:
            print(f"❌ Ошибка для {result['url']}: {result.get('error')}")

    def run_batch(self):
        """Запускает параллельную обработку всех лидов."""
        urls = self.get_urls()
        if not urls:
            return
            
        print(f"📥 Загружено лидов: {len(urls)}. Запускаю {self.max_workers} параллельных потоков...")
        
        # Используем ThreadPoolExecutor для параллельных HTTP-запросов и вызовов API
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Запускаем задачи
            future_to_url = {executor.submit(self.process_single_url, url): url for url in urls}
            
            # Обрабатываем результаты по мере их завершения (кто первый закончил, тот первый записался)
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    self.save_result(result)
                except Exception as exc:
                    print(f"💥 Критическая ошибка при обработке {url}: {exc}")

# ==========================================
# Запуск конвейера
# ==========================================
if __name__ == "__main__":
    processor = LeadProcessor(input_file="leads.txt", output_file="results.csv", max_workers=3)
    processor.run_batch()
    print(f"\n🎉 Пакетная обработка завершена. Проверьте файл {processor.output_file}")
