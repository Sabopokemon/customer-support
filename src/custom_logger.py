"""
カスタムログシステム
アプリケーション全体のログを管理
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .configs import config


class CustomFormatter(logging.Formatter):
    """カスタムログフォーマッター"""
    
    # カラーコード
    COLORS = {
        'DEBUG': '\033[36m',    # シアン
        'INFO': '\033[32m',     # 緑
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 赤
        'CRITICAL': '\033[91m', # 明るい赤
        'RESET': '\033[0m'      # リセット
    }
    
    def format(self, record):
        # ログレベルに応じて色を設定
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # タイムスタンプとレベルをフォーマット
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # ログメッセージを構築
        log_message = (
            f"{color}[{record.levelname}]{reset} "
            f"{timestamp} - "
            f"{record.name} - "
            f"{record.getMessage()}"
        )
        
        # 例外情報があれば追加
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"
        
        return log_message


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    カスタムロガーを設定
    
    Args:
        name: ロガー名
        level: ログレベル
        log_file: ログファイルのパス（オプション）
    
    Returns:
        設定済みのロガー
    """
    logger = logging.getLogger(name)
    
    # 既に設定済みの場合はそのまま返す
    if logger.handlers:
        return logger
    
    # ログレベルを設定
    log_level = level or config.LOG_LEVEL
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # コンソールハンドラーを設定
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)
    
    # ファイルハンドラーを設定（オプション）
    if log_file:
        # ログディレクトリを作成
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # 親ロガーへの伝播を無効化
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    ロガーを取得（キャッシュ機能付き）
    
    Args:
        name: ロガー名
    
    Returns:
        ロガーインスタンス
    """
    return setup_logger(name)


# メインのアプリケーションロガー
app_logger = get_logger("support_bot")

# 各モジュール用のロガーファクトリー関数
def get_module_logger(module_name: str) -> logging.Logger:
    """モジュール専用ロガーを取得"""
    return get_logger(f"support_bot.{module_name}")