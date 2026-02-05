"""
AIプロンプトテンプレート集
回答生成用のプロンプト定義
"""

from typing import List, Dict, Any
from .models import SearchResult


class PromptTemplates:
    """プロンプトテンプレート管理クラス"""
    
    # システムロール（AIアシスタントの基本設定）
    SYSTEM_ROLE = """
あなたは会社内のサポートボットです。
以下の指針に従ってください：

基本姿勢：
- 会社内の従業員を助ける親切なアシスタント
- 正確で分かりやすい回答を心がける
- 分からないことは分からないと正直に答える

回答スタイル：
- 丁寧で親しみやすい口調
- 簡潔で要点を整理した内容
- 必要に応じて手順を番号付きで説明

注意点：
- 推測による回答は避ける
- 検索結果にない情報は「検索結果にありません」と伝える
- 機密情報に関わる質問には回答を控える
"""

    # FAQ専用の回答テンプレート
    FAQ_ANSWER_TEMPLATE = """
以下の質問に対して、検索結果の情報を基に回答してください。

ユーザーの質問：
{question}

関連する検索結果：
{search_results}

回答の要件：
1. 質問に直接答える内容を最初に書いてください
2. 上記の検索結果がある場合はそれらの情報を参考にしてください
3. 検索結果にない情報は推測せず、「情報が見つかりません」と伝えてください
4. 機密性の高い内容については適切に配慮してください

回答をお願いします：
"""

    # マニュアル専用の回答テンプレート
    MANUAL_ANSWER_TEMPLATE = """
以下のマニュアル検索結果を基に、ユーザーの質問に回答してください。

ユーザーの質問：
{question}

参照するマニュアル情報：
{search_results}

回答の要件：
1. マニュアルの内容を整理して説明してください
2. 手順がある場合は番号付きで整理してください
3. 重要なポイントがあれば強調してください
4. 不明な点があれば担当者への問い合わせを案内してください

回答をお願いします：
"""

    # 検索結果なしの場合のテンプレート
    NO_RESULTS_TEMPLATE = """
申し訳ございませんが、「{question}」に関する情報をFAQやマニュアルから見つけることができませんでした。

以下の対応をお勧めします：

1. 質問の表現を変えて再度お試しください
2. より具体的なキーワードで検索してください
3. 直接担当者にお問い合わせください：
   - 人事関連：内線1234
   - ITサポート：内線5678
   - 総務関連：内線9012

引き続きお困りのことがございましたら、お気軽にお声がけください。
"""

    # 複数ソースの統合回答テンプレート
    MULTI_SOURCE_TEMPLATE = """
以下の質問についてFAQとマニュアルの両方から関連情報が見つかりました。

ユーザーの質問：
{question}

FAQ情報：
{faq_results}

マニュアル情報：
{manual_results}

回答の要件：
1. FAQとマニュアルの情報を総合して包括的に回答してください
2. 検索結果がある場合はそれらの詳細な情報を活用してください
3. 両方の情報を統合して、より包括的で有用な回答を作成してください

総合した回答をお願いします：
"""

    @classmethod
    def format_search_results(cls, results: List[SearchResult]) -> str:
        """検索結果を読みやすい形式に整形"""
        if not results:
            return "参照する情報が見つかりませんでした"
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_result = f"""
結果 {i}（類似度: {result.score:.2f}）
ソース: {result.source}
内容: {result.content}
"""
            formatted_results.append(formatted_result)
        
        return "\n".join(formatted_results)

    @classmethod
    def generate_faq_prompt(cls, question: str, results: List[SearchResult]) -> str:
        """FAQ回答用のプロンプトを生成"""
        search_results_text = cls.format_search_results(results)
        return cls.FAQ_ANSWER_TEMPLATE.format(
            question=question,
            search_results=search_results_text
        )

    @classmethod
    def generate_manual_prompt(cls, question: str, results: List[SearchResult]) -> str:
        """マニュアル回答用のプロンプトを生成"""
        search_results_text = cls.format_search_results(results)
        return cls.MANUAL_ANSWER_TEMPLATE.format(
            question=question,
            search_results=search_results_text
        )

    @classmethod
    def generate_no_results_prompt(cls, question: str) -> str:
        """検索結果なしの場合のプロンプトを生成"""
        return cls.NO_RESULTS_TEMPLATE.format(question=question)

    @classmethod
    def generate_multi_source_prompt(
        cls, 
        question: str, 
        faq_results: List[SearchResult],
        manual_results: List[SearchResult]
    ) -> str:
        """複数ソース統合プロンプトを生成"""
        faq_text = cls.format_search_results(faq_results)
        manual_text = cls.format_search_results(manual_results)
        
        return cls.MULTI_SOURCE_TEMPLATE.format(
            question=question,
            faq_results=faq_text,
            manual_results=manual_text
        )


# グローバルインスタンス
prompts = PromptTemplates()