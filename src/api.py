"""
FastAPIベースのREST API (/ask等)
RESTful APIエンドポイントの実装
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import traceback

from .configs import config
from .custom_logger import get_module_logger
from .models import (
    QuestionRequest, AnswerResponse, ErrorResponse, 
    SystemStatus, ConfigUpdate
)
from .agent import get_support_agent

logger = get_module_logger("api")

# FastAPIアプリケーションを作成
app = FastAPI(
    title="Support Bot API",
    description="サポートボット用のREST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル変数
support_agent = None
startup_time = datetime.now()


@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    global support_agent
    try:
        logger.info("Support Bot API を起動中...")
        
        # サポートエージェントを初期化
        support_agent = get_support_agent()
        
        logger.info("Support Bot API の起動が完了しました")
        
    except Exception as e:
        logger.error(f"アプリケーション起動に失敗しました: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("Support Bot API を終了中...")


def get_agent():
    """依存性注入: サポートエージェントを取得"""
    if support_agent is None:
        raise HTTPException(
            status_code=503, 
            detail="サポートエージェントが初期化されていません"
        )
    return support_agent


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Support Bot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    agent = Depends(get_agent)
):
    """
    質問回答エンドポイント
    
    メインのAPIエンドポイント：質問を受けて回答を返す
    """
    try:
        logger.info(f"質問受付: '{request.question}'")
        
        # バリデーション
        if not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="質問が空です"
            )
        
        if len(request.question) > 1000:
            raise HTTPException(
                status_code=400,
                detail="質問が長すぎます（1000文字以内）"
            )
        
        # エージェントで質問を処理
        response = await agent.process_question(request)
        
        logger.info(f"回答完了（信頼度: {response.confidence:.2f}）")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"質問処理中にエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        
        # エラー時の回答
        error_response = AnswerResponse(
            answer="申し訳ございませんが、システムエラーが発生しました。しばらく待ってから再度お試しください。",
            confidence=0.0,
            sources=[],
            processing_time=0.0
        )
        return error_response


@app.post("/batch-ask", response_model=List[AnswerResponse])
async def batch_ask_questions(
    questions: List[str],
    background_tasks: BackgroundTasks,
    agent = Depends(get_agent)
):
    """
    複数質問回答エンドポイント
    
    複数の質問をまとめて処理
    """
    try:
        logger.info(f"複数質問受付: {len(questions)}件")
        
        # バリデーション
        if not questions:
            raise HTTPException(
                status_code=400,
                detail="質問が空です"
            )
        
        if len(questions) > 10:
            raise HTTPException(
                status_code=400,
                detail="一度に処理できる質問は最大10件です"
            )
        
        # バッチ処理実行
        responses = await agent.process_batch_questions(questions)
        
        logger.info(f"複数回答完了: {len(responses)}件")
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"複数質問処理中にエラーが発生しました: {e}")
        raise HTTPException(
            status_code=500,
            detail="複数質問処理中にエラーが発生しました"
        )


@app.get("/health", response_model=SystemStatus)
async def health_check(agent = Depends(get_agent)):
    """
    ヘルスチェックエンドポイント
    
    システムの健全性を確認
    """
    try:
        # エージェントからシステム状態を取得
        agent_status = agent.get_system_status()
        
        # 稼働時間を計算
        uptime = (datetime.now() - startup_time).total_seconds()
        
        # システム状態を作成
        status = SystemStatus(
            status=agent_status.get("agent_status", "unknown"),
            version="1.0.0",
            uptime=uptime,
            database_status="healthy" if agent_status.get("search_engine_status", {}).get("overall", False) else "degraded",
            last_check=datetime.now()
        )
        
        logger.debug(f"ヘルスチェック: {status.status}")
        return status
        
    except Exception as e:
        logger.error(f"ヘルスチェック中にエラーが発生しました: {e}")
        return SystemStatus(
            status="error",
            version="1.0.0",
            uptime=0.0,
            database_status="error",
            last_check=datetime.now()
        )


@app.get("/stats")
async def get_statistics(agent = Depends(get_agent)):
    """
    統計情報エンドポイント
    
    システムの統計情報を返す
    """
    try:
        # 基本統計情報を作成
        stats = {
            "uptime_seconds": (datetime.now() - startup_time).total_seconds(),
            "startup_time": startup_time.isoformat(),
            "current_time": datetime.now().isoformat(),
            "api_version": "1.0.0"
        }
        
        # エージェント統計を取得
        agent_status = agent.get_system_status()
        stats.update(agent_status)
        
        return stats
        
    except Exception as e:
        logger.error(f"統計情報取得中にエラーが発生しました: {e}")
        raise HTTPException(
            status_code=500,
            detail="統計情報の取得処理中にエラーが発生しました"
        )


@app.post("/config")
async def update_config(
    config_update: ConfigUpdate,
    agent = Depends(get_agent)
):
    """
    設定更新エンドポイント
    
    システム設定の変更を行う
    """
    try:
        logger.info(f"設定更新リクエスト: {config_update}")
        
        updated_settings = {}
        
        # 設定を更新
        if config_update.max_search_results is not None:
            config.MAX_SEARCH_RESULTS = config_update.max_search_results
            updated_settings['max_search_results'] = config_update.max_search_results
        
        if config_update.similarity_threshold is not None:
            config.SIMILARITY_THRESHOLD = config_update.similarity_threshold
            updated_settings['similarity_threshold'] = config_update.similarity_threshold
        
        if config_update.openai_model is not None:
            config.OPENAI_MODEL = config_update.openai_model
            updated_settings['openai_model'] = config_update.openai_model
        
        logger.info(f"設定更新完了: {updated_settings}")
        
        return {
            "message": "設定が更新されました",
            "updated_settings": updated_settings,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"設定更新中にエラーが発生しました: {e}")
        raise HTTPException(
            status_code=500,
            detail="設定更新処理中にエラーが発生しました"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """グローバル例外ハンドラー"""
    logger.error(f"予期しないエラーが発生しました: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部サーバーエラーが発生しました",
            "timestamp": datetime.now().isoformat()
        }
    )


def create_app() -> FastAPI:
    """アプリケーションファクトリー"""
    return app


def run_server():
    """開発サーバーを起動"""
    try:
        logger.info(f"APIサーバーを起動中: {config.APP_HOST}:{config.APP_PORT}")
        
        uvicorn.run(
            "src.api:app",
            host=config.APP_HOST,
            port=config.APP_PORT,
            reload=True,
            log_level=config.LOG_LEVEL.lower()
        )
        
    except Exception as e:
        logger.error(f"APIサーバーの起動に失敗しました: {e}")
        raise


if __name__ == "__main__":
    run_server()