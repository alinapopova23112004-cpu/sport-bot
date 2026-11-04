import os
import feedparser
import requests
from google import genai

# Читаем ключи из настроек GitHub Secrets
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

# RSS-ленты спортивных новостей
RSS_URLS = [
    "https://www.sports.ru/rss/main.xml",
    "https://www.championat.com/rss/news/football/",
]

HISTORY_FILE = "posted.txt"


def get_posted_links():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_posted_link(link, posted_links):
    posted_links.add(link)
    recent_links = list(posted_links)[-200:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for url in recent_links:
            f.write(url + "\n")


def find_new_article(posted_links):
    for rss_url in RSS_URLS:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            link = entry.get("link", "")
            if link and link not in posted_links:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                return title, summary, link
    return None, None, None


def rewrite_with_ai(title, summary):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = (
        "Ты — автор популярного спортивного Telegram-канала. "
        "Напиши уникальный, живой и динамичный пост на основе этой новости. "
        "Требования:\n"
        "- Сделай цепляющий заголовок в первой строке.\n"
        "- Перепиши суть своими словами без воды и штампов (1-2 коротких абзаца).\n"
        "- Добавь 2-3 подходящих по смыслу эмодзи.\n"
        "- В конце задай короткий вопрос подписчикам для вовлечения в комментарии.\n"
        "- Не используй разметку со звездочками (**), пиши чистым текстом.\n\n"
        f"Заголовок источника: {title}\n"
        f"Описание: {summary}"
    )
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
    )
    return response.text.strip()


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()


def main():
    posted_links = get_posted_links()
    title, summary, link = find_new_article(posted_links)

    if not link:
        print("Новых новостей пока нет.")
        return

    print(f"Обрабатываю новость: {title}")
    post_text = rewrite_with_ai(title, summary)
    send_to_telegram(post_text)
    save_posted_link(link, posted_links)
    print("Пост успешно опубликован в канал!")


if __name__ == "__main__":
    main()
