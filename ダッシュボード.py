import streamlit as st
import datetime
from utils import load_data
from utils import check_password

# パスワードが通るまで、この先の画面描画や処理をストップさせる
if not check_password():
    st.stop()

goals = load_data("data/goals.json")
books = load_data("data/textbooks.json")
strategy = load_data("data/strategy.json")
progress = load_data("data/progress.json")
if not goals or not strategy:
    st.warning("⚠️ 左のメニューの「🎯 目標設定」から初期設定とAI戦略の立案を行ってください。")
    st.stop()

# ==========================================
# 💡 日数の計算（安全装置付き）
# ==========================================
# 1. 残り日数の計算（試験日を過ぎたら 0 になるよう max でガード）
exam_date = datetime.datetime.strptime(goals.get("exam_date"), "%Y-%m-%d").date()
days_left = max(0, (exam_date - datetime.date.today()).days)

# 2. 学習開始日の取得（データが無い場合は今日を仮の開始日とする安全な書き方）
today_str = datetime.date.today().strftime("%Y-%m-%d")
start_date_str = progress.get("_meta", {}).get("start_date", today_str)
start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
current_day = (datetime.date.today() - start_date).days + 1

# ==========================================
# 🏠 画面表示
# ==========================================
st.title("🏠 学習ダッシュボード")
st.write(f"試験まであと **{days_left}** 日。（学習開始から **Day {current_day}**）")
st.divider()

# --- 💡 進行日数（Day）の計算 ---
today_str = datetime.date.today().strftime("%Y-%m-%d")
start_date_str = progress.get("_meta", {}).get("start_date", today_str)
start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
current_day = (datetime.date.today() - start_date).days + 1

# --- 🌟 【新規追加】ストリーク（連続学習日数）のバッジ表示 ---

streak_count = progress.get("_meta", {}).get("streak_count", 0)
if streak_count >= 2:
    st.success(f"🔥 現在 **{streak_count}日連続** で学習中！素晴らしい継続力です！")
elif streak_count == 1:
    st.info("🔥 連続学習1日目！明日も記録をつけてストリークを伸ばしましょう！")

# --- 1. 📈 スコア予測と学習バランス ---
st.subheader("📈 学習時間から算出するスコア予測")
col1, col2, col3 = st.columns(3)

current = int(goals.get("current_score", 0))
target = int(goals.get("target_score", 0))

# 🌟 【変更】AIの予測値を捨てて、Pythonで現実的なスコアを計算する
exam_date_str = goals.get("exam_date")
exam_date = datetime.datetime.strptime(exam_date_str, "%Y-%m-%d").date()
days_left = max(0, (exam_date - datetime.date.today()).days)

# 目標設定画面で入力した1週間の学習時間を取得（キー名は実際のJSONに合わせてください）
weekly_hours = float(goals.get("weekly_hours", 10)) 
daily_hours = weekly_hours / 7
total_hours = days_left * daily_hours

# 💡 オックスフォード大のデータ準拠: 100点上げるのに約220時間必要と仮定
# (total_hours / 220) * 100 の計算式
expected_increase = int(total_hours / 2.2) 

# 現在のスコアに加算し、上限を990点にガードする
predicted = min(990, current + expected_increase)

col1.metric("現在のスコア", f"{current}点")
col2.metric("現実的な予想到達点", f"{predicted}点", f"{expected_increase}点 UP" if expected_increase > 0 else None)

diff = predicted - target
if diff >= 0:
    col3.metric("目標スコア", f"{target}点", "🎉 達成圏内！")
else:
    col3.metric("目標スコア", f"{target}点", f"{diff}点 (目標まであと少し)", delta_color="inverse")

# --- 2. トップアドバイス ---
st.subheader("🤖 AI戦略レポート")
st.info(f"**💡 アドバイス:**\n\n{strategy.get('strategy_advice', 'アドバイスがありません。')}")

# --- 3. 📅 学習スケジュール ---
st.subheader("📅 目標までの学習スケジュール")
st.write(f"🏃 現在のステータス: 学習開始から **Day {current_day}**")

timeline = strategy.get("schedule_timeline", [])
if timeline:
    for step in timeline:
        start = step.get('start_day', 0)
        end = step.get('end_day', 999)
        period = step.get('period', '時期未定')
        focus = step.get('focus', 'テーマ未定')
        
        is_current_phase = (isinstance(start, int) and isinstance(end, int) and start <= current_day <= end)
        
        if is_current_phase:
            title_text = f"📍 【現在進行中】 {period} (Day {start} 〜 {end}) : {focus}"
            expanded = True
        else:
            title_text = f"📌 {period} (Day {start} 〜 {end}) : {focus}"
            expanded = False
        
        with st.expander(title_text, expanded=expanded):
            if is_current_phase:
                st.success("🔥 現在あなたはこのフェーズにいます！デイリーミッションに沿って学習を進めましょう。")
            st.write(step.get("description", ""))
else:
    st.write("スケジュールのデータがありません。")

st.divider()

# --- 4. 🛒 不足パートと教材提案 ---
st.subheader("🛒 不足領域とオヌヌメ教材")
missing = strategy.get("missing_parts", [])
if missing:
    st.warning(f"**⚠️ 現在不足している対策パート:** {', '.join(missing)}")
    
recommended = strategy.get("recommended_items", [])
if recommended:
    st.write("上記の不足を補うため、以下の教材・アプリをおすすめします。")
    for item in recommended:
        icon = "📱" if item.get("type") == "app" else "📘"
        st.markdown(f"**{icon} {item.get('item_name', '不明')}** (提供: {item.get('publisher', '不明')})")
        st.caption(f"💡 提案理由: {item.get('reason', '')}")
elif not missing:
    st.success("✅ 現在の教材で全パートを十分にカバーできています！追加購入の必要はありません。")

st.divider()

# --- 5. 📚 教材の進捗 ---
st.subheader("📚 教材の進捗")

if books:
    for b_id, b_info in books.items():
        book_name = b_info.get("official_name", "名称不明")
        total_pages = b_info.get("total_pages", 100)
        
        current_comp = progress.get(b_id, {}).get("completed", 0)
        
        prog_ratio = min(current_comp / total_pages, 1.0)
        prog_percent = int(prog_ratio * 100)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{book_name}**")
            st.progress(prog_ratio)
        with col2:
            st.markdown(f"<h3 style='text-align: right; margin-top: 0px;'>{prog_percent}%</h3>", unsafe_allow_html=True)
            st.caption(f"<div style='text-align: right;'>{current_comp} / {total_pages} ページ</div>", unsafe_allow_html=True)
            
        st.write("---")
else:
    st.info("現在登録されている教材はありません。左のメニューの「教材登録と管理」から追加してください。")