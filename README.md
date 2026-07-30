# Backend (FastAPI)

## Setup
1) `cp .env.example .env` и заполнить `DB_URL`, `BOT_TOKEN`, `FRONTEND_ORIGIN`, `FRONTEND_URL`
2) `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
3) `pip install -r requirements.txt`
4) Запуск API: `uvicorn main:app --reload`
5) Запуск бота: `python bot/bot.py`

## Auth
Все запросы из MiniApp должны присылать заголовок:
`X-Telegram-Init-Data: window.Telegram.WebApp.initData`
Бэкенд проверяет подпись по BOT_TOKEN.
