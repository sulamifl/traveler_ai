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
