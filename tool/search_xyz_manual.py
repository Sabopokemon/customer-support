"""
PDF/マニュアル検索エンジン
ChromaDBを使用してPDFマニュアルナレッジベースの情報検索を実行
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

logger = get_module_logger("search_manual")


class ManualSearchEngine:
    """マニュアル検索エンジン"""
    
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
            
            logger.info("マニュアル検索エンジンの初期化が完了しました")
            
        except Exception as e:
            logger.error(f"マニュアル検索エンジンの初期化に失敗しました: {e}")
            raise
    
    def _connect_to_chroma(self):
        """ChromaDBに接続"""
        try:
            self.chroma_client = chromadb.HttpClient(
                host=config.CHROMA_HOST,
                port=config.CHROMA_PORT,
                settings=Settings(allow_reset=True)
            )
            
            # コレクションを取得
            self.collection = self.chroma_client.get_collection(
                name=config.CHROMA_COLLECTION_NAME
            )
            
            # マニュアルドキュメントの件数を確認
            manual_count = self._count_manual_documents()
            logger.info(f"ChromaDBに接続しました (マニュアルドキュメント数: {manual_count})")
            
        except Exception as e:
            logger.error(f"ChromaDBサーバーへの接続に失敗しました: {e}")
            logger.error("ChromaDBが動作していることを確認してください")
            raise
    
    def _count_manual_documents(self) -> int:
        """マニュアルドキュメントの件数を取得"""
        try:
            # ダミークエリでドキュメントの件数を確認
            results = self.collection.query(
                query_embeddings=[self.embedding_model.encode(["dummy"]).tolist()[0]],
                n_results=1000,  # 大きな数を指定
                where={"type": "manual"},
                include=["metadatas"]
            )
            return len(results['metadatas'][0]) if results['metadatas'] and results['metadatas'][0] else 0
        except:
            return 0
    
    def search_manual(
        self, 
        query: str, 
        max_results: int = None,
        min_score: float = None
    ) -> List[SearchResult]:
        """
        マニュアル検索を実行
        
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
            
            logger.info(f"マニュアル検索を実行: '{query}' (最大{max_results}件, 最低スコア{min_score})")
            
            # クエリを埋め込みベクトルに変換
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # ChromaDBで類似度検索を実行（マニュアルのみ）
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                where={"type": "manual"},  # マニュアルのみを対象
                include=["documents", "metadatas", "distances"]
            )
            
            # 結果を処理
            search_results = self._process_search_results(results, min_score)
            
            logger.info(f"マニュアル検索完了: {len(search_results)}件の結果を取得")
            return search_results
            
        except Exception as e:
            logger.error(f"マニュアル検索に失敗しました: {e}")
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
            # 距離を類似度スコアに変換
            similarity_score = max(0, 1 - distance)
            
            # 最低スコア以上の結果のみを追加
            if similarity_score >= min_score:
                # マニュアル形式の内容を整形
                content = self._format_manual_content(metadata, doc)
                
                search_result = SearchResult(
                    content=content,
                    source=self._format_source_info(metadata),
                    score=similarity_score,
                    metadata={
                        'type': 'manual',
                        'title': metadata.get('title', ''),
                        'page': metadata.get('page', 0),
                        'file_path': metadata.get('file_path', ''),
                        'original_distance': distance
                    }
                )
                search_results.append(search_result)
        
        # スコアの高い順にソート
        search_results.sort(key=lambda x: x.score, reverse=True)
        
        return search_results
    
    def _format_manual_content(self, metadata: Dict[str, Any], document: str) -> str:
        """マニュアル内容をユーザー向け形式に整形"""
        title = metadata.get('title', '不明')
        page = metadata.get('page', '')
        
        page_info = f" (ページ {page})" if page else ""
        
        # ドキュメントが既存の形式の場合は内容部分のみ抽出
        # "タイトル: xxx\n内容: yyy" の形式から内容を取得
        if "内容: " in document:
            content = document.split("内容: ", 1)[1]
        else:
            content = document
        
        return f"{title}{page_info}\n{content}"
    
    def _format_source_info(self, metadata: Dict[str, Any]) -> str:
        """ソース情報を整形"""
        file_path = metadata.get('file_path', '')
        title = metadata.get('title', '')
        page = metadata.get('page', '')
        
        if file_path:
            file_name = Path(file_path).name
            source = f"マニュアル: {file_name}"
        else:
            source = "マニュアル"
        
        if title:
            source += f" - {title}"
        
        if page:
            source += f" (ページ {page})"
        
        return source
    
    def search_by_section(
        self, 
        section_title: str, 
        max_results: int = None
    ) -> List[SearchResult]:
        """
        セクション名で絞り込み検索
        
        Args:
            section_title: セクション名
            max_results: 最大結果数
        
        Returns:
            検索結果のリスト
        """
        try:
            logger.info(f"セクション検索を実行: '{section_title}'")
            
            # セクション名をクエリとして検索
            return self.search_manual(section_title, max_results)
            
        except Exception as e:
            logger.error(f"セクション検索に失敗しました: {e}")
            return []
    
    def search_by_page_range(
        self, 
        query: str,
        start_page: int,
        end_page: int,
        max_results: int = None
    ) -> List[SearchResult]:
        """
        ページ範囲を指定してマニュアル検索
        
        Args:
            query: 検索クエリ
            start_page: 開始ページ
            end_page: 終了ページ
            max_results: 最大結果数
        
        Returns:
            検索結果のリスト
        """
        try:
            logger.info(f"ページ範囲検索を実行: '{query}' (ページ {start_page}-{end_page})")
            
            # 全体検索を実行してから結果を絞り込み
            all_results = self.search_manual(query, max_results * 2)  # 多く取得
            
            # ページ範囲で絞り込み
            filtered_results = []
            for result in all_results:
                page = result.metadata.get('page', 0)
                if start_page <= page <= end_page:
                    filtered_results.append(result)
                    if len(filtered_results) >= (max_results or config.MAX_SEARCH_RESULTS):
                        break
            
            logger.info(f"ページ範囲検索完了: {len(filtered_results)}件の結果を取得")
            return filtered_results
            
        except Exception as e:
            logger.error(f"ページ範囲検索に失敗しました: {e}")
            return []
    
    def get_manual_outline(self) -> List[Dict[str, Any]]:
        """
        マニュアルの目次情報を取得
        
        Returns:
            セクション情報のリスト
        """
        try:
            logger.info("マニュアルの目次を取得中...")
            
            # すべてのマニュアルドキュメントを取得
            results = self.collection.query(
                query_embeddings=[self.embedding_model.encode(["目次"]).tolist()[0]],
                n_results=100,  # 多く取得
                where={"type": "manual"},
                include=["metadatas"]
            )
            
            outline = []
            if results['metadatas'] and results['metadatas'][0]:
                for metadata in results['metadatas'][0]:
                    section_info = {
                        'title': metadata.get('title', '不明'),
                        'page': metadata.get('page', 0),
                        'file_path': metadata.get('file_path', '')
                    }
                    outline.append(section_info)
            
            # ページ番号でソート
            outline.sort(key=lambda x: x.get('page', 0))
            
            logger.info(f"目次取得完了: {len(outline)}個のセクション")
            return outline
            
        except Exception as e:
            logger.error(f"目次取得に失敗しました: {e}")
            return []
    
    def health_check(self) -> bool:
        """検索エンジンのヘルスチェック"""
        try:
            # マニュアルドキュメント数を確認
            manual_count = self._count_manual_documents()
            if manual_count == 0:
                logger.warning("マニュアルドキュメントが格納されていません")
                return False
            
            # 簡単な検索テストを実行
            test_results = self.search_manual("テスト", max_results=1)
            
            logger.info(f"マニュアル検索エンジンは正常に動作しています (ドキュメント数: {manual_count})")
            return True
            
        except Exception as e:
            logger.error(f"マニュアル検索エンジンのヘルスチェックに失敗しました: {e}")
            return False


