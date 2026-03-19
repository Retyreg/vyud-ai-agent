import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

class WebScraper:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        # Маскируемся под обычный браузер, чтобы сайты не блокировали нас сразу
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    def _clean_text(self, text: str) -> str:
        """Очищает текст от лишних пробелов, пустых строк и переносов."""
        # Заменяем множественные пробелы и переносы строк на одинарные
        cleaned = re.sub(r'\s+', ' ', text)
        return cleaned.strip()

    def scrape_url(self, url: str) -> str:
        """
        Скачивает HTML страницы и извлекает только полезный текст,
        удаляя скрипты, стили, меню и футеры (по возможности).
        """
        # Добавляем схему, если ее нет
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        try:
            print(f"🌐 Скрапинг URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Удаляем весь "мусор": скрипты, стили, svg, невидимые элементы
            for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
                element.extract()

            # 2. Извлекаем текст
            # get_text(separator=' ') вставляет пробел между тегами
            raw_text = soup.get_text(separator=' ')

            # 3. Чистим текст
            cleaned_text = self._clean_text(raw_text)
            
            # Ограничим размер текста, чтобы не выйти за лимиты токенов LLM
            # ~10 000 символов (около 2500 токенов) обычно достаточно для About Us
            max_chars = 10000
            if len(cleaned_text) > max_chars:
                print(f"⚠️ Текст слишком длинный ({len(cleaned_text)} символов). Обрезаем до {max_chars}.")
                cleaned_text = cleaned_text[:max_chars]

            return cleaned_text

        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при скачивании {url}: {e}")
            return ""

# ==========================================
# Пример использования
# ==========================================
if __name__ == "__main__":
    scraper = WebScraper()
    
    # Тестируем на каком-нибудь публичном B2B сайте
    test_url = "https://www.hubspot.com/our-story"
    result = scraper.scrape_url(test_url)
    
    if result:
        print("\n" + "="*40)
        print("📄 РЕЗУЛЬТАТ СКРАПИНГА (Первые 500 символов):")
        print("="*40)
        print(result[:500] + "...")
        print("="*40)
        print(f"Всего извлечено символов: {len(result)}")
