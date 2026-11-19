# Translator AR

Синхронный переводчик речи с групповым режимом и AR-режимом (распознавание
текста с камеры и перевод поверх кадра).

## Возможности

- **MVP:** запись с микрофона → STT (faster-whisper) → перевод (DeepSeek) → TTS (edge-tts).
- **Групповой режим:** WebSocket-сессии, роли speaker/listener, каждый слушатель
  получает перевод на свой язык; вопросы из группы переводятся на язык говорящего.
- **История:** SQLite с автором, оригиналом, переводом, языками и временем.
- **AR-режим:** камера браузера → OCR (Tesseract) → перевод → overlay с bbox.
- **Веб-UI:** минималистичный интерфейс в стиле мобильного приложения (тёмная тема).

## Установка

```bash
pip install -e ".[stt,translate,tts,net,ar,dev]"
```

Для OCR нужен установленный Tesseract:

- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- macOS: `brew install tesseract tesseract-lang`
- Linux: `sudo apt install tesseract-ocr tesseract-ocr-all`

## Конфигурация

Все настройки — через переменные окружения (см. `translator/config.py`):

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | Ключ DeepSeek (обязателен для перевода) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | Базовый URL API |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Модель |
| `WHISPER_MODEL` | `small` | Размер модели Whisper |
| `WHISPER_DEVICE` | `auto` | `cpu` / `cuda` / `auto` |
| `HISTORY_DB_PATH` | `history.db` | Путь к SQLite |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

## Запуск

### CLI (один проход: запись → перевод → озвучка)

```bash
python -m translator.cli --target en --duration 5 --tts-out out.mp3
```

### Веб-сервер (групповой режим + AR)

```bash
python -m translator.net --host 0.0.0.0 --port 8000
```

Открыть в браузере:

- `http://127.0.0.1:8000/` — групповой чат
- `http://127.0.0.1:8000/ar` — AR-режим (камера браузера)

## Тесты

```bash
python -m pytest -q
```

## Структура

```
translator/
  audio/       — запись с микрофона
  stt/         — распознавание речи (faster-whisper)
  translate/   — перевод (DeepSeek)
  tts/         — синтез речи (edge-tts)
  history/     — SQLite-история
  net/         — WebSocket-сервер + веб-UI
  ar/          — камера, OCR, описание, overlay
  config.py    — конфиг через env
  logging_setup.py
  pipeline.py  — STT → перевод → TTS
  cli.py       — CLI-точка входа
```
