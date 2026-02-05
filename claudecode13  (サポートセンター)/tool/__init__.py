"""
検索ツール集
FAQ検索とマニュアル検索の統合エンジン
"""

from .search_xyz_qa import get_faq_search_engine, FAQSearchEngine
from .search_xyz_manual import get_manual_search_engine, ManualSearchEngine

__all__ = [
    'get_faq_search_engine',
    'get_manual_search_engine', 
    'FAQSearchEngine',
    'ManualSearchEngine',
    'UnifiedSearchEngine'
]

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import asyncio

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.custom_logger import get_module_logger
from src.models import SearchResult

logger = get_module_logger("unified_search")


class UnifiedSearchEngine:
    """統合検索エンジン（FAQ + マニュアル）"""
    
    def __init__(self):
        self.faq_engine = None
        self.manual_engine = None
        self._initialize()
    
    def _initialize(self):
        """統合検索エンジンを初期化"""
        try:
            logger.info("統合検索エンジンを初期化中...")
            
            # FAQ検索エンジンを初期化
            self.faq_engine = get_faq_search_engine()
            
            # マニュアル検索エンジンを初期化
            self.manual_engine = get_manual_search_engine()
            
            logger.info("統合検索エンジンの初期化が完了しました")
            
        except Exception as e:
            logger.error(f"統合検索エンジンの初期化に失敗しました: {e}")
            raise
    
    def search_all(
        self, 
        query: str,
        max_results_per_source: int = 3,
        min_score: float = None
    ) -> Dict[str, List[SearchResult]]:
        """
        FAQ とマニュアルの両方を検索
        
        Args:
            query: 検索クエリ
            max_results_per_source: ソース別の最大結果数
            min_score: 最低類似度スコア
        
        Returns:
            ソース別の検索結果
        """
        try:
            logger.info(f"統合検索実行: '{query}'")
            
            results = {
                'faq': [],
                'manual': []
            }
            
            # FAQ検索を実行
            try:
                faq_results = self.faq_engine.search_faq(
                    query=query,
                    max_results=max_results_per_source,
                    min_score=min_score
                )
                results['faq'] = faq_results
                logger.info(f"FAQ検索完了: {len(faq_results)}件")
            except Exception as e:
                logger.error(f"FAQ検索に失敗しました: {e}")
            
            # マニュアル検索を実行
            try:
                manual_results = self.manual_engine.search_manual(
                    query=query,
                    max_results=max_results_per_source,
                    min_score=min_score
                )
                results['manual'] = manual_results
                logger.info(f"マニュアル検索完了: {len(manual_results)}件")
            except Exception as e:
                logger.error(f"マニュアル検索に失敗しました: {e}")
            
            total_results = len(results['faq']) + len(results['manual'])
            logger.info(f"統合検索完了: {total_results}件の結果を取得")
            
            return results
            
        except Exception as e:
            logger.error(f"統合検索に失敗しました: {e}")
            return {'faq': [], 'manual': []}
    
    def search_ranked(
        self, 
        query: str,
        max_total_results: int = 5,
        min_score: float = None
    ) -> List[SearchResult]:
        """
        FAQ とマニュアルを統合してスコア順にソート
        
        Args:
            query: 検索クエリ
            max_total_results: 合計最大結果数
            min_score: 最低類似度スコア
        
        Returns:
            スコア順の統合検索結果
        """
        try:
            # 両方のソースから結果を取得
            search_results = self.search_all(
                query=query,
                max_results_per_source=max_total_results,
                min_score=min_score
            )
            
            # すべての結果を統合
            all_results = []
            all_results.extend(search_results['faq'])
            all_results.extend(search_results['manual'])
            
            # スコア順にソート
            all_results.sort(key=lambda x: x.score, reverse=True)
            
            # 指定した数まで切り取り
            ranked_results = all_results[:max_total_results]
            
            logger.info(f"ランキング検索完了: {len(ranked_results)}件の結果")
            return ranked_results
            
        except Exception as e:
            logger.error(f"ランキング検索に失敗しました: {e}")
            return []
    
    def smart_search(
        self, 
        query: str,
        context: Dict[str, Any] = None
    ) -> Tuple[List[SearchResult], str]:
        """
        スマート検索エンジンの実装（戦略的検索）
        
        Args:
            query: 検索クエリ
            context: 追加のコンテキスト情報
        
        Returns:
            (検索結果, 検索戦略)
        """
        try:
            context = context or {}
            
            # クエリの分析で検索戦略を決定
            search_strategy = self._determine_search_strategy(query, context)
            
            logger.info(f"スマート検索実行: '{query}' (戦略: {search_strategy})")
            
            if search_strategy == "faq_focus":
                # FAQ重視の検索
                results = self.search_all(query, max_results_per_source=4)
                # FAQの結果を優先
                final_results = results['faq'][:3] + results['manual'][:2]
                
            elif search_strategy == "manual_focus":
                # マニュアル重視の検索
                results = self.search_all(query, max_results_per_source=4)
                # マニュアルの結果を優先
                final_results = results['manual'][:3] + results['faq'][:2]
                
            else:  # "balanced"
                # バランス型の検索
                final_results = self.search_ranked(query, max_total_results=5)
            
            logger.info(f"スマート検索完了: {len(final_results)}件 (戦略: {search_strategy})")
            return final_results, search_strategy
            
        except Exception as e:
            logger.error(f"スマート検索に失敗しました: {e}")
            return [], "error"
    
    def _determine_search_strategy(
        self, 
        query: str, 
        context: Dict[str, Any]
    ) -> str:
        """検索戦略を決定"""
        query_lower = query.lower()
        
        # FAQ向けキーワード
        faq_keywords = [
            'ログイン', '申請', 'パスワード', 'できない', 'エラー', 
            'アカウント', 'ユーザー', 'サインイン', 'トラブル', '問題'
        ]
        
        # マニュアル向けキーワード
        manual_keywords = [
            '手順', '方法', '設定', '操作', '画面', 'ボタン', 
            'メニュー', '機能', '使い方', 'システム'
        ]
        
        # FAQキーワードのマッチ数
        faq_score = sum(1 for keyword in faq_keywords if keyword in query_lower)
        
        # マニュアルキーワードのマッチ数
        manual_score = sum(1 for keyword in manual_keywords if keyword in query_lower)
        
        # 戦略を決定
        if faq_score > manual_score:
            return "faq_focus"
        elif manual_score > faq_score:
            return "manual_focus"
        else:
            return "balanced"
    
    def health_check(self) -> Dict[str, bool]:
        """統合検索エンジンのヘルスチェック"""
        health_status = {
            'faq_engine': False,
            'manual_engine': False,
            'overall': False
        }
        
        try:
            # FAQ検索エンジンのヘルスチェック
            if self.faq_engine:
                health_status['faq_engine'] = self.faq_engine.health_check()
            
            # マニュアル検索エンジンのヘルスチェック
            if self.manual_engine:
                health_status['manual_engine'] = self.manual_engine.health_check()
            
            # 全体のヘルスは少なくとも一つのエンジンが正常であればOK
            health_status['overall'] = (
                health_status['faq_engine'] or 
                health_status['manual_engine']
            )
            
            logger.info(f"統合検索エンジンのヘルスチェック: {health_status}")
            return health_status
            
        except Exception as e:
            logger.error(f"ヘルスチェックに失敗しました: {e}")
            return health_status


# グローバルインスタンス
_unified_search_engine = None

def get_unified_search_engine() -> UnifiedSearchEngine:
    """統合検索エンジンのグローバルインスタンスを取得"""
    global _unified_search_engine
    if _unified_search_engine is None:
        _unified_search_engine = UnifiedSearchEngine()
    return _unified_search_engine