
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: Path, name: str = 'suite', level: int = logging.INFO) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        ch = logging.StreamHandler(); ch.setLevel(level)
        fmt = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        ch.setFormatter(fmt)
        fh = RotatingFileHandler(log_dir / f'{name}.log', maxBytes=2_000_000, backupCount=3)
        fh.setLevel(level); fh.setFormatter(fmt)
        logger.addHandler(ch); logger.addHandler(fh)
    return logger
