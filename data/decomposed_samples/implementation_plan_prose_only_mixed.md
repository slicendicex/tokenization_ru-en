Implementation plan

Блок 1 — Цель

Цель этого слоя — пересобрать Markdown samples так, чтобы они были похожи на реальные instruction files для coding agents.
Практические файлы должны быть достаточно длинными, потому что короткие prompts плохо отражают реальный или .
Сравнение должно оставаться честным: русский и английский варианты должны передавать один и тот же смысл.
Mixed sample должен быть отдельным сценарием и не должен заменять strict comparison.

Block 2 — Expected outputs

The layer must produce a revised set of Markdown samples.
Each practical sample should contain more than 150 lines and fewer than 300 lines.
The files should resemble real project instruction files rather than artificial paragraphs.
The output should include strict pairs and one pair.

Блок 3 — Входные файлы

Ожидаемые strict pairs:

и .
и .
и .
и .

Ожидаемый mixed pair:

.
.

Block 4 — Repository commands

Run all commands from the repository root.
Use the existing virtual environment.
Do not install dependencies globally.

The script should write the file to .
The script should write metadata to .

Блок 5 — Правила для Markdown samples

Файлы должны использовать реалистичную Markdown-разметку.
Нужны заголовки первого и второго уровня.
Нужны списки, inline code и небольшие fenced code blocks.
Не нужно писать длинные художественные абзацы.
Файл должен выглядеть как рабочая инструкция, а не как эссе.
Русский и английский strict samples должны иметь похожую структуру.

Block 6 — Counting rules

The tokenizer script must count Markdown files by default.
The script must ignore old samples unless explicitly configured otherwise.
Strict and comparisons must be reported separately.
The must include , , and .
The metadata must list all discovered sample pairs.

Блок 7 — Единственный смешанный блок

Этот блок intentionally mixes Russian explanation with English technical labels, but only here.
Задача блока — смоделировать real developer note, где человек пишет reasoning по-русски, но оставляет commands, filenames и engineering terms на английском.
Например: сначала проверь , потом run , затем compare and ratios.
Если почти равен , не делай громкий claim просто record the observation and keep the methodology honest.
После этого блока остальные разделы снова идут либо полностью на русском, либо полностью на английском.

Block 8 — Verification checklist

Verify that every practical Markdown file has more than 150 lines.
Verify that no practical Markdown file has more than 300 lines.
Verify that strict files have matching sections.
Verify that the mixed file alternates language blocks.
Verify that only one block contains mixed Russian-English prose.
Verify that the English comparison file preserves the meaning.

Блок 9 — Ограничения

Этот слой не считает Claude.
Этот слой не считает Gemini.
Этот слой не считает стоимость.
Этот слой не проверяет качество ответов.
Этот слой не доказывает финальный тезис статьи.
Он только готовит более реалистичные входные Markdown-файлы.

Block 10 — Failure handling

If the script fails, collect the full traceback.
Do not move to the next layer until the failure is understood.
Check file paths first.
Then check the virtual environment.
Then check the expected file extensions.
Then check the field names.

Блок 11 — Что сохранить

Сохрани revised samples в .
Сохрани updated counting script в .
Сохрани layer note в корне проекта или в .
Сохрани generated в , но проверь его перед commit.
Не сохраняй секреты и raw corpus files без проверки условий датасета.

Block 12 — Final response format

The final response should include a compact table.
The table should show sample name, comparison type, encoding, baseline tokens, compared tokens, and ratio.
The response should not overinterpret the numbers.
The response should identify the next layer only after the current one is verified.

Блок 13 — Критерии завершения

Слой завершён, если Markdown samples пересобраны.
Слой завершён, если line count находится в заданном диапазоне.
Слой завершён, если mixed sample не смешивает языки хаотично.
Слой завершён, если counting script успешно запускается.
Слой завершён, если result table можно вставить в layer result note.

Block 14 — Next step

After this layer, rerun the tokenizer measurement.
Then regenerate the Layer 02 result note.
Only after that move to Claude official token counting.
Do not start the Claude layer until the Markdown samples are accepted.
The article should be built from stable inputs, not from temporary drafts.
