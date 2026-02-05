"""
設定読み込み（.env など）
環境変数とシステム設定を管理
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# プロジェクトルートディレクトリを特定
PROJECT_ROOT = Path(__file__).parent.parent

# .envファイルを読み込み
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """システム設定クラス"""
    
    # OpenAI API設定
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # ベクトルDB設定（Chroma）
    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "support_bot")
    
    # アプリケーション設定
    APP_HOST: str = os.getenv("APP_HOST", "localhost")
    APP_PORT: int = int(os.getenv("APP_PORT", "8080"))
    
    # ログレベル
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # データディレクトリ
    DATA_DIR: Path = PROJECT_ROOT / "data"
    FAQ_FILE: Path = DATA_DIR / "faq.csv"
    MANUAL_DIR: Path = DATA_DIR / "manuals"
    
    # 埋め込みモデル設定
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # RAG設定
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    
    @classmethod
    def validate(cls) -> bool:
        """設定の妥当性をチェック"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        
        if not cls.FAQ_FILE.exists():
            raise FileNotFoundError(f"FAQ file not found: {cls.FAQ_FILE}")
        
        return True


# グローバル設定インスタンス
config = Config()