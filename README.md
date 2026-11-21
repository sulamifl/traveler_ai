# Translator AR

Синхронный переводчик речи с групповым режимом и AR-режимом (распознавание
текста с камеры и перевод поверх кадра).

## Возможности

- **MVP:** запись с микрофона в браузере → STT (Groq Whisper API) → перевод (DeepSeek) → TTS (edge-tts).
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

### Языковые пакеты Tesseract

Tesseract распознаёт только те языки, для которых установлены пакеты.
Коды языков совпадают с ISO 639-2 (три буквы) и используются в UI
(`source_lang` на странице `/ar`).

| Язык | Код | Пакет (Debian/Ubuntu) |
|---|---|---|
| English | `eng` | `tesseract-ocr-eng` |
| Русский | `rus` | `tesseract-ocr-rus` |
| Deutsch | `deu` | `tesseract-ocr-deu` |
| Français | `fra` | `tesseract-ocr-fra` |
| Español | `spa` | `tesseract-ocr-spa` |
| 中文 (упрощ.) | `chi_sim` | `tesseract-ocr-chi-sim` |
| 日本語 | `jpn` | `tesseract-ocr-jpn` |

Установка нужных языков (пример):

```bash
# Linux
sudo apt install tesseract-ocr-eng tesseract-ocr-rus tesseract-ocr-deu

# macOS (все языки сразу)
brew install tesseract-lang
```

Проверить установленные языки:

```bash
tesseract --list-langs
```

Если нужного языка нет в списке — OCR вернёт пустой результат
или ошибку. Выбирайте в UI (`/ar` → «Исходный (OCR)») только те языки,
которые установлены.

## Конфигурация

Все настройки — через переменные окружения (см. `translator/config.py`):

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | Ключ DeepSeek (обязателен для перевода) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | Базовый URL API |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Модель |
| `GROQ_API_KEY` | — | Ключ Groq (обязателен для STT) |
| `GROQ_MODEL` | `whisper-large-v3-turbo` | Модель Whisper на Groq |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Базовый URL Groq |
| `GROQ_TIMEOUT` | `60.0` | Таймаут запроса к Groq, сек |
| `HISTORY_DB_PATH` | `history.db` | Путь к SQLite |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

Ключ Groq можно получить бесплатно на https://console.groq.com/keys.

## Запуск

### CLI (один проход: STT → перевод → озвучка)

```bash
python -m translator.cli --audio recording.webm --target en --tts-out out.mp3
```

Запись с микрофона выполняется в браузере (MediaRecorder API) на странице `/`.

### Веб-сервер (групповой режим + AR)

```bash
python -m translator.net --host 0.0.0.0 --port 8000
```

Открыть в браузере:

- `http://127.0.0.1:8000/` — групповой чат
- `http://127.0.0.1:8000/ar` — AR-режим (камера браузера)

Для разработки удобно запускать с авто-перезагрузкой при изменении кода:

```bash
uvicorn translator.net.__main__:build_app --factory --reload --host 127.0.0.1 --port 8000
```

Флаг `--reload` перезапускает сервер при правках Python-файлов.
Изменения в `translator/net/static/*` подхватываются браузером после
обычного обновления страницы (Ctrl/Cmd+R).

## PWA (установка как приложение)

Веб-UI можно установить на телефон или десктоп как обычное приложение —
с иконкой на домашнем экране и офлайн-оболочкой.

- **Android / Chrome:** открыть `http://<host>:8000/` → меню «⋮» →
  «Установить приложение» / «Добавить на главный экран».
- **iOS / Safari:** открыть `http://<host>:8000/` → «Поделиться» →
  «На экран Домой».
- **Desktop / Chrome / Edge:** иконка установки в адресной строке.

Что кэшируется: HTML-оболочка (`/`, `/ar`), `styles.css`, `icon.svg`,
`manifest.webmanifest`. Service worker (`translator/net/static/sw.js`)
не кэширует WebSocket, `/stt` и `/ar/frame` — они всегда идут в сеть.

Офлайн работает только оболочка (интерфейс). Перевод, STT и OCR требуют
сети и запущенного сервера.

## Тесты

```bash
python -m pytest -q
```

## Структура

```
translator/
  stt/         — распознавание речи (Groq Whisper API)
  translate/   — перевод (DeepSeek)
  tts/         — синтез речи (edge-tts)
  history/     — SQLite-история
  net/         — WebSocket-сервер + веб-UI (микрофон и камера — в браузере)
  ar/          — OCR, описание, overlay
  config.py    — конфиг через env
  logging_setup.py
  pipeline.py  — STT → перевод → TTS
  cli.py       — CLI-точка входа
```

## Деплой на Render

Проект содержит `Dockerfile` и `render.yaml` для деплоя на Render
(бесплатный план). В Dockerfile устанавливаются системные зависимости
`tesseract-ocr` и `libglib2.0-0`.

Переменные окружения, которые нужно задать в Render:

- `DEEPSEEK_API_KEY` — ключ DeepSeek
- `GROQ_API_KEY` — ключ Groq (бесплатный)
