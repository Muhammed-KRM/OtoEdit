import logging
import sys
from pathlib import Path


def setup_logging(log_file: str = "logs/worker.log", level: int = logging.INFO):
    """Worker genelinde standart ve yapılandırılmış loglama mekanizmasını kurar."""
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Konsol Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Dosya Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Var olan handler'ları temizle
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Üçüncü parti gürültülü log seviyelerini sınırla
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("mediapipe").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Verilen isimle yapılandırılmış logger döner."""
    return logging.getLogger(name)
