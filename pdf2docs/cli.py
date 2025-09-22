"""CLI interface for PDF2Docs using Click."""

import click
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from .processor import PDFProcessor
from .utils import validate_language_code


@click.command()
@click.option(
    '--input', 'input_path',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Input PDF file or directory (data/raw/es or data/raw/en)'
)
@click.option(
    '--out-ext',
    type=click.Choice(['txt', 'md']),
    required=True,
    help='Output file extension (txt or md)'
)
@click.option(
    '--lang',
    type=click.Choice(['es', 'en']),
    help='Language override (es or en)'
)
@click.option(
    '--pattern',
    help='Glob pattern to filter files'
)
@click.option(
    '--workers',
    type=click.IntRange(1, 16),
    help='Number of parallel workers (1-16)'
)
@click.option(
    '--backend',
    help='Docling backend identifier'
)
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    help='Path to configuration YAML file'
)
@click.option(
    '--log-file',
    type=click.Path(path_type=Path),
    help='Path to log file'
)
@click.option(
    '--quiet',
    is_flag=True,
    help='Disable progress display'
)
@click.option(
    '--no-progress',
    is_flag=True,
    help='Disable progress display (alias for --quiet)'
)
@click.option(
    '--fail-fast',
    is_flag=True,
    help='Stop processing on first error'
)
@click.version_option()
def main(
    input_path: Path,
    out_ext: str,
    lang: Optional[str] = None,
    pattern: Optional[str] = None,
    workers: Optional[int] = None,
    backend: Optional[str] = None,
    config: Optional[Path] = None,
    log_file: Optional[Path] = None,
    quiet: bool = False,
    no_progress: bool = False,
    fail_fast: bool = False
):
    """Convert PDF files to text or markdown using Docling.

    Converts PDFs from data/raw/{es,en} to data/result/{es,en} with
    automatic language detection and skip logic for existing files.
    """
    try:
        # Combine quiet flags
        is_quiet = quiet or no_progress

        # Load configuration
        config_manager = ConfigManager(config) if config else ConfigManager.from_default_locations()

        # Build args dict for config override
        args = {
            'workers': workers,
            'quiet': is_quiet,
            'fail_fast': fail_fast,
            'log_file': str(log_file) if log_file else None,
            'backend': backend
        }

        # Override config with CLI args
        app_config = config_manager.override_with_args(args)

        # Validate language if provided
        if lang and not validate_language_code(lang):
            raise click.BadParameter(f"Invalid language code: {lang}. Must be 'es' or 'en'.")

        # Create processor and run
        processor = PDFProcessor(app_config)
        success = processor.process(
            input_path=input_path,
            output_ext=out_ext,
            language_override=lang,
            pattern=pattern
        )

        # Exit with appropriate code
        if not success:
            click.echo("Processing completed with errors. Check logs for details.", err=True)
            raise click.Abort()
        else:
            click.echo("Processing completed successfully.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()