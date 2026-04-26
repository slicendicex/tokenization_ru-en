Project overview

Этот репозиторий содержит исследовательский проект для статьи о tokenization premium.
Проект измеряет, сколько токенов занимают Markdown-инструкции на русском и английском языке.
Главный результат проекта — воспроизводимые таблицы для статьи на Хабре.
Код должен быть простым, проверяемым и пригодным для чтения в статье.

Repository layout

— входные Markdown samples.
— одноцелевые scripts для подготовки данных и подсчёта токенов.
— generated и metadata.
— черновики блоков будущей статьи.
— методологические notes и layer docs.
— краткая инструкция запуска.

Setup commands

Используй Python virtual environment.
Не устанавливай зависимости глобально.
Базовая настройка:

Common commands

Подготовить samples:

Посчитать tokenizers:

Проверить результат:

Scope rules

Сравниваются только русский и английский языки.
Другие языки не добавляй в собственные измерения.
используется как neutral parallel baseline.
Markdown practical samples используются как agent workflow baseline.
Mixed sample измеряется отдельно от strict samples.

Methodology rules

Не смешивай и .
Не смешивай и .
Не используй как proxy для Claude или Gemini.
Для Claude используй официальный token counting .
Для Gemini используй официальный count tokens .
Фиксируй дату запуска и версию библиотек.
Фиксируй tokenizer name или model name.
Фиксируй sample id, language и comparison type.

Data rules

Практические samples должны быть Markdown files.
Не используй для agent instruction samples.
Strict samples должны сохранять один и тот же смысл.
Сохраняй похожую структуру разделов между и файлами.
Не делай английскую версию искусственно короче.
Не раздувай русскую версию ради красивого ratio.
Mixed file должен быть отдельным сценарием.
Mixed file не должен подменять strict comparison.

Generated data policy

Не коммить raw files, если условия датасета ограничивают redistribution.
Можно коммитить scripts подготовки данных.
Можно коммитить aggregated results после проверки.
Не коммить , keys или local auth tokens.
Не коммить временные notebooks без необходимости.

Code style

Пиши простой Python.
Предпочитай стандартную библиотеку, если она достаточна.
Не добавляй , если задача решается через .
Разделяй parsing, counting и writing.
Не смешивай parsing и business logic в одной большой функции.
Используй для путей.
Используй , если структура строки становится длинной.
Держи output deterministic.

Testing and verification

После изменения script запусти основной command.
Проверь, что создан.
Проверь, что metadata создана.
Проверь, что strict и не смешаны.
Проверь, что files считаются по умолчанию.
Проверь, что warning не скрывает fatal error.
Если проверка не запускалась, явно скажи об этом.

Article writing rules

Не пиши финальный вывод до завершения измерений.
Каждый claim должен опираться на таблицу или источник.
Не утверждай, что русский всегда стоит в три раза дороже.
Не утверждай, что английский всегда лучше.
Не утверждай, что все русские prompts надо переводить.
Главная рекомендация должна быть условной и практической.
Данные должны идти раньше интерпретации.

Security considerations

Не печатай токены доступа в logs.
Не сохраняй secrets в results.
Не добавляй network calls в raw tokenizer scripts.
Не отправляй samples во внешние в raw count layer.
Перед layers проверь, какие данные реально уходят наружу.

Git hygiene

Перед commit проверь .
Не добавляй generated raw corpus files.
Не добавляй .
Не добавляй cache directories.
Коммить layer docs, scripts и reviewed result notes.
Пиши commit message по смыслу слоя.

Agent behavior

Работай узко.
Не делай broad refactor без запроса.
Не переписывай существующую методологию без обсуждения.
Если видишь риск, сначала опиши его.
Если нужен новый слой, предложи его как отдельный step.
Не исправляй несколько независимых проблем одним изменением.

Final response expectations

В финальном ответе укажи changed files.
Укажи commands run.
Укажи generated outputs.
Укажи verification result.
Укажи what was not verified.
Укажи remaining risks.

Important reminder

Этот проект строится от данных к статье.
Не подгоняй эксперимент под красивый тезис.
Если результат слабее ожиданий, это всё равно результат.
Если новый tokenizer почти выравнивает mixed prompt, зафиксируй это честно.
Если strict Russian остаётся дороже, тоже зафиксируй это честно.
