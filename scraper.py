import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

class WebScraper:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        # Тщательно маскируемся под реального пользователя (Chrome/Mac)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }

    def _clean_text(self, text: str) -> str:
        """Очищает текст от лишних пробелов, пустых строк и переносов."""
        # Заменяем множественные пробелы и переносы строк на одинарные
        cleaned = re.sub(r'[\r\n\s\t]+', ' ', text)
        return cleaned.strip()

    def scrape_url(self, url: str) -> str:
        """
        Скачивает HTML страницы и извлекает только полезный текст.
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url

        try:
            print(f"🌐 Скрапинг URL: {url}")
            # Создаем сессию, чтобы сохранять куки (некоторые сайты этого требуют)
            session = requests.Session()
            response = session.get(url, headers=self.headers, timeout=self.timeout)
            
            # Проверка на код блокировки
            if response.status_code == 403:
                print(f"❌ Доступ к {url} запрещен (403 Forbidden).")
                return ""
            
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Удаляем весь "мусор": скрипты, стили, svg, невидимые элементы
            for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside"]):
                element.extract()

            # 2. Извлекаем текст
            raw_text = soup.get_text(separator=' ')

            # 3. Чистим текст
            cleaned_text = self._clean_text(raw_text)
            
            # Если текст слишком короткий, вероятно, скрапинг не удался
            if len(cleaned_text) < 50:
                print(f"⚠️ Извлеченный текст слишком короткий ({len(cleaned_text)} симв.). Сайт может быть динамическим или заблокированным.")
                return ""

            max_chars = 10000
            if len(cleaned_text) > max_chars:
                print(f"⚠️ Текст слишком длинный ({len(cleaned_text)} символов). Обрезаем.")
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
