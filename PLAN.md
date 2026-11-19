# PLAN — Синхронный переводчик с AR

## Этап 0. Инфраструктура
- [x] Создать `PLAN.md` и структуру пакетов
- [x] `pyproject.toml` с зависимостями (sounddevice, numpy, faster-whisper, httpx, edge-tts, fastapi, uvicorn, opencv-python, pytest)
- [x] `translator/config.py` — конфиг через env-переменные
- [x] `translator/logging_setup.py` — единая настройка логирования

## Этап 1. MVP: базовый перевод речи
- [x] **Шаг 1.1.** Захват аудио с микрофона → WAV (`translator/audio/recorder.py`) + тест
- [x] **Шаг 1.2.** STT через `faster-whisper` (`translator/stt/whisper_stt.py`) + тест с моком
- [x] **Шаг 1.3.** Перевод через DeepSeek API (`translator/translate/deepseek.py`) + тест с моком httpx
- [x] **Шаг 1.4.** TTS через `edge-tts` (`translator/tts/edge_tts.py`) + тест
- [x] **Шаг 1.5.** CLI-пайплайн: запись → STT → перевод → TTS/текст
- [x] **Шаг 1.6.** История реплик в SQLite (`translator/history/store.py`) + тест

## Этап 2. Групповой режим
- [x] **Шаг 2.1.** Модель сессии: участники, роли (speaker/listener), языки (`translator/net/session.py`) + тест
- [x] **Шаг 2.2.** WebSocket-сервер на FastAPI (`translator/net/server.py`) + тест через TestClient
- [x] **Шаг 2.3.** Маршрутизация реплик: голос говорящего → перевод на язык каждого слушателя (в `server.py`)
- [x] **Шаг 2.4.** Вопросы из группы → перевод на язык основного говорящего (в `server.py`)
- [x] **Шаг 2.5.** История с авторством и временем (`server.py` + `GET /sessions/{id}/history`) + тест

## Этап 3. AR-режим
- [x] **Шаг 3.1.** Захват кадра с камеры (OpenCV) — `translator/ar/camera.py` + тест
- [x] **Шаг 3.2.** Распознавание текста (OCR) — `translator/ar/ocr.py` + тест
- [x] **Шаг 3.3.** Поиск/описание объекта и перевод на язык пользователя — `translator/ar/describe.py` + тест
- [x] **Шаг 3.4.** Вывод поверх кадра (overlay) — `translator/ar/overlay.py` + тест

## Этап 4. UX/UI (после AR)
- [x] **Шаг 4.1.** Веб-UI на FastAPI + HTML/JS поверх существующего WebSocket-сервера
      (`translator/net/static/index.html`, `GET /`, `/static`) + тест
- [x] **Шаг 4.2.** Страница AR-режима (камера браузера → кадр на сервер → overlay)
      (`translator/net/static/ar.html`, `POST /ar/frame`, `GET /ar`) + тест
- [x] **Шаг 4.3.** Редизайн UI: тёмная тема, стеклянные панели, нижняя навигация
      (`translator/net/static/styles.css`) — минимализм 2026
- [ ] (вне MVP) Мобильный клиент (React Native / Flutter) для AR с камерой телефона

## Этап 5. Сборка и документация
- [x] **Шаг 5.1.** Точка входа сервера `python -m translator.net` (`translator/net/__main__.py`)
- [x] **Шаг 5.2.** `README.md` — установка, конфигурация, запуск, тесты

## Этап 6. Полировка
- [x] **Шаг 6.1.** Прокинуть `source_lang` в OCR (`ObjectDescriber(ocr_factory=...)`) + тест
- [ ] **Шаг 6.2.** `session_id` в `HistoryStore` + фильтрация истории по сессии
- [x] **Шаг 6.3.** UI-полировка: тосты, анимации, safe-area (iPhone), тач-таргеты 44px,
      `prefers-reduced-motion`, iOS-фиксы (`-webkit-`, `font-size: 16px`)
- [x] **Шаг 6.4.** Микрофон в браузере: `MediaRecorder` → `POST /stt` → автозаполнение
      поля реплики; пульсирующий индикатор записи (`mic-btn.recording`)
- [x] **Шаг 6.5.** PWA: `manifest.webmanifest`, `sw.js`, `icon.svg`, регистрация SW
- [ ] **Шаг 6.6.** README: Tesseract-языки, `--reload`, PWA

## Правила
- Один шаг = одна маленькая функция + тест.
- После каждого шага обновляем этот файл.
- Если шаг дублируется — меняем подход.
