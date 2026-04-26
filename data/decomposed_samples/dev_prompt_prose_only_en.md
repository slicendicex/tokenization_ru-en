Dev task instructions

File purpose

This file models a task that a developer gives to a coding agent inside an existing repository.
It is not a global project memory file and does not replace or .
Its purpose is to describe one concrete change, its constraints, verification steps, and final response format.

Context

The project is a tool for measuring tokenization of Markdown files.
The main scenario is to compare Russian, English, and project instructions.
The code should remain small, reproducible, and suitable for publishing together with the article.
Do not turn this layer into a full research framework.

Goal

Add a command that counts tokens in Markdown samples.
The command must use the local tokenizer through .
The command must support and .
The command must save the result to .
The command must be safe to rerun without manually cleaning output files.

Non-goals

Do not add Claude token counting in this layer.
Do not add Gemini token counting in this layer.
Do not add cost calculation in this layer.
Do not add prompt caching in this layer.
Do not build a web interface.
Do not rewrite the project structure.
Do not add if the standard module is enough.

Input files

The script must read Markdown files from .
Strict pairs use the form and .
pairs use the form and .
The sample can be generated as and .
Old samples must not participate in the default run.

Output files

The main must be saved to .
The metadata file must be saved to .
The should be deterministic and safe to overwrite.
The metadata must record the run date, the version, and the list of encodings.

Required columns

is the sample name without the language suffix.
is the sample type: corpus, , , or .
is the comparison type: or .
is the language of the current row: , , or .
is the input file format, currently .
is the tokenizer encoding name.
is the number of Unicode characters.
is the number of -8 bytes.
is a rough word estimate.
is the number of lines in the Markdown file.
is the number of tokens.
is the compared token count divided by the English baseline.

Implementation constraints

Keep the script at .
Do not add hidden network calls.
Do not use keys.
Do not modify generated files.
Do not commit raw text if the dataset terms restrict redistribution.
Write code that can be read and explained in the article.
Separate file discovery, pair grouping, token counting, and writing.
Handle missing as a warning, not as a fatal error.

Verification

After the changes, run:

Then inspect the first rows:

Then print a compact Markdown ratio table.
The table must include rows for strict and comparisons.
The table must include both encodings: and .

Acceptance criteria

The command runs from the repository root.
The is created without manually preparing the directory.
Markdown samples are counted by default.
samples do not participate in the default measurement.
Strict and are not merged into one metric.
The metadata shows which sample pairs were found.
If is missing, the script continues with practical samples.
The code does not require external .
The code does not require network access.
The code does not add irrelevant dependencies.

Final response format

In the final response, list:

changed files
created files
commands that were run
verification result
what could not be verified
remaining methodological risks.

Notes

Do not make final article conclusions at this stage.
Layer 02 records only raw tokenizer count.
Claude, Gemini, usage, and price will be separate layers.
If a result looks surprising, verify the input Markdown files first.
