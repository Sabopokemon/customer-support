"""
FAQのCSVファイル検索エンジン
ChromaDBを使用してFAQナレッジベースを検索
"""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.configs import config
from src.custom_logger import get_module_logger
from src.models import SearchResult

logger = get_module_logger("search_qa")


class FAQSearchEngine:
    """FAQ検索エンジン"""
    
    def __init__(self):
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        """検索エンジンを初期化"""
        try:
            # 埋め込みモデルを読み込み
            logger.info(f"埋め込みモデルを読み込み中: {config.EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
            
            # ChromaDBに接続
            self._connect_to_chroma()
            
            logger.info("FAQ検索エンジンの初期化が完了しました")
            
        except Exception as e:
            logger.error(f"FAQ検索エンジンの初期化に失敗しました: {e}")
            raise
    
    def _connect_to_chroma(self):
        """ChromaDBに接続"""
        try:
            self.chroma_client = chromadb.HttpClient(
                host=config.CHROMA_HOST,
                port=config.CHROMA_PORT,
                settings=Settings(allow_reset=True)
            )
            
            # FAQコレクションを取得
            self.collection = self.chroma_client.get_collection(
                name=config.CHROMA_COLLECTION_NAME
            )
            
            # コレクションの件数を確認
            count = self.collection.count()
            logger.info(f"ChromaDBに接続しました (コレクション: {config.CHROMA_COLLECTION_NAME}, ドキュメント数: {count})")
            
        except Exception as e:
            logger.error(f"ChromaDBサーバーへの接続に失敗しました: {e}")
            logger.error("ChromaDBが動作していることを確認してください")
            raise
    
    def search_faq(
        self, 
        query: str, 
        max_results: int = None,
        min_score: float = None
    ) -> List[SearchResult]:
        """
        FAQ検索を実行
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
            min_score: 最低類似度スコア
        
        Returns:
            検索結果のリスト
        """
        try:
            if not query.strip():
                logger.warning("空の検索クエリが指定されました")
                return []
            
            # デフォルト値を設定
            max_results = max_results or config.MAX_SEARCH_RESULTS
            min_score = min_score or config.SIMILARITY_THRESHOLD
            
            logger.info(f"FAQ検索を実行: '{query}' (最大{max_results}件, 最低スコア{min_score})")
            
            # クエリを埋め込みベクトルに変換
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # ChromaDBで類似度検索を実行
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                where={"type": "faq"},  # FAQのみを対象
                include=["documents", "metadatas", "distances"]
            )
            
            # 結果を処理
            search_results = self._process_search_results(results, min_score)
            
            logger.info(f"FAQ検索完了: {len(search_results)}件の結果を取得")
            return search_results
            
        except Exception as e:
            logger.error(f"FAQ検索に失敗しました: {e}")
            return []
    
    def _process_search_results(
        self, 
        raw_results: Dict[str, Any], 
        min_score: float
    ) -> List[SearchResult]:
        """検索結果を処理してSearchResultオブジェクトに変換"""
        search_results = []
        
        if not raw_results['documents'] or not raw_results['documents'][0]:
            return search_results
        
        documents = raw_results['documents'][0]
        metadatas = raw_results['metadatas'][0]
        distances = raw_results['distances'][0]
        
        for doc, metadata, distance in zip(documents, metadatas, distances):
            # 距離を類似度スコアに変換（距離が小さいほど類似度が高い）
            similarity_score = max(0, 1 - distance)
            
            # 最低スコア以上の結果のみを追加
            if similarity_score >= min_score:
                # FAQ形式の内容を整形
                content = self._format_faq_content(metadata)
                
                search_result = SearchResult(
                    content=content,
                    source=f"FAQ: {metadata.get('question', 'Unknown')}",
                    score=similarity_score,
                    metadata={
                        'type': 'faq',
                        'question': metadata.get('question', ''),
                        'answer': metadata.get('answer', ''),
                        'original_distance': distance
                    }
                )
                search_results.append(search_result)
        
        # スコアの高い順にソート
        search_results.sort(key=lambda x: x.score, reverse=True)
        
        return search_results
    
    def _format_faq_content(self, metadata: Dict[str, Any]) -> str:
        """FAQメタデータをユーザー向け形式に整形"""
        question = metadata.get('question', '')
        answer = metadata.get('answer', '')
        
        return f"質問: {question}\n回答: {answer}"
    
    def search_by_keywords(
        self, 
        keywords: List[str], 
        max_results: int = None
    ) -> List[SearchResult]:
        """
        キーワードリストによるFAQ検索
        
        Args:
            keywords: 検索キーワードのリスト
            max_results: 最大結果数
        
        Returns:
            検索結果のリスト
        """
        try:
            # キーワードを結合して一つのクエリに
            query = " ".join(keywords)
            logger.info(f"キーワード検索を実行: {keywords}")
            
            return self.search_faq(query, max_results)
            
        except Exception as e:
            logger.error(f"キーワード検索に失敗しました: {e}")
            return []
    
    def get_random_faqs(self, count: int = 5) -> List[SearchResult]:
        """
        ランダムなFAQを取得してサンプル表示用
        
        Args:
            count: 取得数
        
        Returns:
            FAQ結果のリスト
        """
        try:
            logger.info(f"ランダムFAQを{count}件取得中...")
            
            # ダミークエリで検索（実際の実装ではランダム選択が必要）
            results = self.collection.query(
                query_embeddings=[self.embedding_model.encode(["サンプル"]).tolist()[0]],
                n_results=count,
                where={"type": "faq"},
                include=["documents", "metadatas", "distances"]
            )
            
            return self._process_search_results(results, min_score=0.0)
            
        except Exception as e:
            logger.error(f"ランダムFAQ取得に失敗しました: {e}")
            return []
    
    def health_check(self) -> bool:
        """検索エンジンのヘルスチェック"""
        try:
            # コレクションの件数を取得
            count = self.collection.count()
            if count == 0:
                logger.warning("FAQドキュメントが格納されていません")
                return False
            
            # 簡単な検索テストを実行
            test_results = self.search_faq("テスト", max_results=1)
            
            logger.info(f"FAQ検索エンジンは正常に動作しています (ドキュメント数: {count})")
            return True
            
        except Exception as e:
            logger.error(f"FAQ検索エンジンのヘルスチェックに失敗しました: {e}")
            return False


