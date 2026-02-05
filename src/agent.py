"""
エージェント司令塔（RAGロジック）
質問応答処理の中核となるエージェント
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI

from .configs import config
from .custom_logger import get_module_logger
from .models import (
    QuestionRequest, AnswerResponse, SearchResult, 
    ErrorResponse
)
from .prompts import prompts
from tool import get_unified_search_engine

logger = get_module_logger("agent")


class SupportAgent:
    """サポートボットエージェント"""
    
    def __init__(self):
        self.openai_client = None
        self.search_engine = None
        self._initialize()
    
    def _initialize(self):
        """エージェントを初期化"""
        try:
            logger.info("サポートエージェントを初期化中...")
            
            # OpenAIクライアントを初期化
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            
            # 統合検索エンジンを取得
            self.search_engine = get_unified_search_engine()
            
            # 健全性チェック
            self._health_check()
            
            logger.info("サポートエージェントの初期化が完了しました")
            
        except Exception as e:
            logger.error(f"サポートエージェントの初期化に失敗しました: {e}")
            raise
    
    def _health_check(self):
        """システムの健全性をチェック"""
        try:
            # OpenAI接続テスト
            self.openai_client.models.list()
            logger.info("OpenAI接続: OK")
            
            # 検索エンジンの健全性チェック
            search_health = self.search_engine.health_check()
            if search_health['overall']:
                logger.info("検索エンジン: OK")
            else:
                logger.warning("検索エンジンの一部が利用できません")
            
        except Exception as e:
            logger.error(f"健全性チェックに失敗しました: {e}")
            raise
    
    async def process_question(
        self, 
        question_request: QuestionRequest
    ) -> AnswerResponse:
        """
        質問を処理して回答を生成
        
        Args:
            question_request: 質問リクエスト
        
        Returns:
            回答レスポンス
        """
        start_time = time.time()
        
        try:
            question = question_request.question
            context = question_request.context or {}
            
            logger.info(f"質問を処理中: '{question}'")
            
            # 1. 検索実行
            search_results, search_strategy = await self._search_knowledge_base(
                question, context
            )
            
            # 2. 回答生成
            if search_results:
                answer, confidence = await self._generate_answer_with_sources(
                    question, search_results, search_strategy
                )
            else:
                answer, confidence = await self._generate_no_results_answer(question)
                search_results = []
            
            # 3. レスポンス作成
            processing_time = time.time() - start_time
            
            response = AnswerResponse(
                answer=answer,
                confidence=confidence,
                sources=search_results,
                processing_time=processing_time
            )
            
            logger.info(f"質問処理完了: {processing_time:.2f}秒, 信頼度: {confidence:.2f}")
            return response
            
        except Exception as e:
            logger.error(f"質問処理に失敗しました: {e}")
            processing_time = time.time() - start_time
            
            # エラーレスポンスを作成
            return AnswerResponse(
                answer="申し訳ございませんが、システムエラーが発生しました。しばらく待ってから再度お試しください。",
                confidence=0.0,
                sources=[],
                processing_time=processing_time
            )
    
    async def _search_knowledge_base(
        self, 
        question: str, 
        context: Dict[str, Any]
    ) -> tuple[List[SearchResult], str]:
        """ナレッジベースを検索"""
        try:
            # スマート検索を実行
            search_results, strategy = self.search_engine.smart_search(
                query=question,
                context=context
            )
            
            logger.info(f"検索完了: {len(search_results)}件 (戦略: {strategy})")
            
            # 結果をログに記録
            for i, result in enumerate(search_results[:3], 1):
                logger.debug(f"検索結果{i}: {result.source} (スコア: {result.score:.3f})")
            
            return search_results, strategy
            
        except Exception as e:
            logger.error(f"ナレッジベース検索に失敗しました: {e}")
            return [], "error"
    
    async def _generate_answer_with_sources(
        self, 
        question: str, 
        search_results: List[SearchResult],
        search_strategy: str
    ) -> tuple[str, float]:
        """検索結果を基に回答を生成"""
        try:
            # 検索結果をソース別に分類
            faq_results = [r for r in search_results if r.metadata.get('type') == 'faq']
            manual_results = [r for r in search_results if r.metadata.get('type') == 'manual']
            
            # プロンプトを選択
            if faq_results and manual_results:
                # 複数ソース統合プロンプト
                prompt = prompts.generate_multi_source_prompt(
                    question=question,
                    faq_results=faq_results,
                    manual_results=manual_results
                )
            elif faq_results:
                # FAQ専用プロンプト
                prompt = prompts.generate_faq_prompt(question, faq_results)
            elif manual_results:
                # マニュアル専用プロンプト
                prompt = prompts.generate_manual_prompt(question, manual_results)
            else:
                # 結果なしプロンプト
                prompt = prompts.generate_no_results_prompt(question)
            
            # OpenAIで回答生成
            response = self.openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": prompts.SYSTEM_ROLE},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            answer = response.choices[0].message.content.strip()
            
            # 信頼度を計算
            confidence = self._calculate_confidence(search_results, search_strategy)
            
            logger.info(f"回答生成完了: {len(answer)}文字, 信頼度: {confidence:.2f}")
            return answer, confidence
            
        except Exception as e:
            logger.error(f"回答生成に失敗しました: {e}")
            return "回答の生成中にエラーが発生しました。", 0.0
    
    async def _generate_no_results_answer(self, question: str) -> tuple[str, float]:
        """検索結果がない場合の回答を生成"""
        try:
            prompt = prompts.generate_no_results_prompt(question)
            
            response = self.openai_client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": prompts.SYSTEM_ROLE},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            answer = response.choices[0].message.content.strip()
            
            logger.info("検索結果なし回答を生成しました")
            return answer, 0.1  # 低い信頼度
            
        except Exception as e:
            logger.error(f"検索結果なし回答の生成に失敗しました: {e}")
            return prompts.generate_no_results_prompt(question), 0.0
    
    def _calculate_confidence(
        self, 
        search_results: List[SearchResult],
        search_strategy: str
    ) -> float:
        """回答の信頼度を計算"""
        if not search_results:
            return 0.0
        
        # 基本スコア（最高スコアの結果を重視）
        max_score = max(result.score for result in search_results)
        avg_score = sum(result.score for result in search_results) / len(search_results)
        
        # 結果数による調整
        result_count_factor = min(len(search_results) / 3.0, 1.0)
        
        # 検索戦略による調整
        strategy_factor = {
            "faq_focus": 0.9,
            "manual_focus": 0.8,
            "balanced": 0.85,
            "error": 0.3
        }.get(search_strategy, 0.7)
        
        # 信頼度を計算
        confidence = (max_score * 0.6 + avg_score * 0.4) * result_count_factor * strategy_factor
        
        # 0.0-1.0の範囲に正規化
        return max(0.0, min(1.0, confidence))
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム状態を取得"""
        try:
            status = {
                "agent_status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "openai_connection": False,
                "search_engine_status": {},
                "version": "1.0.0"
            }
            
            # OpenAI接続チェック
            try:
                self.openai_client.models.list()
                status["openai_connection"] = True
            except:
                status["openai_connection"] = False
                status["agent_status"] = "degraded"
            
            # 検索エンジン状態チェック
            try:
                status["search_engine_status"] = self.search_engine.health_check()
                if not status["search_engine_status"]["overall"]:
                    status["agent_status"] = "degraded"
            except:
                status["search_engine_status"] = {"overall": False}
                status["agent_status"] = "degraded"
            
            return status
            
        except Exception as e:
            logger.error(f"システム状態取得に失敗しました: {e}")
            return {
                "agent_status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    async def process_batch_questions(
        self, 
        questions: List[str]
    ) -> List[AnswerResponse]:
        """複数の質問をバッチ処理"""
        try:
            logger.info(f"バッチ処理を開始: {len(questions)}件の質問")
            
            responses = []
            for i, question in enumerate(questions, 1):
                logger.info(f"バッチ処理中 ({i}/{len(questions)}): {question}")
                
                request = QuestionRequest(question=question)
                response = await self.process_question(request)
                responses.append(response)
            
            logger.info(f"バッチ処理完了: {len(responses)}件の回答を生成")
            return responses
            
        except Exception as e:
            logger.error(f"バッチ処理に失敗しました: {e}")
            return []


