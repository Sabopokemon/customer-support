"""
既存インデックスの削除
ChromaDBのコレクション削除スクリプト
"""

import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.configs import config
from src.custom_logger import get_module_logger

logger = get_module_logger("delete_index")


class IndexDeleter:
    """インデックス削除クラス"""
    
    def __init__(self):
        self.chroma_client = None
    
    def connect_to_chroma(self):
        """ChromaDBに接続"""
        try:
            self.chroma_client = chromadb.HttpClient(
                host=config.CHROMA_HOST,
                port=config.CHROMA_PORT,
                settings=Settings(allow_reset=True)
            )
            logger.info("ChromaDBに接続しました")
        except Exception as e:
            logger.error(f"ChromaDBへの接続に失敗しました: {e}")
            raise
    
    def list_collections(self):
        """既存のコレクション一覧を表示"""
        try:
            collections = self.chroma_client.list_collections()
            if collections:
                logger.info("既存のコレクション:")
                for collection in collections:
                    count = collection.count()
                    logger.info(f"  - {collection.name}: {count}件のドキュメント")
            else:
                logger.info("コレクションが見つかりません")
            return collections
        except Exception as e:
            logger.error(f"コレクション一覧の取得に失敗しました: {e}")
            return []
    
    def delete_collection(self, collection_name: str, force: bool = False):
        """指定したコレクションを削除"""
        try:
            # コレクションの存在確認
            try:
                collection = self.chroma_client.get_collection(collection_name)
                count = collection.count()
                logger.info(f"コレクション '{collection_name}' ({count}件のドキュメント) を削除対象に特定しました")
            except:
                logger.warning(f"コレクション '{collection_name}' が見つかりません")
                return False
            
            # 確認処理（force=Falseの場合）
            if not force:
                response = input(f"\nコレクション '{collection_name}' を削除しますか? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    logger.info("削除をキャンセルしました")
                    return False
            
            # コレクション削除
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"✅ コレクション '{collection_name}' を削除しました")
            return True
            
        except Exception as e:
            logger.error(f"コレクションの削除に失敗しました: {e}")
            return False
    
    def delete_all_collections(self, force: bool = False):
        """すべてのコレクションを削除"""
        try:
            collections = self.chroma_client.list_collections()
            if not collections:
                logger.info("削除するコレクションがありません")
                return True
            
            logger.info(f"{len(collections)}個のコレクションが見つかりました")
            
            # 確認処理（force=Falseの場合）
            if not force:
                response = input(f"\nすべてのコレクションを削除しますか? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    logger.info("削除をキャンセルしました")
                    return False
            
            # コレクション削除
            success_count = 0
            for collection in collections:
                try:
                    self.chroma_client.delete_collection(collection.name)
                    logger.info(f"  ✅ コレクション '{collection.name}' を削除しました")
                    success_count += 1
                except Exception as e:
                    logger.error(f"  ❌ コレクション '{collection.name}' の削除に失敗: {e}")
            
            logger.info(f"削除完了: {success_count}/{len(collections)}個のコレクションを削除しました")
            return success_count == len(collections)
            
        except Exception as e:
            logger.error(f"全コレクション削除に失敗しました: {e}")
            return False
    
    def reset_database(self, force: bool = False):
        """データベース全体をリセット"""
        try:
            logger.warning("⚠️  データベース全体のリセット処理を行います")
            
            # 確認処理（force=Falseの場合）
            if not force:
                response = input("\n本当にデータベース全体をリセットしますか? (y/N): ")
                if response.lower() not in ['y', 'yes']:
                    logger.info("処理をキャンセルしました")
                    return False
            
            # データベースをリセット
            self.chroma_client.reset()
            logger.info("✅ データベースのリセットが完了しました")
            return True
            
        except Exception as e:
            logger.error(f"データベースのリセットに失敗しました: {e}")
            return False


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ChromaDBのインデックスを削除")
    parser.add_argument(
        '--collection', 
        type=str, 
        help="削除するコレクション名（指定なしはデフォルトコレクション）"
    )
    parser.add_argument(
        '--all', 
        action='store_true', 
        help="すべてのコレクションを削除"
    )
    parser.add_argument(
        '--reset', 
        action='store_true', 
        help="データベース全体をリセット"
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help="確認処理をスキップ"
    )
    parser.add_argument(
        '--list', 
        action='store_true', 
        help="コレクション一覧を表示するだけ"
    )
    
    args = parser.parse_args()
    
    try:
        deleter = IndexDeleter()
        deleter.connect_to_chroma()
        
        # コレクション一覧表示
        if args.list:
            deleter.list_collections()
            return 0
        
        # データベースリセット
        if args.reset:
            success = deleter.reset_database(args.force)
            return 0 if success else 1
        
        # 全コレクション削除
        if args.all:
            success = deleter.delete_all_collections(args.force)
            return 0 if success else 1
        
        # 個別コレクション削除
        collection_name = args.collection or config.CHROMA_COLLECTION_NAME
        success = deleter.delete_collection(collection_name, args.force)
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n処理が中断されました")
        return 0
    except Exception as e:
        logger.error(f"❌ 予期しないエラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)