# グローバルインスタンス管理
_faq_search_engine = None

def get_faq_search_engine() -> FAQSearchEngine:
    """FAQ検索エンジンのグローバルインスタンスを取得"""
    global _faq_search_engine
    if _faq_search_engine is None:
        _faq_search_engine = FAQSearchEngine()
    return _faq_search_engine


def main():
    """テスト用のメイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FAQ検索エンジンのテスト")
    parser.add_argument('query', help='検索クエリ')
    parser.add_argument('--max-results', type=int, default=5, help='最大結果数')
    parser.add_argument('--min-score', type=float, default=0.5, help='最低類似度スコア')
    
    args = parser.parse_args()
    
    try:
        # 検索エンジンを初期化
        engine = get_faq_search_engine()
        
        # ヘルスチェック
        if not engine.health_check():
            logger.error("検索エンジンのヘルスチェックに失敗しました")
            return 1
        
        # 検索を実行
        results = engine.search_faq(
            query=args.query,
            max_results=args.max_results,
            min_score=args.min_score
        )
        
        # 結果を表示
        print(f"\n検索結果: '{args.query}' ({len(results)}件)")
        print("=" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"\n【結果 {i}】(類似度: {result.score:.3f})")
            print(f"ソース: {result.source}")
            print(result.content)
            print("-" * 30)
        
        if not results:
            print("該当する結果が見つかりませんでした。")
        
        return 0
        
    except Exception as e:
        logger.error(f"テスト実行に失敗しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())