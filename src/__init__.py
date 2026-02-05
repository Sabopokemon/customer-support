"""
Support Bot Core Package
サポートボットのコアパッケージ
"""

from .agent import get_support_agent, SupportAgent
from .api import create_app, run_server
from .configs import config
from .custom_logger import get_module_logger, app_logger
from .models import (
    QuestionRequest, AnswerResponse, SearchResult,
    ErrorResponse, SystemStatus
)
from .prompts import prompts

__version__ = "1.0.0"

__all__ = [
    'get_support_agent',
    'SupportAgent', 
    'create_app',
    'run_server',
    'config',
    'get_module_logger',
    'app_logger',
    'QuestionRequest',
    'AnswerResponse', 
    'SearchResult',
    'ErrorResponse',
    'SystemStatus',
    'prompts'
]