# グローバルインスタンス管理
_manual_search_engine = None

def get_manual_search_engine() -> ManualSearchEngine:
    """マニュアル検索エンジンのグローバルインスタンスを取得"""
    global _manual_search_engine
    if _manual_search_engine is None:
        _manual_search_engine = ManualSearchEngine()
    return _manual_search_engine


def main():
    """テスト用のメイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="マニュアル検索エンジンのテスト")
    parser.add_argument('query', help='検索クエリ')
    parser.add_argument('--max-results', type=int, default=5, help='最大結果数')
    parser.add_argument('--min-score', type=float, default=0.3, help='最低類似度スコア')
    parser.add_argument('--outline', action='store_true', help='目次を表示')
    
    args = parser.parse_args()
    
    try:
        # 検索エンジンを初期化
        engine = get_manual_search_engine()
        
        # ヘルスチェック
        if not engine.health_check():
            logger.warning("マニュアル検索エンジンのヘルスチェックに失敗しました")
        
        # 目次表示
        if args.outline:
            outline = engine.get_manual_outline()
            print("\n=== マニュアル目次:")
            print("=" * 50)
            for section in outline:
                print(f"ページ {section['page']:2d}: {section['title']}")
            return 0
        
        # 検索を実行
        results = engine.search_manual(
            query=args.query,
            max_results=args.max_results,
            min_score=args.min_score
        )
        
        # 結果を表示
        print(f"\n=== マニュアル検索結果: '{args.query}' ({len(results)}件)")
        print("=" * 60)
        
        for i, result in enumerate(results, 1):
            print(f"\n【結果 {i}】(類似度: {result.score:.3f})")
            print(f"ソース: {result.source}")
            print(result.content)
            print("-" * 40)
        
        if not results:
            print("該当する結果が見つかりませんでした。")
            print("別のキーワードで検索してください。")
        
        return 0
        
    except Exception as e:
        logger.error(f"テスト実行に失敗しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())