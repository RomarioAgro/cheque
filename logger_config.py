import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_LOG_FORMAT = "%(asctime)s - %(filename)s - %(funcName)s: %(lineno)d - %(message)s"
DEFAULT_DATE_FORMAT = "%H:%M:%S"
DEFAULT_LOG_DIR = Path(r"D:\files")
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "log.log"


def build_check_log_file(arg_value: str, current_time: Optional[str] = None) -> Path:
    timestamp = current_time or datetime.now().strftime("%Y-%m-%d %H_%M_%S")
    safe_arg = re.sub(r'[<>:"/\\|?*]+', "_", str(arg_value).strip()) or "unknown"
    return DEFAULT_LOG_DIR / f"check_{safe_arg}_{timestamp}.log"


def get_formatter() -> logging.Formatter:
    return logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)


def configure_logging(
    log_file: Optional[str | Path] = None,
    level: int = logging.DEBUG,
) -> logging.Logger:
    root_logger = logging.getLogger()
    if root_logger.handlers and log_file is None:
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)
        return root_logger

    target_path = Path(log_file) if log_file else DEFAULT_LOG_FILE
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path = target_path.resolve()

    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).resolve() == target_path:
            root_logger.setLevel(level)
            handler.setLevel(level)
            return root_logger

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(target_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(get_formatter())

    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    return root_logger


def get_logger(
    name: Optional[str] = None,
    log_file: Optional[str | Path] = None,
    level: int = logging.DEBUG,
) -> logging.Logger:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level)
        for handler in root_logger.handlers:
            handler.setLevel(level)
    else:
        configure_logging(log_file=log_file, level=level)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = True
    return logger
