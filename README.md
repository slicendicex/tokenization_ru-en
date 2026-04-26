# Tokenization premium: Russian vs English Markdown

This repository contains an experiment on how many tokens Russian, English, and
mixed-language Markdown instructions use in LLM agent workflows.

The central question is: **how much more expensive Russian Markdown is than
English Markdown in token count, and how that gap changes across tokenizers and
API token counters**.

The project does not claim that "Russian is always more expensive than English"
in one universal sense. It measures a narrower and more testable question: the
ratio between the token count of a Russian or mixed-language version and an
English baseline with the same intended meaning.

## What Is Measured

The project separates three measurement levels. They should not be merged into
one metric:

| Level                      | Meaning                                                        | Project status                         |
| :------------------------- | :------------------------------------------------------------- | :------------------------------------- |
| Raw tokenizer count        | Local token count from a specific tokenizer                    | Measured for OpenAI `tiktoken`         |
| Official API token count   | Official input-token counter from a specific model/API         | Measured for OpenAI and Gemini         |
| API usage / billable usage | Actual `usage` after a real request and possible billing usage | Not yet treated as the final metric    |

For that reason, the current tables should not be read as final request cost.
They compare tokenization and API-level input counts, not pricing.

## Why Markdown

Plain parallel text is useful as a neutral baseline, but LLM developers often
send models Markdown files rather than plain text: `AGENTS.md`, `CLAUDE.md`,
`README.md`, implementation plans, project rules, and layer docs.

These files contain more than natural language:

| Element                 | Example                                   |
| :---------------------- | :---------------------------------------- |
| Headings                | `## Verification`                         |
| Lists                   | `- Run tests before final response`       |
| Inline code             | `` `pytest` ``                            |
| File paths              | `scripts/count_openai_tiktoken.py`        |
| Commands                | `python scripts/count_openai_tiktoken.py` |
| English technical labels | `provider boundary`, `API usage`         |

Because of this, practical Markdown samples behave differently from ordinary
corpus prose: code-like elements and English technical terms reduce the share of
pure Russian text in the total input.

## Dataset

The experiment uses two kinds of data:

| Data type                   | What it tests                                  |
| :-------------------------- | :--------------------------------------------- |
| FLORES+ corpus baseline     | Neutral parallel RU/EN prose                   |
| Practical Markdown samples  | Files resembling real agent/context prompts    |

Practical samples:

| Sample                  | What it represents                            | Comparison              |
| :---------------------- | :-------------------------------------------- | :---------------------- |
| `dev_prompt`            | A task for a coding agent                     | `*_ru.md` vs `*_en.md`  |
| `project_rules`         | `AGENTS.md` / project-level rules             | `*_ru.md` vs `*_en.md`  |
| `system_prompt`         | A long system instruction                     | `*_ru.md` vs `*_en.md`  |
| `implementation_plan`   | A mixed-language implementation plan          | `*_mixed.md` vs `*_en.md` |
| `flores`                | Neutral corpus baseline                       | `*_ru.md` vs `*_en.md`  |

The mixed sample does not replace the strict RU/EN comparison. It is a separate
practical case where Russian explanations appear next to commands, file paths,
identifiers, and English engineering terms.

## Results Summary

`Ratio` shows how many times longer the compared file is than the English
baseline by token count.

| Sample                  | Comparison | OpenAI `cl100k_base` | OpenAI `o200k_base` | OpenAI current API | Gemini official | Claude |
| :---------------------- | :--------- | -------------------: | ------------------: | -----------------: | --------------: | :----- |
| `dev_prompt`            | `ru_en`    |               1.455x |              1.088x |             1.088x |          1.065x | TODO   |
| `project_rules`         | `ru_en`    |               1.573x |              1.140x |             1.139x |          1.112x | TODO   |
| `system_prompt`         | `ru_en`    |               1.792x |              1.154x |             1.153x |          1.111x | TODO   |
| `implementation_plan`   | `mixed_en` |               1.399x |              1.101x |             1.100x |          1.090x | TODO   |
| `flores`                | `ru_en`    |               2.492x |              1.463x |             1.463x |          1.400x | TODO   |

What stands out:

- The older OpenAI `cl100k_base` baseline shows the largest RU/EN gap.
- The newer OpenAI `o200k_base` sharply reduces the gap on Markdown samples.
- OpenAI current API input counts are almost identical to `o200k_base` ratios.
- Gemini official `countTokens` shows a slightly smaller gap than OpenAI current API.
- FLORES shows a larger gap than practical Markdown across all measured providers.

## Detailed Measurements

