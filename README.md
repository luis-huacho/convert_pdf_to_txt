# PDF2Docs CLI Tool

A powerful CLI tool for converting PDF documents to text or Markdown format using [Docling](https://docling-project.github.io/docling/).

## Features

- **Multi-format output**: Convert PDFs to plain text (.txt) or Markdown (.md)
- **Language support**: Automatic language detection from folder structure (Spanish/English)
- **Smart processing**: Skip existing files, handle image-only PDFs, size limits
- **Parallel processing**: Multi-threaded conversion with progress tracking
- **Structured logging**: Comprehensive JSON logging with metrics
- **Table handling**: Preserve table structure in Markdown or convert to tab-delimited text
- **Configurable**: YAML configuration with CLI overrides

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .
```

## Quick Start

```bash
# Convert Spanish PDFs to text
pdf2docs --input data/raw/es --out-ext txt

# Convert English PDFs to Markdown
pdf2docs --input data/raw/en --out-ext md

# Convert specific file with language override
pdf2docs --input document.pdf --out-ext md --lang es
```

## Directory Structure

The tool expects this folder structure:

```
project_root/
└── data/
    ├── raw/
    │   ├── es/   # Spanish PDFs
    │   └── en/   # English PDFs
    └── result/
        ├── es/   # Spanish outputs
        └── en/   # English outputs
```

## Usage

```bash
pdf2docs --input <path> --out-ext <txt|md> [OPTIONS]
```

### Required Arguments

- `--input <path>`: PDF file or directory (data/raw/es or data/raw/en)
- `--out-ext <txt|md>`: Output format (txt or md)

### Optional Arguments

- `--lang <es|en>`: Language override
- `--pattern <glob>`: File pattern filter (e.g., "report_*.pdf")
- `--workers <N>`: Number of parallel workers (1-16, default: 4)
- `--backend <id>`: Docling backend identifier
- `--config <path>`: Custom configuration file
- `--log-file <path>`: Custom log file path
- `--quiet`: Disable progress display
- `--fail-fast`: Stop on first error

### Examples

```bash
# Process all PDFs in Spanish folder
pdf2docs --input data/raw/es --out-ext txt

# Process with custom pattern and workers
pdf2docs --input data/raw/en --out-ext md --pattern "scientific_*.pdf" --workers 8

# Process single file with language override
pdf2docs --input /path/to/document.pdf --out-ext txt --lang es

# Quiet processing with custom config
pdf2docs --input data/raw/es --out-ext md --quiet --config custom.yaml
```

## Configuration

Create a `config.yaml` file to customize behavior:

```yaml
limits:
  max_file_size_mb: 10
  max_pages: 500
  timeout_per_file_sec: 120

serialization:
  markdown:
    add_yaml_header: false
  text:
    table_delimiter: "\\t"

logging:
  level: INFO
  progress: true
  fail_fast: false
  workers: 4

docling:
  backend: auto
```

## Output Formats

### Text (.txt)
- Plain text with normalized line endings
- Tables converted to tab-delimited format
- UTF-8 encoding

### Markdown (.md)
- Preserves document structure
- Tables in Markdown format
- UTF-8 encoding

## Processing Logic

1. **Language Detection**: Automatic from folder path or manual override
2. **File Discovery**: Find PDFs matching optional pattern
3. **Skip Logic**: Skip if output exists or file exceeds limits
4. **Validation**: Check PDF readability and text content
5. **Conversion**: Extract text/structure using Docling
6. **Output**: Write formatted content to result folder

## Logging

Structured JSON logs are written to `logs/run-YYYYMMDD-HHMMSS.log` with:

- Processing metrics (duration, pages, characters)
- Skip reasons (already_done, image_only_pdf, limit_exceeded)
- Error details and categorization
- Final summary statistics

## Error Handling

Files are categorized as:
- **Converted**: Successfully processed
- **Skipped**: Already exists, image-only, or exceeds limits
- **Failed**: Processing errors or timeouts

## Requirements

- Python 3.12+
- Docling library
- Click, PyYAML, tqdm, pathlib2

## License

MIT License - see LICENSE file for details.