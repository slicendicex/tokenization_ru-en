# Dev task instructions

## File purpose

This file models a task that a developer gives to a coding agent inside an existing repository.
It is not a global project memory file and does not replace `AGENTS.md` or `CLAUDE.md`.
Its purpose is to describe one concrete change, its constraints, verification steps, and final response format.

## Context

The project is a CLI tool for measuring tokenization of Markdown files.
The main scenario is to compare Russian, English, and mixed-language project instructions.
The code should remain small, reproducible, and suitable for publishing together with the article.
Do not turn this layer into a full research framework.

## Goal

Add a `count-openai` command that counts tokens in Markdown samples.
The command must use the local OpenAI tokenizer through `tiktoken`.
The command must support `cl100k_base` and `o200k_base`.
The command must save the result to `results/openai_tiktoken_counts.csv`.
The command must be safe to rerun without manually cleaning output files.

## Non-goals

Do not add Claude token counting in this layer.
Do not add Gemini token counting in this layer.
Do not add cost calculation in this layer.
Do not add prompt caching in this layer.
Do not build a web interface.
Do not rewrite the project structure.
Do not add `pandas` if the standard `csv` module is enough.

## Input files

The script must read Markdown files from `data/samples/`.
Strict RU/EN pairs use the form `*_ru.md` and `*_en.md`.
Mixed/EN pairs use the form `*_mixed.md` and `*_en.md`.
The FLORES sample can be generated as `flores_ru.md` and `flores_en.md`.
Old `.txt` samples must not participate in the default run.

## Output files

The main CSV must be saved to `results/openai_tiktoken_counts.csv`.
The metadata file must be saved to `results/openai_tiktoken_counts_metadata.json`.
The CSV should be deterministic and safe to overwrite.
The metadata must record the run date, the `tiktoken` version, and the list of encodings.

## Required CSV columns

`sample_id` is the sample name without the language suffix.
`sample_type` is the sample type: corpus, agent_rules, system_prompt, or implementation_plan.
`comparison` is the comparison type: `ru_en` or `mixed_en`.
`language` is the language of the current row: `en`, `ru`, or `mixed`.
`source_format` is the input file format, currently `md`.
`encoding` is the tokenizer encoding name.
`char_count` is the number of Unicode characters.
`byte_count` is the number of UTF-8 bytes.
`word_count` is a rough whitespace-based word estimate.
`line_count` is the number of lines in the Markdown file.
`token_count` is the number of tokens.
`comparison_ratio` is the compared token count divided by the English baseline.

## Implementation constraints

Keep the script at `scripts/count_openai_tiktoken.py`.
Do not add hidden network calls.
Do not use API keys.
Do not modify generated FLORES files.
Do not commit raw FLORES text if the dataset terms restrict redistribution.
Write code that can be read and explained in the article.
Separate file discovery, pair grouping, token counting, and CSV writing.
Handle missing FLORES as a warning, not as a fatal error.

## Verification

After the changes, run:

```bash
python scripts/count_openai_tiktoken.py
```

Then inspect the first CSV rows:

```bash
head -n 10 results/openai_tiktoken_counts.csv
```

Then print a compact Markdown ratio table.
The table must include rows for strict RU/EN and mixed/EN comparisons.
The table must include both encodings: `cl100k_base` and `o200k_base`.

## Acceptance criteria

- The command runs from the repository root.
- The CSV is created without manually preparing the `results/` directory.
- Markdown samples are counted by default.
- `.txt` samples do not participate in the default measurement.
- Strict RU/EN and mixed/EN are not merged into one metric.
- The metadata shows which sample pairs were found.
- If FLORES is missing, the script continues with practical samples.
- The code does not require external APIs.
- The code does not require network access.
- The code does not add irrelevant dependencies.

## Final response format

In the final response, list:

- changed files;
- created files;
- commands that were run;
- verification result;
- what could not be verified;
- remaining methodological risks.

## Notes

Do not make final article conclusions at this stage.
Layer 02 records only raw tokenizer count.
Claude, Gemini, API usage, and price will be separate layers.
If a result looks surprising, verify the input Markdown files first.

