# AGENTS.md

## Project overview

Этот репозиторий содержит исследовательский проект для статьи о tokenization premium.
Проект измеряет, сколько токенов занимают Markdown-инструкции на русском и английском языке.
Главный результат проекта — воспроизводимые таблицы для статьи на Хабре.
Код должен быть простым, проверяемым и пригодным для чтения в статье.

## Repository layout

- `data/samples/` — входные Markdown samples.
- `scripts/` — одноцелевые scripts для подготовки данных и подсчёта токенов.
- `results/` — generated CSV и metadata.
- `article/` — черновики блоков будущей статьи.
- `docs/` — методологические notes и layer docs.
- `README.md` — краткая инструкция запуска.

## Setup commands

Используй Python virtual environment.
Не устанавливай зависимости глобально.
Базовая настройка:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Common commands

Подготовить FLORES samples:

```bash
python scripts/prepare_flores_plus.py --split dev --limit 200 --format md
```

Посчитать OpenAI tokenizers:

```bash
python scripts/count_openai_tiktoken.py
```

Проверить результат:

```bash
head -n 10 results/openai_tiktoken_counts.csv
cat results/openai_tiktoken_counts_metadata.json
```

## Scope rules

Сравниваются только русский и английский языки.
Другие языки не добавляй в собственные измерения.
FLORES используется как neutral parallel baseline.
Markdown practical samples используются как agent workflow baseline.
Mixed sample измеряется отдельно от strict RU/EN samples.

## Methodology rules

Не смешивай `raw tokenizer count` и `API usage`.
Не смешивай `official API token count` и `billable usage`.
Не используй `tiktoken` как proxy для Claude или Gemini.
Для Claude используй официальный token counting API.
Для Gemini используй официальный count tokens API.
Фиксируй дату запуска и версию библиотек.
Фиксируй tokenizer name или model name.
Фиксируй sample id, language и comparison type.

## Data rules

Практические samples должны быть Markdown files.
Не используй `.txt` для agent instruction samples.
Strict RU/EN samples должны сохранять один и тот же смысл.
Сохраняй похожую структуру разделов между RU и EN файлами.
Не делай английскую версию искусственно короче.
Не раздувай русскую версию ради красивого ratio.
Mixed file должен быть отдельным сценарием.
Mixed file не должен подменять strict RU/EN comparison.

## Generated data policy

Не коммить raw FLORES files, если условия датасета ограничивают redistribution.
Можно коммитить scripts подготовки данных.
Можно коммитить aggregated results после проверки.
Не коммить `.env`, API keys или local auth tokens.
Не коммить временные notebooks без необходимости.

## Code style

Пиши простой Python.
Предпочитай стандартную библиотеку, если она достаточна.
Не добавляй `pandas`, если задача решается через `csv`.
Разделяй parsing, counting и writing.
Не смешивай CLI parsing и business logic в одной большой функции.
Используй `pathlib.Path` для путей.
Используй `dataclass`, если структура строки становится длинной.
Держи output deterministic.

## Testing and verification

После изменения script запусти основной command.
Проверь, что CSV создан.
Проверь, что metadata создана.
Проверь, что strict RU/EN и mixed/EN не смешаны.
Проверь, что `.md` files считаются по умолчанию.
Проверь, что warning не скрывает fatal error.
Если проверка не запускалась, явно скажи об этом.

## Article writing rules

Не пиши финальный вывод до завершения измерений.
Каждый claim должен опираться на таблицу или источник.
Не утверждай, что русский всегда стоит в три раза дороже.
Не утверждай, что английский всегда лучше.
Не утверждай, что все русские prompts надо переводить.
Главная рекомендация должна быть условной и практической.
Данные должны идти раньше интерпретации.

## Security considerations

Не печатай токены доступа в logs.
Не сохраняй secrets в results.
Не добавляй network calls в raw tokenizer scripts.
Не отправляй samples во внешние API в OpenAI raw count layer.
Перед API layers проверь, какие данные реально уходят наружу.

## Git hygiene

Перед commit проверь `git status --short`.
Не добавляй generated raw corpus files.
Не добавляй `.venv/`.
Не добавляй cache directories.
Коммить layer docs, scripts и reviewed result notes.
Пиши commit message по смыслу слоя.

## Agent behavior

Работай узко.
Не делай broad refactor без запроса.
Не переписывай существующую методологию без обсуждения.
Если видишь риск, сначала опиши его.
Если нужен новый слой, предложи его как отдельный step.
Не исправляй несколько независимых проблем одним изменением.

## Final response expectations

В финальном ответе укажи changed files.
Укажи commands run.
Укажи generated outputs.
Укажи verification result.
Укажи what was not verified.
Укажи remaining risks.

## Important reminder

Этот проект строится от данных к статье.
Не подгоняй эксперимент под красивый тезис.
Если результат слабее ожиданий, это всё равно результат.
Если новый tokenizer почти выравнивает mixed prompt, зафиксируй это честно.
Если strict Russian остаётся дороже, тоже зафиксируй это честно.
