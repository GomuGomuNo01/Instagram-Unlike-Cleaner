"""Journaux de l'application : console et fichier tournant dans DATA_DIR/logs.

Le module s'appelle `logs` et non `logging` pour ne pas masquer le module standard.
"""

import logging
import re
from logging.handlers import RotatingFileHandler

from app.core.config import Settings

LOGGER_NAME = "app"
LOG_FILE_NAME = "iuc.log"
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s : %(message)s"

# Cookies de session Instagram, mots de passe et jeton de l'API : ils ne doivent jamais
# finir dans un journal.
_SECRET_PATTERN = re.compile(
    r"(?i)\b(sessionid|csrftoken|ds_user_id|password|passwd|mot_de_passe|token|jeton)"
    r"(\s*[=:]\s*)([^\s;,&\"']+)"
)


class RedactSecretsFilter(logging.Filter):
    """Remplace la valeur des secrets connus par *** avant l'écriture du message."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _SECRET_PATTERN.sub(r"\1\2***", message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def close_logging() -> bool:
    """Ferme les sorties du logger (dont le fichier, que Windows refuse sinon de supprimer).
    Renvoie True si des sorties étaient ouvertes."""
    logger = logging.getLogger(LOGGER_NAME)
    handlers = list(logger.handlers)
    for handler in handlers:
        logger.removeHandler(handler)
        handler.close()
    return bool(handlers)


def setup_logging(settings: Settings) -> logging.Logger:
    """Configure le logger de l'application. Peut être rappelée sans dupliquer les sorties."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(settings.log_level)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT)
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        RotatingFileHandler(
            settings.logs_dir / LOG_FILE_NAME,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        ),
    ]
    # Le filtre est posé sur les handlers : un filtre posé sur le logger ignorerait
    # les messages des sous-loggers (app.browser, app.services...).
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RedactSecretsFilter())
        logger.addHandler(handler)
    return logger
