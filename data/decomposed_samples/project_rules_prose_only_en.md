Project overview

This repository contains a research project for an article about tokenization premium.
The project measures how many tokens Markdown instructions use in Russian and English.
The main output is a set of reproducible tables for a Habr article.
The code should remain simple, verifiable, and readable in the article.

Repository layout

contains input Markdown samples.
contains scripts for data preparation and token counting.
contains generated files and metadata.
contains draft sections for the future article.
contains methodology notes and layer documents.
contains a short run guide.

Setup commands

Use a Python virtual environment.
Do not install dependencies globally.
Basic setup:

Common commands

Prepare samples:

Count tokenizers:

Inspect the result:

Scope rules

Only Russian and English are compared.
Do not add other languages to the project measurements.
is used as the neutral parallel baseline.
Markdown practical samples are used as the agent workflow baseline.
The mixed sample is measured separately from strict samples.

Methodology rules

Do not merge with .
Do not merge with .
Do not use as a proxy for Claude or Gemini.
For Claude, use the official token counting .
For Gemini, use the official count tokens .
Record the run date and library versions.
Record the tokenizer name or model name.
Record sample id, language, and comparison type.

Data rules

Practical samples must be Markdown files.
Do not use for agent instruction samples.
Strict samples must preserve the same meaning.
Keep a similar section structure between and files.
Do not make the English version artificially shorter.
Do not inflate the Russian version to create a prettier ratio.
The mixed file must be a separate scenario.
The mixed file must not replace strict comparison.

Generated data policy

Do not commit raw files if dataset terms restrict redistribution.
It is fine to commit data preparation scripts.
It is fine to commit aggregated results after review.
Do not commit , keys, or local auth tokens.
Do not commit temporary notebooks unless necessary.

Code style

Write simple Python.
Prefer the standard library when it is enough.
Do not add if the task can be solved with .
Separate parsing, counting, and writing.
Do not mix parsing and business logic in one large function.
Use for paths.
Use if the output row structure becomes long.
Keep output deterministic.

Testing and verification

After changing a script, run the main command.
Check that the was created.
Check that the metadata was created.
Check that strict and are not merged.
Check that files are counted by default.
Check that a warning is not hiding a fatal error.
If verification was not run, say so explicitly.

Article writing rules

Do not write the final conclusion before measurements are complete.
Every claim must be supported by a table or a source.
Do not claim that Russian always costs three times more.
Do not claim that English is always better.
Do not claim that all Russian prompts must be translated.
The main recommendation must be conditional and practical.
Data must come before interpretation.

Security considerations

Do not print access tokens in logs.
Do not save secrets in results.
Do not add network calls to raw tokenizer scripts.
Do not send samples to external in the raw count layer.
Before layers, verify which data is actually sent outside.

Git hygiene

Before committing, check .
Do not add generated raw corpus files.
Do not add .
Do not add cache directories.
Commit layer docs, scripts, and reviewed result notes.
Write a commit message that matches the layer purpose.

Agent behavior

Work narrowly.
Do not perform a broad refactor without a request.
Do not rewrite the existing methodology without discussion.
If you see a risk, describe it first.
If a new layer is needed, propose it as a separate step.
Do not fix several independent problems in one change.

Final response expectations

In the final response, list changed files.
List commands run.
List generated outputs.
List verification result.
List what was not verified.
List remaining risks.

Important reminder

This project moves from data to article.
Do not fit the experiment to a nice thesis.
If the result is weaker than expected, it is still a result.
If the new tokenizer almost equalizes the mixed prompt, record that honestly.
If strict Russian remains more expensive, record that honestly.
