"""
Centralized logging configuration for Manus AI Clone
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from flask_socketio import SocketIO

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Custom SocketIO Handler for real-time log streaming
class SocketIOHandler(logging.Handler):
    def __init__(self, socketio: SocketIO):
        super().__init__()
        self.socketio = socketio

    def emit(self, record):
        log_message = self.format(record)
        self.socketio.emit('log_update', {
            'level': record.levelname,
            'message': log_message,
            'timestamp': record.asctime,
            'module': record.module,
            'line': record.lineno
        })

# Configure root logger
def configure_logging(socketio: SocketIO = None):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    logger.handlers = []

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)

    # File handler with rotation
    log_file = os.path.join(LOG_DIR, 'manus_ai.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)  # 10MB per file, 5 backups
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # SocketIO handler for real-time UI updates if provided
    if socketio:
        socketio_handler = SocketIOHandler(socketio)
        socketio_handler.setLevel(logging.INFO)  # Limit to INFO and above for UI
        logger.addHandler(socketio_handler)

    # Set format for all handlers
    log_format = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s:%(lineno)d - %(message)s')
    for handler in logger.handlers:
        handler.setFormatter(log_format)

    return logger

# Utility to get a logger with the specified name
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)