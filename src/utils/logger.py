"""
Centralized logging configuration for Orbitspace Compyle
Provides structured logging with different levels and formatters
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "project_id"):
            log_data["project_id"] = record.project_id
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "phase"):
            log_data["phase"] = record.phase
        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = self.COLORS.get(levelname, self.RESET)

        # Format: [TIME] LEVEL - logger - message
        time_str = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        log_message = f"[{time_str}] {color}{levelname:8s}{self.RESET} - {record.name:30s} - {record.getMessage()}"

        # Add extra context if available
        extras = []
        if hasattr(record, "project_id"):
            extras.append(f"project={record.project_id}")
        if hasattr(record, "task_id"):
            extras.append(f"task={record.task_id}")
        if hasattr(record, "phase"):
            extras.append(f"phase={record.phase}")

        if extras:
            log_message += f" [{', '.join(extras)}]"

        # Add exception if present
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        return log_message


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        json_format: Use JSON format for structured logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter())

    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())  # Always use JSON for file logs
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Application loggers
def get_agent_logger(agent_name: str, project_id: str, task_id: str) -> logging.LoggerAdapter:
    """
    Get a logger adapter for agent execution with context

    Args:
        agent_name: Name of the agent
        project_id: Project ID
        task_id: Task ID

    Returns:
        LoggerAdapter with context
    """
    logger = get_logger(f"agent.{agent_name}")
    return logging.LoggerAdapter(logger, {
        "agent_name": agent_name,
        "project_id": project_id,
        "task_id": task_id
    })


def get_api_logger() -> logging.Logger:
    """Get logger for API operations"""
    return get_logger("api")


def get_orchestrator_logger() -> logging.Logger:
    """Get logger for orchestrator operations"""
    return get_logger("orchestrator")


def get_tool_logger(tool_name: str) -> logging.Logger:
    """Get logger for tool operations"""
    return get_logger(f"tool.{tool_name}")


# Initialize root logger on module import
setup_logger(
    "compyle",
    level="INFO",
    json_format=False
)
