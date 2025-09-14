"""
Streamlit版UIの質問回答表示
サポートボット用のWebインターフェース
"""

import streamlit as st
import requests
import json
import sys
from pathlib import Path
from datetime import datetime
import time

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from src.configs import config

# ページ設定
st.set_page_config(
    page_title="サポートボット",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.question-box {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
}
.answer-box {
    background-color: #e8f4fd;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #1f77b4;
    margin: 1rem 0;
}
.confidence-high { color: #28a745; }
.confidence-medium { color: #ffc107; }
.confidence-low { color: #dc3545; }
.source-item {
    background-color: #f8f9fa;
    padding: 0.5rem;
    margin: 0.25rem 0;
    border-radius: 0.25rem;
    border-left: 3px solid #6c757d;
}
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'api_url' not in st.session_state:
    # クライアント側は常にlocalhostでAPIにアクセス
    api_host = "localhost" if config.APP_HOST == "0.0.0.0" else config.APP_HOST
    st.session_state.api_url = f"http://{api_host}:{config.APP_PORT}"


def check_api_health():
    """APIのヘルスチェック"""
    try:
        response = requests.get(f"{st.session_state.api_url}/health", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"APIエラー: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, f"接続エラー: {str(e)}"


def send_question(question: str):
    """APIに質問を送信"""
    try:
        payload = {"question": question}
        response = requests.post(
            f"{st.session_state.api_url}/ask",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"APIエラー: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"通信エラー: {str(e)}"


def format_confidence(confidence: float) -> str:
    """信頼度を色付きで表示"""
    if confidence >= 0.7:
        return f'<span class="confidence-high">高 ({confidence:.1%})</span>'
    elif confidence >= 0.4:
        return f'<span class="confidence-medium">中 ({confidence:.1%})</span>'
    else:
        return f'<span class="confidence-low">低 ({confidence:.1%})</span>'


def main():
    """メイン関数"""
    
    # タイトル
    st.markdown('<h1 class="main-header">🤖 サポートボット</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # サイドバー
    with st.sidebar:
        st.header("⚙️ システム設定")
        
        # API接続設定
        st.subheader("API接続")
        # UIではlocalhostを表示（0.0.0.0の場合）
        display_host = "localhost" if config.APP_HOST == "0.0.0.0" else config.APP_HOST
        api_host = st.text_input("APIホスト", value=display_host)
        api_port = st.number_input("APIポート", value=config.APP_PORT, min_value=1, max_value=65535)
        
        if st.button("接続設定を更新"):
            st.session_state.api_url = f"http://{api_host}:{api_port}"
            st.success("設定を更新しました")
        
        # ヘルスチェック
        st.subheader("システム状態")
        if st.button("状態を確認"):
            is_healthy, health_data = check_api_health()
            if is_healthy:
                st.success("✅ API正常")
                with st.expander("詳細情報"):
                    st.json(health_data)
            else:
                st.error(f"❌ API異常: {health_data}")
        
        # 履歴クリア
        st.subheader("会話履歴")
        if st.button("履歴をクリア"):
            st.session_state.conversation_history = []
            st.success("履歴をクリアしました")
        
        # 使用方法
        st.subheader("使用方法")
        st.markdown("""
        1. 下のテキストエリアに質問を入力
        2. 質問を送信ボタンをクリック
        3. FAQやマニュアルから回答を表示
        
        **質問例:**
        - 勤怠管理システムにログインできません
        - 有給申請はどこから行いますか？
        - 会議室の予約方法を教えてください
        """)
    
    # メインエリア
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 質問入力")
        
        # 質問入力エリア
        question = st.text_area(
            "質問を入力してください:",
            height=100,
            placeholder="例: 勤怠管理システムにログインできません"
        )
        
        # 送信ボタン
        col_send, col_clear = st.columns([1, 1])
        
        with col_send:
            if st.button("📤 質問を送信", type="primary"):
                if question.strip():
                    with st.spinner("回答を生成中..."):
                        success, result = send_question(question.strip())
                        
                        if success:
                            # 会話履歴に追加
                            st.session_state.conversation_history.append({
                                'timestamp': datetime.now(),
                                'question': question.strip(),
                                'response': result
                            })
                            st.success("回答が完了しました")
                        else:
                            st.error(f"エラーが発生しました: {result}")
                else:
                    st.warning("質問を入力してください")
        
        with col_clear:
            if st.button("🗑️ クリア"):
                question = ""
                st.experimental_rerun()
    
    with col2:
        st.subheader("📊 統計情報")
        
        # 簡単な統計表示
        total_questions = len(st.session_state.conversation_history)
        if total_questions > 0:
            recent_confidence = st.session_state.conversation_history[-1]['response'].get('confidence', 0)
            avg_confidence = sum(h['response'].get('confidence', 0) for h in st.session_state.conversation_history) / total_questions
            
            st.metric("総質問数", total_questions)
            st.metric("最新の信頼度", f"{recent_confidence:.1%}")
            st.metric("平均信頼度", f"{avg_confidence:.1%}")
        else:
            st.info("まだ質問がありません")
    
    # 会話履歴表示
    st.subheader("📋 会話履歴")
    
    if st.session_state.conversation_history:
        # 最新の質問から表示
        for i, conv in enumerate(reversed(st.session_state.conversation_history)):
            with st.expander(f"💬 {conv['question'][:50]}... ({conv['timestamp'].strftime('%H:%M:%S')})", expanded=(i==0)):
                
                # 質問表示
                st.markdown(f'<div class="question-box"><strong>質問:</strong> {conv["question"]}</div>', unsafe_allow_html=True)
                
                # 回答表示
                response_data = conv['response']
                answer = response_data.get('answer', 'エラー: 回答が取得できませんでした')
                confidence = response_data.get('confidence', 0)
                processing_time = response_data.get('processing_time', 0)
                sources = response_data.get('sources', [])
                
                st.markdown(f'<div class="answer-box"><strong>回答:</strong><br>{answer}</div>', unsafe_allow_html=True)
                
                # 詳細情報
                col_conf, col_time, col_sources = st.columns(3)
                
                with col_conf:
                    st.markdown(f"**信頼度:** {format_confidence(confidence)}", unsafe_allow_html=True)
                
                with col_time:
                    st.markdown(f"**処理時間:** {processing_time:.2f}秒")
                
                with col_sources:
                    st.markdown(f"**参照数:** {len(sources)}件")
                
                # 参照情報
                if sources:
                    st.markdown("**参照した情報:**")
                    for j, source in enumerate(sources, 1):
                        source_info = f"[{j}] {source.get('source', '')} (スコア: {source.get('score', 0):.2f})"
                        st.markdown(f'<div class="source-item">{source_info}</div>', unsafe_allow_html=True)
    else:
        st.info("会話履歴がありません。上記から質問してください。")
    
    # フッター
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "🤖 Support Bot MVP v1.0.0 | "
        f"API: {st.session_state.api_url}"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()