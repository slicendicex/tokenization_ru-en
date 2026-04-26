# Dev task instructions

## Назначение файла

Этот файл моделирует задачу, которую разработчик даёт coding agent в существующем репозитории.
Он не является глобальной памятью проекта и не заменяет `AGENTS.md` или `CLAUDE.md`.
Его задача — описать конкретное изменение, ограничения, проверки и формат результата.

## Context

Проект — CLI-инструмент для измерения токенизации Markdown-файлов.
Основной сценарий — сравнить русский, английский и mixed-language project instructions.
Код должен оставаться маленьким, воспроизводимым и пригодным для публикации вместе со статьёй.
Не нужно превращать этот слой в полноценный research framework.

## Goal

Добавь команду `count-openai`, которая считает токены в Markdown samples.
Команда должна использовать локальный OpenAI tokenizer через `tiktoken`.
Команда должна поддерживать `cl100k_base` и `o200k_base`.
Команда должна сохранять результат в `results/openai_tiktoken_counts.csv`.
Команда должна быть пригодна для повторного запуска без ручной очистки файлов.

## Non-goals

Не добавляй подсчёт Claude в этом слое.
Не добавляй подсчёт Gemini в этом слое.
Не добавляй расчёт стоимости в этом слое.
Не добавляй prompt caching в этом слое.
Не делай веб-интерфейс.
Не переписывай структуру проекта.
Не добавляй `pandas`, если стандартного `csv` достаточно.

## Input files

Скрипт должен читать Markdown-файлы из `data/samples/`.
Strict RU/EN пары имеют вид `*_ru.md` и `*_en.md`.
Mixed/EN пары имеют вид `*_mixed.md` и `*_en.md`.
FLORES sample может быть сгенерирован как `flores_ru.md` и `flores_en.md`.
Старые `.txt` samples не должны участвовать в основном запуске.

## Output files

Основной CSV должен лежать в `results/openai_tiktoken_counts.csv`.
Metadata должна лежать в `results/openai_tiktoken_counts_metadata.json`.
CSV должен быть перезаписываемым и детерминированным.
Metadata должна фиксировать дату запуска, версию `tiktoken` и список encodings.

## Required CSV columns

`sample_id` — имя sample без языкового суффикса.
`sample_type` — тип sample: corpus, agent_rules, system_prompt или implementation_plan.
`comparison` — тип сравнения: `ru_en` или `mixed_en`.
`language` — язык текущей строки: `en`, `ru` или `mixed`.
`source_format` — формат входного файла, сейчас `md`.
`encoding` — имя tokenizer encoding.
`char_count` — число Unicode characters.
`byte_count` — число UTF-8 bytes.
`word_count` — грубая оценка слов через whitespace split.
`line_count` — число строк в Markdown-файле.
`token_count` — число токенов.
`comparison_ratio` — отношение compared tokens к English baseline.

## Implementation constraints

Сохрани скрипт в `scripts/count_openai_tiktoken.py`.
Не добавляй скрытых network calls.
Не используй API keys.
Не меняй generated FLORES files.
Не коммить raw FLORES text, если условия датасета запрещают redistribution.
Пиши код так, чтобы его можно было прочитать в статье.
Раздели поиск файлов, группировку пар, подсчёт токенов и запись CSV.
Обрабатывай отсутствие FLORES как warning, а не как fatal error.

## Verification

После изменений запусти команду:

```bash
python scripts/count_openai_tiktoken.py
```

Затем проверь первые строки CSV:

```bash
head -n 10 results/openai_tiktoken_counts.csv
```

Потом выведи компактную Markdown-таблицу ratio.
В таблице должны быть строки для strict RU/EN и mixed/EN comparisons.
В таблице должны быть оба encodings: `cl100k_base` и `o200k_base`.

## Acceptance criteria

- Команда запускается из корня проекта.
- CSV создаётся без ручной подготовки папки `results/`.
- Markdown samples считаются по умолчанию.
- `.txt` samples не участвуют в основном измерении.
- Strict RU/EN и mixed/EN не смешиваются в одной метрике.
- В metadata видно, какие sample pairs были найдены.
- Если FLORES отсутствует, скрипт продолжает работу на practical samples.
- Код не требует внешних API.
- Код не требует сетевого доступа.
- Код не добавляет нерелевантных зависимостей.

## Final response format

В финальном ответе перечисли:

- изменённые файлы;
- созданные файлы;
- команды, которые были запущены;
- результат проверки;
- что не удалось проверить;
- оставшиеся методологические риски.

## Notes

Не делай финальных выводов для статьи на этом этапе.
Layer 02 фиксирует только raw tokenizer count.
Claude, Gemini, API usage и price будут отдельными слоями.
Если результат кажется неожиданным, сначала проверь входные Markdown files.

