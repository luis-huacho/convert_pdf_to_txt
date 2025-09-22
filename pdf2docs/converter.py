"""Core PDF converter using Docling."""

import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

from .config import Config
from .utils import normalize_text


class PDFConverter:
    """Handles PDF conversion using Docling."""

    def __init__(self, config: Config):
        self.config = config
        self._converter = None

    def _get_converter(self) -> DocumentConverter:
        """Get or create DocumentConverter instance."""
        if self._converter is None:
            # Configure pipeline options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = False  # Only process PDFs with extractable text
            pipeline_options.do_table_structure = True

            # Set up format options
            format_options = {
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }

            self._converter = DocumentConverter(
                format_options=format_options
            )

        return self._converter

    def convert_pdf(self, pdf_path: Path, output_ext: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Convert PDF to text or markdown.

        Returns:
            Tuple of (success, result_info)
            result_info contains: content, pages_total, pages_with_text,
            char_count, duration_ms, status, error_reason
        """
        start_time = time.time()
        result_info = {
            'content': '',
            'pages_total': 0,
            'pages_with_text': 0,
            'char_count': 0,
            'duration_ms': 0,
            'status': 'failed',
            'error_reason': None
        }

        try:
            # Get converter
            converter = self._get_converter()

            # Convert document
            conversion_result = converter.convert(pdf_path)

            # Extract document
            doc = conversion_result.document

            # Count pages
            result_info['pages_total'] = len(doc.pages) if hasattr(doc, 'pages') and doc.pages else 1

            # Convert to target format
            if output_ext == 'md':
                content = doc.export_to_markdown()
            else:  # txt
                # For text, we'll use the markdown export and then convert
                content = doc.export_to_markdown()
                # Convert markdown tables to tab-delimited if needed
                content = self._convert_markdown_tables_to_tabs(content)

            # Normalize text
            content = normalize_text(content)
            result_info['content'] = content
            result_info['char_count'] = len(content)

            # Count pages with text
            result_info['pages_with_text'] = self._count_pages_with_text(doc)

            # Check if this is an image-only PDF
            if result_info['char_count'] == 0:
                result_info['status'] = 'skipped'
                result_info['error_reason'] = 'image_only_pdf'
                return False, result_info

            result_info['status'] = 'ok'
            return True, result_info

        except Exception as e:
            result_info['error_reason'] = str(e)
            result_info['status'] = 'failed'
            return False, result_info

        finally:
            # Calculate duration
            duration = time.time() - start_time
            result_info['duration_ms'] = int(duration * 1000)

    def _convert_to_text(self, doc) -> str:
        """Convert document to plain text with tab-delimited tables."""
        content_parts = []

        if hasattr(doc, 'pages') and doc.pages:
            for page in doc.pages:
                page_content = []

                # Process each element in the page
                if hasattr(page, 'elements') and page.elements:
                    for element in page.elements:
                        if hasattr(element, 'text') and element.text:
                            if hasattr(element, 'label') and element.label == 'table':
                                # Convert table to tab-delimited format
                                table_text = self._table_to_tab_delimited(element)
                                page_content.append(table_text)
                            else:
                                # Regular text content
                                page_content.append(element.text)

                if page_content:
                    content_parts.append('\n'.join(page_content))

        return '\n\n'.join(content_parts)

    def _convert_markdown_tables_to_tabs(self, markdown_content: str) -> str:
        """Convert markdown tables to tab-delimited format."""
        import re

        lines = markdown_content.split('\n')
        converted_lines = []
        in_table = False

        for line in lines:
            # Check if this line is a markdown table row
            if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
                # This is a table row
                in_table = True
                # Remove leading/trailing | and split by |
                cells = [cell.strip() for cell in line.strip()[1:-1].split('|')]
                # Join with tabs
                converted_lines.append('\t'.join(cells))
            elif in_table and line.strip().startswith('|') and '-' in line:
                # This is a table separator line in markdown, skip it
                continue
            else:
                # Regular line or end of table
                in_table = False
                converted_lines.append(line)

        return '\n'.join(converted_lines)

    def _table_to_tab_delimited(self, table_element) -> str:
        """Convert table element to tab-delimited text."""
        try:
            # If table has structured data, process it
            if hasattr(table_element, 'data') and table_element.data:
                rows = []
                for row in table_element.data:
                    if isinstance(row, list):
                        # Join row cells with tabs
                        row_text = '\t'.join(str(cell) for cell in row)
                        rows.append(row_text)
                return '\n'.join(rows)
            else:
                # Fallback to text content with tab delimiter
                text = getattr(table_element, 'text', '')
                # Replace common table separators with tabs
                text = text.replace('|', '\t').replace('  ', '\t')
                return text
        except Exception:
            # Fallback to raw text
            return getattr(table_element, 'text', '')

    def _count_pages_with_text(self, doc) -> int:
        """Count pages that contain extractable text."""
        # For now, if we got text content, assume we have text pages
        # This is a simplified approach to avoid API complexities
        try:
            markdown_content = doc.export_to_markdown()
            if markdown_content and markdown_content.strip():
                return len(doc.pages) if hasattr(doc, 'pages') and doc.pages else 1
            return 0
        except:
            return 0

    def validate_pdf_content(self, pdf_path: Path) -> Tuple[bool, str]:
        """
        Quick validation to check if PDF has extractable text.

        Returns:
            Tuple of (has_text, reason)
        """
        try:
            converter = self._get_converter()
            result = converter.convert(pdf_path)
            doc = result.document

            # Check if document has extractable text
            try:
                markdown_content = doc.export_to_markdown()
                if markdown_content and markdown_content.strip():
                    return True, "has_text"
                return False, "image_only_pdf"
            except:
                return False, "export_error"

        except Exception as e:
            return False, f"validation_error: {str(e)}"