# グローバルインスタンス
_support_agent = None

def get_support_agent() -> SupportAgent:
    """サポートエージェントのグローバルインスタンスを取得"""
    global _support_agent
    if _support_agent is None:
        _support_agent = SupportAgent()
    return _support_agent


async def main():
    """テスト用のメイン関数"""
    import asyncio
    
    try:
        # エージェントを初期化
        agent = get_support_agent()
        
        # システム状態を表示
        status = agent.get_system_status()
        print(f"システム状態: {status['agent_status']}")
        
        # テスト質問
        test_questions = [
            "勤怠管理システムにログインできません",
            "有給申請はどこから行いますか？",
            "会議室の予約方法を教えてください"
        ]
        
        print("\n🤖 サポートエージェントのテスト:")
        print("=" * 50)
        
        for question in test_questions:
            print(f"\n質問: {question}")
            print("-" * 30)
            
            request = QuestionRequest(question=question)
            response = await agent.process_question(request)
            
            print(f"信頼度: {response.confidence:.2f}")
            print(f"処理時間: {response.processing_time:.2f}秒")
            print(f"参照数: {len(response.sources)}件")
            print(f"回答:\n{response.answer}")
        
        return 0
        
    except Exception as e:
        logger.error(f"テスト実行に失敗しました: {e}")
        return 1


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())