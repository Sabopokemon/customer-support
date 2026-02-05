"""
データスキーマ（Pydantic）
APIの入出力とデータ構造を定義
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """質問リクエストのスキーマ"""
    question: str = Field(..., description="ユーザーからの質問", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="追加のコンテキスト情報")


class SearchResult(BaseModel):
    """検索結果のスキーマ"""
    content: str = Field(..., description="検索された内容")
    source: str = Field(..., description="ソース（FAQ、マニュアルなど）")
    score: float = Field(..., description="類似度スコア", ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加のメタデータ")


class AnswerResponse(BaseModel):
    """回答レスポンスのスキーマ"""
    answer: str = Field(..., description="生成された回答")
    confidence: float = Field(..., description="回答の信頼度", ge=0.0, le=1.0)
    sources: List[SearchResult] = Field(default_factory=list, description="参照した情報源")
    timestamp: datetime = Field(default_factory=datetime.now, description="回答生成時刻")
    processing_time: Optional[float] = Field(None, description="処理時間（秒）")


class ErrorResponse(BaseModel):
    """エラーレスポンスのスキーマ"""
    error: str = Field(..., description="エラーメッセージ")
    error_code: Optional[str] = Field(None, description="エラーコード")
    timestamp: datetime = Field(default_factory=datetime.now, description="エラー発生時刻")


class FAQItem(BaseModel):
    """FAQ項目のスキーマ"""
    question: str = Field(..., description="質問")
    answer: str = Field(..., description="回答")
    category: Optional[str] = Field(None, description="カテゴリ")
    tags: List[str] = Field(default_factory=list, description="タグ")


class ManualSection(BaseModel):
    """マニュアル項目のスキーマ"""
    title: str = Field(..., description="セクションタイトル")
    content: str = Field(..., description="セクション内容")
    page_number: Optional[int] = Field(None, description="ページ番号")
    section_number: Optional[str] = Field(None, description="セクション番号")


class IndexStatus(BaseModel):
    """インデックス状態のスキーマ"""
    collection_name: str = Field(..., description="コレクション名")
    total_documents: int = Field(..., description="総ドキュメント数")
    last_updated: datetime = Field(..., description="最終更新時刻")
    status: str = Field(..., description="ステータス（active, building, error）")


class SystemStatus(BaseModel):
    """システム状態のスキーマ"""
    status: str = Field(..., description="システム状態（healthy, degraded, down）")
    version: str = Field(..., description="アプリケーションバージョン")
    uptime: float = Field(..., description="稼働時間（秒）")
    database_status: str = Field(..., description="データベース状態")
    last_check: datetime = Field(default_factory=datetime.now, description="最終チェック時刻")


class ConfigUpdate(BaseModel):
    """設定更新のスキーマ"""
    max_search_results: Optional[int] = Field(None, description="最大検索結果数", ge=1, le=20)
    similarity_threshold: Optional[float] = Field(None, description="類似度閾値", ge=0.0, le=1.0)
    openai_model: Optional[str] = Field(None, description="OpenAIモデル名")


class LogEntry(BaseModel):
    """ログエントリのスキーマ"""
    timestamp: datetime = Field(default_factory=datetime.now, description="ログ時刻")
    level: str = Field(..., description="ログレベル")
    message: str = Field(..., description="ログメッセージ")
    module: str = Field(..., description="モジュール名")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="追加データ")