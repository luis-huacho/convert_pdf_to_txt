"""Structured logging system for PDF2Docs."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from .config import LoggingConfig


@dataclass
class ProcessingMetrics:
    timestamp: str
    level: str
    input_file: str
    output_file: str
    language: str
    duration_ms: int
    file_size_bytes: int
    status: str  # ok|skipped|failed
    error_reason: Optional[str] = None
    pages_total: int = 0
    pages_with_text: int = 0
    char_count: int = 0


@dataclass
class ProcessingSummary:
    total_processed: int
    converted: int
    skipped: int
    failed: int
    total_time_sec: float
    start_time: str
    end_time: str
    skipped_reasons: Dict[str, int]
    error_reasons: Dict[str, int]


class StructuredLogger:
    """Handles structured logging to file and console progress."""

    def __init__(self, config: LoggingConfig):
        self.config = config
        self.metrics: List[ProcessingMetrics] = []
        self.start_time = datetime.now()

        # Set up file logger
        self._setup_file_logger()

    def _setup_file_logger(self):
        """Set up file logging with JSON format."""
        # Create log file path
        if self.config.log_file:
            log_path = Path(self.config.log_file)
        else:
            # Default log file with timestamp
            timestamp = self.start_time.strftime("%Y%m%d-%H%M%S")
            log_path = Path("logs") / f"run-{timestamp}.log"

        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger('pdf2docs')
        self.logger.setLevel(getattr(logging, self.config.level))

        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # File handler with JSON formatter
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)

        # Console handler for errors
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        self.logger.addHandler(console_handler)

        self.log_file_path = log_path

    def log_processing_result(
        self,
        input_file: Path,
        output_file: Path,
        language: str,
        result_info: Dict[str, Any],
        file_size: int
    ):
        """Log processing result with structured data."""
        timestamp = datetime.now().isoformat()

        metrics = ProcessingMetrics(
            timestamp=timestamp,
            level="INFO",
            input_file=str(input_file),
            output_file=str(output_file),
            language=language,
            duration_ms=result_info.get('duration_ms', 0),
            file_size_bytes=file_size,
            status=result_info.get('status', 'failed'),
            error_reason=result_info.get('error_reason'),
            pages_total=result_info.get('pages_total', 0),
            pages_with_text=result_info.get('pages_with_text', 0),
            char_count=result_info.get('char_count', 0)
        )

        # Store metrics
        self.metrics.append(metrics)

        # Log to file
        self.logger.info("Processing result", extra={"metrics": asdict(metrics)})

    def log_skip(
        self,
        input_file: Path,
        output_file: Path,
        language: str,
        reason: str,
        file_size: int
    ):
        """Log file skip with reason."""
        timestamp = datetime.now().isoformat()

        metrics = ProcessingMetrics(
            timestamp=timestamp,
            level="INFO",
            input_file=str(input_file),
            output_file=str(output_file),
            language=language,
            duration_ms=0,
            file_size_bytes=file_size,
            status="skipped",
            error_reason=reason
        )

        # Store metrics
        self.metrics.append(metrics)

        # Log to file
        self.logger.info("File skipped", extra={"metrics": asdict(metrics)})

    def log_error(self, message: str, input_file: Optional[Path] = None, error: Optional[Exception] = None):
        """Log error message."""
        extra = {}
        if input_file:
            extra['input_file'] = str(input_file)
        if error:
            extra['error'] = str(error)

        self.logger.error(message, extra=extra)

    def log_info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def get_summary(self) -> ProcessingSummary:
        """Generate processing summary."""
        end_time = datetime.now()
        total_time = (end_time - self.start_time).total_seconds()

        # Count statuses
        converted = sum(1 for m in self.metrics if m.status == 'ok')
        skipped = sum(1 for m in self.metrics if m.status == 'skipped')
        failed = sum(1 for m in self.metrics if m.status == 'failed')

        # Count skip reasons
        skipped_reasons = {}
        for m in self.metrics:
            if m.status == 'skipped' and m.error_reason:
                skipped_reasons[m.error_reason] = skipped_reasons.get(m.error_reason, 0) + 1

        # Count error reasons
        error_reasons = {}
        for m in self.metrics:
            if m.status == 'failed' and m.error_reason:
                error_reasons[m.error_reason] = error_reasons.get(m.error_reason, 0) + 1

        return ProcessingSummary(
            total_processed=len(self.metrics),
            converted=converted,
            skipped=skipped,
            failed=failed,
            total_time_sec=total_time,
            start_time=self.start_time.isoformat(),
            end_time=end_time.isoformat(),
            skipped_reasons=skipped_reasons,
            error_reasons=error_reasons
        )

    def print_summary(self):
        """Print processing summary to console."""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Total files processed: {summary.total_processed}")
        print(f"Successfully converted: {summary.converted}")
        print(f"Skipped: {summary.skipped}")
        print(f"Failed: {summary.failed}")
        print(f"Total time: {summary.total_time_sec:.2f} seconds")

        if summary.skipped_reasons:
            print(f"\nSkip reasons:")
            for reason, count in summary.skipped_reasons.items():
                print(f"  {reason}: {count}")

        if summary.error_reasons:
            print(f"\nError reasons:")
            for reason, count in summary.error_reasons.items():
                print(f"  {reason}: {count}")

        print(f"\nLog file: {self.log_file_path}")
        print("="*60)

        # Log summary to file
        self.logger.info("Processing summary", extra={"summary": asdict(summary)})


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
        }

        # Add extra fields
        if hasattr(record, 'metrics'):
            log_entry.update(record.metrics)
        elif hasattr(record, 'summary'):
            log_entry['summary'] = record.summary
        else:
            # Add any other extra fields
            for key, value in record.__dict__.items():
                if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                             'filename', 'module', 'lineno', 'funcName', 'created',
                             'msecs', 'relativeCreated', 'thread', 'threadName',
                             'processName', 'process', 'message'):
                    log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)