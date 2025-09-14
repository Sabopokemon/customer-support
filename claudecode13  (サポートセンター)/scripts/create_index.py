"""
PDF/CSVを処理してベクトル埋め込みを生成
埋め込みをChromaDBに格納するインデックス作成スクリプト
"""

import asyncio
import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import uuid

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.configs import config
from src.custom_logger import get_module_logger
from src.models import FAQItem, ManualSection

logger = get_module_logger("create_index")


class DocumentProcessor:
    """ドキュメント処理クラス"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.chroma_client = None
        self.collection = None
    
    def connect_to_chroma(self):
        """ChromaDBに接続"""
        try:
            # ChromaDBクライアントを初期化
            self.chroma_client = chromadb.HttpClient(
                host=config.CHROMA_HOST,
                port=config.CHROMA_PORT,
                settings=Settings(allow_reset=True)
            )
            
            # コレクション取得または作成
            try:
                self.collection = self.chroma_client.get_collection(
                    name=config.CHROMA_COLLECTION_NAME
                )
                logger.info(f"既存のコレクション '{config.CHROMA_COLLECTION_NAME}' に接続しました")
            except:
                self.collection = self.chroma_client.create_collection(
                    name=config.CHROMA_COLLECTION_NAME,
                    metadata={"description": "Support bot knowledge base"}
                )
                logger.info(f"新しいコレクション '{config.CHROMA_COLLECTION_NAME}' を作成しました")
                
        except Exception as e:
            logger.error(f"ChromaDBへの接続に失敗しました: {e}")
            raise
    
    def process_faq_csv(self, csv_path: Path) -> List[Dict[str, Any]]:
        """FAQのCSVファイルを処理"""
        try:
            logger.info(f"FAQファイルを処理中: {csv_path}")
            
            # CSVファイルを読み込み
            df = pd.read_csv(csv_path, encoding='utf-8')
            
            documents = []
            for index, row in df.iterrows():
                # FAQ項目を作成
                faq_item = FAQItem(
                    question=str(row['question']),
                    answer=str(row['answer'])
                )
                
                # ドキュメント形式に変換
                content = f"質問: {faq_item.question}\n回答: {faq_item.answer}"
                
                doc = {
                    'id': f"faq_{index}_{uuid.uuid4().hex[:8]}",
                    'content': content,
                    'metadata': {
                        'source': 'FAQ',
                        'question': faq_item.question,
                        'answer': faq_item.answer,
                        'type': 'faq',
                        'index': index
                    }
                }
                documents.append(doc)
            
            logger.info(f"FAQ {len(documents)}件を処理しました")
            return documents
            
        except Exception as e:
            logger.error(f"FAQファイルの処理に失敗しました: {e}")
            raise
    
    def process_manual_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """PDFマニュアルを処理（サンプル実装）"""
        try:
            logger.info(f"PDFファイルを処理中: {pdf_path}")
            
            # 実際のPDF処理ライブラリが必要
            # ここではサンプルデータを使用
            documents = []
            
            sample_sections = [
                {
                    'title': '勤怠管理',
                    'content': 'この章では勤怠管理システムの使用方法について説明します。',
                    'page': 1
                },
                {
                    'title': '有給申請',
                    'content': '有給申請を行うには以下の手順に従ってください。',
                    'page': 2
                }
            ]
            
            for i, section in enumerate(sample_sections):
                doc = {
                    'id': f"manual_{i}_{uuid.uuid4().hex[:8]}",
                    'content': f"タイトル: {section['title']}\n内容: {section['content']}",
                    'metadata': {
                        'source': f'Manual: {pdf_path.name}',
                        'title': section['title'],
                        'page': section['page'],
                        'type': 'manual',
                        'file_path': str(pdf_path)
                    }
                }
                documents.append(doc)
            
            logger.info(f"マニュアル {len(documents)}セクションを処理しました")
            return documents
            
        except Exception as e:
            logger.error(f"PDFファイルの処理に失敗しました: {e}")
            raise
    
    def embed_documents(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """ドキュメントを埋め込み"""
        try:
            logger.info(f"{len(documents)}件のドキュメントを埋め込み中...")
            
            contents = [doc['content'] for doc in documents]
            embeddings = self.embedding_model.encode(contents, show_progress_bar=True)
            
            logger.info("埋め込みが完了しました")
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"埋め込みに失敗しました: {e}")
            raise
    
    def add_to_chroma(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]):
        """ChromaDBにドキュメントを追加"""
        try:
            logger.info(f"{len(documents)}件のドキュメントをChromaDBに追加中...")
            
            ids = [doc['id'] for doc in documents]
            contents = [doc['content'] for doc in documents]
            metadatas = [doc['metadata'] for doc in documents]
            
            self.collection.add(
                ids=ids,
                documents=contents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info("ChromaDBへの追加が完了しました")
            
        except Exception as e:
            logger.error(f"ChromaDBへの追加に失敗しました: {e}")
            raise
    
    def create_index(self):
        """インデックスを作成"""
        try:
            logger.info("インデックス作成を開始します")
            
            # ChromaDBに接続
            self.connect_to_chroma()
            
            all_documents = []
            
            # FAQファイルを処理
            if config.FAQ_FILE.exists():
                faq_docs = self.process_faq_csv(config.FAQ_FILE)
                all_documents.extend(faq_docs)
            else:
                logger.warning(f"FAQファイルが見つかりません: {config.FAQ_FILE}")
            
            # マニュアルディレクトリを処理
            if config.MANUAL_DIR.exists():
                for pdf_file in config.MANUAL_DIR.glob("*.pdf"):
                    manual_docs = self.process_manual_pdf(pdf_file)
                    all_documents.extend(manual_docs)
            else:
                logger.warning(f"マニュアルディレクトリが見つかりません: {config.MANUAL_DIR}")
            
            if not all_documents:
                logger.error("処理するドキュメントが見つかりません")
                return False
            
            # 埋め込み処理
            embeddings = self.embed_documents(all_documents)
            
            # ChromaDBに追加
            self.add_to_chroma(all_documents, embeddings)
            
            # 結果表示
            count = self.collection.count()
            logger.info(f"インデックス作成完了: 総ドキュメント数 {count}")
            
            return True
            
        except Exception as e:
            logger.error(f"インデックス作成に失敗しました: {e}")
            return False


def main():
    """メイン関数"""
    try:
        # 設定を検証
        config.validate()
        
        # プロセッサーを初期化
        processor = DocumentProcessor()
        
        # インデックスを作成
        success = processor.create_index()
        
        if success:
            logger.info("✅ インデックス作成が成功しました")
            return 0
        else:
            logger.error("❌ インデックス作成に失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"❌ 予期しないエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)