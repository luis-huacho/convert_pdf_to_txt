"""Utility functions for PDF2Docs CLI."""

import os
from pathlib import Path
from typing import List, Optional, Tuple


def detect_language_from_path(input_path: Path) -> Optional[str]:
    """Detect language from path structure (data/raw/es or data/raw/en)."""
    path_parts = input_path.parts

    # Look for language indicators in the path
    for i, part in enumerate(path_parts):
        if part == "raw" and i + 1 < len(path_parts):
            next_part = path_parts[i + 1]
            if next_part in ("es", "en"):
                return next_part

    # Check if path ends with es/ or en/
    if input_path.name in ("es", "en"):
        return input_path.name

    return None


def resolve_output_path(input_path: Path, language: str, output_ext: str) -> Path:
    """Resolve output path based on input path and language."""
    # Get the filename without extension
    stem = input_path.stem

    # Build output path: data/result/{language}/{filename}.{ext}
    output_dir = Path("data/result") / language
    return output_dir / f"{stem}.{output_ext}"


def ensure_directories_exist(paths: List[Path]) -> None:
    """Ensure all directories exist, create if necessary."""
    for path in paths:
        if path.suffix:  # It's a file, get parent directory
            path.parent.mkdir(parents=True, exist_ok=True)
        else:  # It's a directory
            path.mkdir(parents=True, exist_ok=True)


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    return file_path.stat().st_size / (1024 * 1024)


def validate_pdf_file(file_path: Path) -> Tuple[bool, str]:
    """Validate if file is a readable PDF."""
    if not file_path.exists():
        return False, "file_not_found"

    if file_path.suffix.lower() != ".pdf":
        return False, "not_pdf"

    if file_path.stat().st_size == 0:
        return False, "empty_file"

    return True, "valid"


def find_pdf_files(input_path: Path, pattern: Optional[str] = None) -> List[Path]:
    """Find all PDF files in the given path matching optional pattern."""
    if input_path.is_file():
        if input_path.suffix.lower() == ".pdf":
            return [input_path]
        return []

    if not input_path.is_dir():
        return []

    # Find all PDF files
    if pattern:
        pdf_files = list(input_path.glob(pattern))
    else:
        pdf_files = list(input_path.glob("*.pdf"))

    # Filter to only PDF files
    return [f for f in pdf_files if f.suffix.lower() == ".pdf"]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')

    # Ensure not empty
    if not filename:
        filename = "untitled"

    return filename


def normalize_text(text: str) -> str:
    """Normalize text by fixing line endings and encoding."""
    # Normalize line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove excessive whitespace but preserve paragraph breaks
    lines = text.split('\n')
    normalized_lines = []

    for line in lines:
        # Strip trailing whitespace but preserve intentional indentation
        line = line.rstrip()
        normalized_lines.append(line)

    return '\n'.join(normalized_lines)


def validate_language_code(lang: str) -> bool:
    """Validate language code."""
    return lang in ("es", "en")


def get_skip_reason(output_path: Path, file_size_mb: float, max_size_mb: int) -> Optional[str]:
    """Determine if file should be skipped and return reason."""
    if output_path.exists():
        return "already_done"

    if file_size_mb > max_size_mb:
        return "limit_exceeded"

    return None