# Implementation plan

## Block 1 — Goal

The goal of this layer is to rebuild Markdown samples so that they resemble real instruction files for coding agents.
Practical files should be long enough, because short prompts do not represent a real `AGENTS.md` or `CLAUDE.md` file.
The comparison must remain fair: Russian and English variants must preserve the same meaning.
The mixed sample must be a separate scenario and must not replace strict RU/EN comparison.

## Block 2 — Expected outputs

The layer must produce a revised set of Markdown samples.
Each practical sample should contain more than 150 lines and fewer than 300 lines.
The files should resemble real project instruction files rather than artificial paragraphs.
The output should include strict RU/EN pairs and one mixed/EN pair.

## Block 3 — Input files

Expected strict pairs:

- `dev_prompt_ru.md` and `dev_prompt_en.md`.
- `system_prompt_ru.md` and `system_prompt_en.md`.
- `project_rules_ru.md` and `project_rules_en.md`.
- `flores_ru.md` and `flores_en.md`.

Expected mixed pair:

- `implementation_plan_mixed.md`.
- `implementation_plan_en.md`.

## Block 4 — Repository commands

Run all commands from the repository root.
Use the existing virtual environment.
Do not install dependencies globally.

```bash
cd ~/research/tokenization
source .venv/bin/activate
python scripts/count_openai_tiktoken.py
```

The script should write the CSV file to `results/openai_tiktoken_counts.csv`.
The script should write metadata to `results/openai_tiktoken_counts_metadata.json`.

## Block 5 — Rules for Markdown samples

Files should use realistic Markdown formatting.
They should include first-level and second-level headings.
They should include lists, inline code, and small fenced code blocks.
They should not contain long literary paragraphs.
Each file should look like a working instruction file, not an essay.
Russian and English strict samples should have a similar structure.

## Block 6 — Counting rules

The tokenizer script must count Markdown files by default.
The script must ignore old `.txt` samples unless explicitly configured otherwise.
Strict RU/EN and mixed/EN comparisons must be reported separately.
The CSV must include `comparison`, `source_format`, and `comparison_ratio`.
The metadata must list all discovered sample pairs.

## Block 7 — Mixed-block equivalent

This block is the English-only equivalent of the mixed block in the comparison file.
The purpose is to model the same developer note without switching languages.
First check `git status --short`, then run `python scripts/count_openai_tiktoken.py`, then compare the `ru_en` and `mixed_en` ratios.
If `mixed_en` is close to `1.0`, do not make a dramatic claim; record the observation and keep the methodology honest.
After this block, the remaining sections continue in English only.

## Block 8 — Verification checklist

- Verify that every practical Markdown file has more than 150 lines.
- Verify that no practical Markdown file has more than 300 lines.
- Verify that strict RU/EN files have matching sections.
- Verify that the mixed file alternates language blocks.
- Verify that only one block contains mixed Russian-English prose.
- Verify that the English comparison file preserves the meaning.

## Block 9 — Limitations

This layer does not count Claude.
This layer does not count Gemini.
This layer does not calculate cost.
This layer does not evaluate response quality.
This layer does not prove the final article thesis.
It only prepares more realistic input Markdown files.

## Block 10 — Failure handling

If the script fails, collect the full traceback.
Do not move to the next layer until the failure is understood.
Check file paths first.
Then check the virtual environment.
Then check the expected file extensions.
Then check the CSV field names.

## Block 11 — What to save

Save the revised samples in `data/samples/`.
Save the updated counting script in `scripts/`.
Save the layer note in the project root or in `docs/layers/`.
Save the generated CSV in `results/`, but review it before commit.
Do not save secrets or raw corpus files without checking dataset terms.

## Block 12 — Final response format

The final response should include a compact table.
The table should show sample name, comparison type, encoding, baseline tokens, compared tokens, and ratio.
The response should not overinterpret the numbers.
The response should identify the next layer only after the current one is verified.

## Block 13 — Completion criteria

The layer is complete if the Markdown samples are rebuilt.
The layer is complete if line count is within the required range.
The layer is complete if the mixed sample does not mix languages chaotically.
The layer is complete if the counting script runs successfully.
The layer is complete if the result table can be inserted into the layer result note.

## Block 14 — Next step

After this layer, rerun the OpenAI tokenizer measurement.
Then regenerate the Layer 02 result note.
Only after that move to Claude official token counting.
Do not start the Claude layer until the Markdown samples are accepted.
The article should be built from stable inputs, not from temporary drafts.

