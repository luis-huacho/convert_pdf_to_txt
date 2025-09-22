"""Main processing engine with parallelization and progress tracking."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple
import signal
import sys

from tqdm import tqdm

from .config import Config
from .converter import PDFConverter
from .logger import StructuredLogger
from .utils import (
    detect_language_from_path,
    resolve_output_path,
    ensure_directories_exist,
    get_file_size_mb,
    validate_pdf_file,
    find_pdf_files,
    get_skip_reason
)


class PDFProcessor:
    """Main processing engine for PDF conversion."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = StructuredLogger(config.logging)
        self.converter = PDFConverter(config)
        self._cancelled = False

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\nShutdown signal received. Finishing current tasks...")
        self._cancelled = True

    def process(
        self,
        input_path: Path,
        output_ext: str,
        language_override: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> bool:
        """
        Main processing function.

        Returns:
            bool: True if processing completed successfully, False if errors occurred
        """
        try:
            # Detect language
            if language_override:
                language = language_override
            else:
                language = detect_language_from_path(input_path)
                if not language:
                    self.logger.log_error(
                        f"Cannot determine language from path: {input_path}. "
                        f"Use --lang to specify language."
                    )
                    return False

            # Find PDF files
            pdf_files = find_pdf_files(input_path, pattern)
            if not pdf_files:
                self.logger.log_info(f"No PDF files found in {input_path}")
                return True

            self.logger.log_info(f"Found {len(pdf_files)} PDF files to process")

            # Ensure output directories exist
            output_dirs = [Path("data/result") / language]
            ensure_directories_exist(output_dirs)

            # Prepare file list with validation
            file_tasks = []
            for pdf_file in pdf_files:
                output_path = resolve_output_path(pdf_file, language, output_ext)
                file_size_mb = get_file_size_mb(pdf_file)

                # Check if file should be skipped
                skip_reason = get_skip_reason(
                    output_path,
                    file_size_mb,
                    self.config.limits.max_file_size_mb
                )

                if skip_reason:
                    # Log skip
                    self.logger.log_skip(
                        pdf_file,
                        output_path,
                        language,
                        skip_reason,
                        int(pdf_file.stat().st_size)
                    )
                    continue

                # Validate PDF file
                is_valid, reason = validate_pdf_file(pdf_file)
                if not is_valid:
                    self.logger.log_skip(
                        pdf_file,
                        output_path,
                        language,
                        f"invalid_pdf_{reason}",
                        int(pdf_file.stat().st_size)
                    )
                    continue

                file_tasks.append((pdf_file, output_path, language, output_ext))

            if not file_tasks:
                self.logger.log_info("No files to process after validation")
                self.logger.print_summary()
                return True

            # Process files
            success = self._process_files_parallel(file_tasks)

            # Print summary
            self.logger.print_summary()

            return success

        except Exception as e:
            self.logger.log_error(f"Processing failed: {e}")
            return False

    def _process_files_parallel(self, file_tasks: List[Tuple[Path, Path, str, str]]) -> bool:
        """Process files in parallel with progress tracking."""
        total_files = len(file_tasks)
        successful = 0
        failed = 0

        # Set up progress bar
        if self.config.logging.progress and not self._cancelled:
            pbar = tqdm(
                total=total_files,
                desc="Converting PDFs",
                unit="file",
                disable=False
            )
        else:
            pbar = None

        try:
            # Process with thread pool
            with ThreadPoolExecutor(max_workers=self.config.logging.workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(self._process_single_file, *task): task
                    for task in file_tasks
                }

                # Process completed tasks
                for future in as_completed(future_to_task):
                    if self._cancelled:
                        break

                    task = future_to_task[future]
                    input_file, output_file, language, output_ext = task

                    try:
                        success = future.result(timeout=self.config.limits.timeout_per_file_sec)
                        if success:
                            successful += 1
                        else:
                            failed += 1
                            if self.config.logging.fail_fast:
                                self.logger.log_error(f"Stopping on first failure: {input_file}")
                                break

                    except Exception as e:
                        failed += 1
                        self.logger.log_error(f"Task failed for {input_file}: {e}")

                        # Log as failed
                        self.logger.log_processing_result(
                            input_file,
                            output_file,
                            language,
                            {
                                'status': 'failed',
                                'error_reason': f"task_error: {str(e)}",
                                'duration_ms': 0,
                                'pages_total': 0,
                                'pages_with_text': 0,
                                'char_count': 0
                            },
                            int(input_file.stat().st_size)
                        )

                        if self.config.logging.fail_fast:
                            break

                    # Update progress
                    if pbar:
                        pbar.update(1)
                        pbar.set_postfix({
                            'success': successful,
                            'failed': failed
                        })

        finally:
            if pbar:
                pbar.close()

        # Return True if no failures or not in fail_fast mode
        return failed == 0 or not self.config.logging.fail_fast

    def _process_single_file(
        self,
        input_file: Path,
        output_file: Path,
        language: str,
        output_ext: str
    ) -> bool:
        """Process a single PDF file."""
        try:
            # Convert PDF
            success, result_info = self.converter.convert_pdf(input_file, output_ext)

            # Get file size
            file_size = int(input_file.stat().st_size)

            if success:
                # Write output file
                content = result_info['content']
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Log success
                self.logger.log_processing_result(
                    input_file,
                    output_file,
                    language,
                    result_info,
                    file_size
                )

                return True

            else:
                # Log failure or skip
                if result_info['status'] == 'skipped':
                    self.logger.log_skip(
                        input_file,
                        output_file,
                        language,
                        result_info['error_reason'],
                        file_size
                    )
                else:
                    self.logger.log_processing_result(
                        input_file,
                        output_file,
                        language,
                        result_info,
                        file_size
                    )

                return False

        except Exception as e:
            # Log unexpected error
            self.logger.log_error(f"Unexpected error processing {input_file}: {e}")
            return False