| Sample                  | Source              | Model / encoding     | EN tokens | RU / mixed tokens | Ratio  | Measurement level              |
| :---------------------- | :------------------ | :------------------- | --------: | ----------------: | -----: | :----------------------------- |
| `dev_prompt`            | OpenAI tiktoken     | `cl100k_base`        |     1,027 |             1,494 | 1.455x | local raw tokenizer count      |
| `dev_prompt`            | OpenAI tiktoken     | `o200k_base`         |     1,018 |             1,108 | 1.088x | local raw tokenizer count      |
| `dev_prompt`            | OpenAI current API  | `gpt-5.5`            |     1,024 |             1,114 | 1.088x | Responses input token count    |
| `dev_prompt`            | Gemini official     | `gemini-2.5-flash`   |     1,140 |             1,214 | 1.065x | official countTokens           |
| `project_rules`         | OpenAI tiktoken     | `cl100k_base`        |     1,098 |             1,727 | 1.573x | local raw tokenizer count      |
| `project_rules`         | OpenAI tiktoken     | `o200k_base`         |     1,094 |             1,247 | 1.140x | local raw tokenizer count      |
| `project_rules`         | OpenAI current API  | `gpt-5.5`            |     1,100 |             1,253 | 1.139x | Responses input token count    |
| `project_rules`         | Gemini official     | `gemini-2.5-flash`   |     1,193 |             1,327 | 1.112x | official countTokens           |
| `system_prompt`         | OpenAI tiktoken     | `cl100k_base`        |       877 |             1,572 | 1.792x | local raw tokenizer count      |
| `system_prompt`         | OpenAI tiktoken     | `o200k_base`         |       870 |             1,004 | 1.154x | local raw tokenizer count      |
| `system_prompt`         | OpenAI current API  | `gpt-5.5`            |       876 |             1,010 | 1.153x | Responses input token count    |
| `system_prompt`         | Gemini official     | `gemini-2.5-flash`   |       946 |             1,051 | 1.111x | official countTokens           |
| `implementation_plan`   | OpenAI tiktoken     | `cl100k_base`        |     1,074 |             1,503 | 1.399x | local raw tokenizer count      |
| `implementation_plan`   | OpenAI tiktoken     | `o200k_base`         |     1,072 |             1,180 | 1.101x | local raw tokenizer count      |
| `implementation_plan`   | OpenAI current API  | `gpt-5.5`            |     1,078 |             1,186 | 1.100x | Responses input token count    |
| `implementation_plan`   | Gemini official     | `gemini-2.5-flash`   |     1,204 |             1,312 | 1.090x | official countTokens           |
| `flores`                | OpenAI tiktoken     | `cl100k_base`        |     5,469 |            13,629 | 2.492x | local raw tokenizer count      |
| `flores`                | OpenAI tiktoken     | `o200k_base`         |     5,440 |             7,959 | 1.463x | local raw tokenizer count      |
| `flores`                | OpenAI current API  | `gpt-5.5`            |     5,446 |             7,965 | 1.463x | Responses input token count    |
| `flores`                | Gemini official     | `gemini-2.5-flash`   |     5,777 |             8,086 | 1.400x | official countTokens           |

## Interim Conclusion

Russian tokenization premium still exists, but its size depends on the
tokenizer, API counter, and text type.

On the neutral FLORES baseline, the gap remains visible:

| Measurement          | RU/EN ratio |
| :------------------- | ----------: |
| OpenAI current API   |      1.463x |
| Gemini official      |      1.400x |

On practical Markdown instructions, the gap is much smaller:

| Measurement          | Practical Markdown RU/EN range |
| :------------------- | ------------------------------: |
| OpenAI current API   |                  1.088x-1.153x |
| Gemini official      |                  1.065x-1.112x |

In other words, the claim "Russian is more expensive than English" needs
qualification. On ordinary parallel prose, the gap can be large. On
agent-oriented Markdown files with commands, file paths, inline code, and
English technical labels, it becomes substantially smaller.

## Project Structure

| Path                          | Purpose                                      |
| :---------------------------- | :------------------------------------------- |
| `data/samples/`               | Markdown samples for comparison              |
| `scripts/`                    | Data preparation and token counting scripts  |
| `results/`                    | Generated CSV and metadata summaries         |
| `requirements.txt`            | Python dependencies                          |

## Reproduce

```bash
python scripts/count_openai_tiktoken.py
python scripts/count_openai_current_model_input_tokens.py --models gpt-5.5 gpt-5.4 gpt-5.4-mini
python scripts/build_cross_model_summary.py
```

API-level measurements require the relevant provider keys in the environment.
API keys and local `.env` files should not be committed to Git.

## Work In Progress

This work is still in progress. Next steps:

- compare Claude official token count;
- check actual API usage on real requests;
- calculate pricing scenarios separately, including input/output tokens,
  caching, and the billing rules of specific models.
