"""Configuration management for PDF2Docs CLI."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LimitsConfig:
    max_file_size_mb: int = 10
    max_pages: int = 500
    timeout_per_file_sec: int = 120
    timeout_strategy: str = "per_file"


@dataclass
class SerializationConfig:
    markdown: Dict[str, Any] = field(default_factory=lambda: {"add_yaml_header": False})
    text: Dict[str, Any] = field(default_factory=lambda: {"table_delimiter": "\t"})


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: Optional[str] = None
    progress: bool = True
    fail_fast: bool = False
    workers: int = 4


@dataclass
class DoclingConfig:
    backend: str = "auto"


@dataclass
class Config:
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    serialization: SerializationConfig = field(default_factory=SerializationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    docling: DoclingConfig = field(default_factory=DoclingConfig)


class ConfigManager:
    """Manages configuration loading and validation."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        self._config = None

    def load_config(self) -> Config:
        """Load configuration from YAML file or use defaults."""
        if self._config is not None:
            return self._config

        config_data = {}

        # Load from file if provided
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                raise ValueError(f"Error loading config from {self.config_path}: {e}")

        # Build config with defaults
        self._config = Config(
            limits=LimitsConfig(**config_data.get('limits', {})),
            serialization=SerializationConfig(**config_data.get('serialization', {})),
            logging=LoggingConfig(**config_data.get('logging', {})),
            docling=DoclingConfig(**config_data.get('docling', {}))
        )

        return self._config

    def override_with_args(self, args: Dict[str, Any]) -> Config:
        """Override config with CLI arguments."""
        config = self.load_config()

        # Override logging config
        if args.get('workers') is not None:
            config.logging.workers = args['workers']
        if args.get('quiet') is not None:
            config.logging.progress = not args['quiet']
        if args.get('fail_fast') is not None:
            config.logging.fail_fast = args['fail_fast']
        if args.get('log_file') is not None:
            config.logging.log_file = args['log_file']

        # Override docling config
        if args.get('backend') is not None:
            config.docling.backend = args['backend']

        return config

    @classmethod
    def from_default_locations(cls) -> 'ConfigManager':
        """Create config manager checking default locations."""
        default_paths = [
            Path("config.yaml"),
            Path("pdf2docs.yaml"),
            Path.home() / ".pdf2docs.yaml"
        ]

        for path in default_paths:
            if path.exists():
                return cls(path)

        return cls()