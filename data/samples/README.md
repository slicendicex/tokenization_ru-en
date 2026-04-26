# data/samples

Эта папка содержит входные тексты для замеров токенизации.

## Синтетические samples

Эти файлы созданы вручную и могут быть закоммичены:

```text
dev_prompt_ru.txt
dev_prompt_en.txt
project_rules_ru.txt
project_rules_en.txt
system_prompt_ru.txt
system_prompt_en.txt
```

Они нужны для практических dev-сценариев: coding agent, CLAUDE.md / AGENTS.md-like правила, system prompt.

## FLORES+ samples

Эти файлы должны быть сгенерированы локально:

```text
flores_ru.txt
flores_en.txt
flores_ru_en.jsonl
```

Не рекомендуется коммитить сырой FLORES+ текст в публичный репозиторий. Лучше коммитить скрипт подготовки и агрегированные результаты измерений.

Команда:

```bash
python scripts/prepare_flores_plus.py --split dev --limit 100
```
