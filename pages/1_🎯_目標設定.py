import streamlit as st
import datetime
import time
# 💡 utils.py から共通の関数をインポート
from utils import load_data, save_data, generate_ai_strategy
from utils import check_password

# パスワードが通るまで、この先の画面描画や処理をストップさせる
if not check_password():
    st.stop()

# --- 初期設定 ---
st.title("🎯 目標設定とAI戦略立案")

# 💡 utils.py の load_data を使用（独自の load_json は削除しました）
goals = load_data("data/goals.json")
books = load_data("data/textbooks.json")

st.subheader("1. 学習目標とリソースの入力")
col1, col2 = st.columns(2)

with col1:
    # value=... の部分で、保存済みの値を初期値としてセットしています
    current_score = st.number_input("現在のスコア", 10, 990, int(goals.get("current_score", 400)), step=5)
    target_score = st.number_input("目標スコア", 10, 990, int(goals.get("target_score", 700)), step=5)

with col2:
    try:
        saved_date = datetime.date.fromisoformat(goals.get("exam_date", "2026-10-25"))
    except:
        # 万が一パースエラーになった場合の安全策
        saved_date = datetime.date(2026, 10, 25) 
    
    exam_date = st.date_input("試験日", saved_date)
    weekly_hours = st.number_input("1週間の学習時間（時間）", 1, 100, int(goals.get("weekly_hours", 10)))

# --- 保存処理 ---
def perform_save():
    new_data = {
        "current_score": current_score,
        "target_score": target_score,
        "exam_date": str(exam_date),
        "weekly_hours": weekly_hours
    }
    goals.update(new_data)
    # 💡 utils.py の save_data を使用
    save_data("data/goals.json", goals)

if st.button("💾 基本設定のみ保存"):
    perform_save()
    st.success("基本設定を保存しました！")

st.divider()

st.subheader("2. 🤖 AI戦略プランナー")
if st.button("✨ Geminiに戦略立案を依頼する（設定も保存）", type="primary"):
    # 1. フォーム内容の保存（これは一瞬なのでスピナーの外でOK）
    perform_save()

    # 2. utils.py に切り出した関数を使って戦略を生成！
    with st.spinner("インテリジェンスちゃむが作戦を練っています..."):
        # 💡 長いプロンプトやAPI呼び出しはすべて generate_ai_strategy の中で実行されます
        res = generate_ai_strategy()
        
        if "error" in res:
            st.error(f"エラーが発生しました: {res['error']}")
        else:
            st.balloons()
            st.success("設定の保存とAI戦略の策定が完了しました！")
            time.sleep(1.5)
            st.rerun()