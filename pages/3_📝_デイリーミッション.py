import streamlit as st
import datetime
import math
import time
# 💡 utils.py から共通の関数をインポート
from utils import load_data, save_data
from utils import check_password

# パスワードが通るまで、この先の画面描画や処理をストップさせる
if not check_password():
    st.stop()

st.set_page_config(page_title="デイリーミッション", page_icon="📝")

def auto_fill_pace(b_id, target_pace, current_done):
    if st.session_state[f"check_{b_id}"]:
        st.session_state[f"input_{b_id}"] = target_pace
    else:
        st.session_state[f"input_{b_id}"] = current_done

goals = load_data("data/goals.json")
books = load_data("data/textbooks.json")
strategy = load_data("data/strategy.json")
progress = load_data("data/progress.json")

if not goals or not strategy:
    st.warning("⚠️ 「🎯 目標設定」を完了させて、AI戦略を策定してください。")
    st.stop()

exam_date = datetime.datetime.strptime(goals.get("exam_date"), "%Y-%m-%d").date()
days_left = (exam_date - datetime.date.today()).days

today_str = datetime.date.today().strftime("%Y-%m-%d")
updated_progress = progress.copy()

if "_meta" not in updated_progress:
    updated_progress["_meta"] = {"last_updated": "", "start_date": today_str}
elif "start_date" not in updated_progress["_meta"]:
    updated_progress["_meta"]["start_date"] = today_str

start_date = datetime.datetime.strptime(updated_progress["_meta"]["start_date"], "%Y-%m-%d").date()
current_day = (datetime.date.today() - start_date).days + 1

for b_id in books.keys():
    if b_id not in updated_progress:
        updated_progress[b_id] = {"completed": 0, "today_done": 0, "last_date": today_str}
    else:
        if updated_progress[b_id].get("last_date") != today_str:
            updated_progress[b_id]["today_done"] = 0
            updated_progress[b_id]["last_date"] = today_str

if st.session_state.get("clear_inputs", False):
    for b_id in books.keys():
        st.session_state[f"input_{b_id}"] = updated_progress.get(b_id, {}).get("today_done", 0)
        if f"check_{b_id}" in st.session_state:
            st.session_state[f"check_{b_id}"] = False
    st.session_state.clear_inputs = False 
else:
    for b_id in books.keys():
        if f"input_{b_id}" not in st.session_state:
            st.session_state[f"input_{b_id}"] = updated_progress.get(b_id, {}).get("today_done", 0)

st.title("📝 デイリーミッション")
st.write(f"試験まであと **{days_left}** 日。（学習開始から **Day {current_day}**）")
st.divider()

strategies = strategy.get("material_strategies", [])
all_missions_completed = True
has_active_missions = False
mission_ui_elements = []

if strategies and books:
    for strat in strategies:
        strat_start = strat.get("start_day", 1)
        strat_end = strat.get("end_day", 999)
        
        if current_day < strat_start or current_day > strat_end:
            continue

        mat_name = strat.get("material", "教材不明")
        target_cycles = strat.get("target_cycles", 1)

        total_pages = 100
        book_id = None
        for b_id, b_info in books.items():
            db_name = b_info.get("official_name", "").replace(" ", "").replace("　", "")
            safe_mat_name = mat_name.replace(" ", "").replace("　", "")
            
            if db_name in safe_mat_name or safe_mat_name in db_name:
                total_pages = b_info.get("total_pages", 100)
                book_id = b_id
                break
        
        if not book_id:
            continue
            
        has_active_missions = True

        total_required_pages = total_pages * target_cycles
        current_comp = updated_progress[book_id].get("completed", 0)

        remaining_pages = max(0, total_required_pages - current_comp)
        remaining_days_in_phase = max(1, strat_end - current_day + 1)

        target_daily_pace = math.ceil(remaining_pages / remaining_days_in_phase)
        today_done = updated_progress[book_id].get("today_done", 0)
        remaining_today = target_daily_pace - today_done

        if remaining_today > 0:
            all_missions_completed = False
            mission_ui_elements.append({
                "type": "incomplete",
                "id": book_id,
                "name": mat_name,
                "remaining": remaining_today,
                "target_pace": target_daily_pace,
                "today_done": today_done,
                "info": f"（Day {strat_start}〜{strat_end}で{target_cycles}周ペース）"
            })
        else:
            mission_ui_elements.append({
                "type": "complete",
                "id": book_id,
                "name": mat_name,
                "pace": target_daily_pace,
                "today_done": today_done
            })

is_today_done = has_active_missions and all_missions_completed

st.subheader("🔥 今日のミッション")

if is_today_done:
    with st.container(border=True):
        st.success("🎉 **本日のミッションはすべて完了しています！**")
        st.write("今日もお疲れ様でした！追加で学習した場合は、下のフォームから記録を更新できます。")
        
        st.write("---")
        for elem in mission_ui_elements:
            st.markdown(f"📘 **{elem['name']}** ｜ ✅ **今日のノルマ（{elem['pace']}ページ）達成！**")
else:
    st.write("AIの戦略に基づき、現在のフェーズでやるべきタスクを表示しています。")
    if has_active_missions:
        for elem in mission_ui_elements:
            with st.container(border=True):
                if elem["type"] == "incomplete":
                    st.markdown(f"📘 **{elem['name']}** ｜ 💡 {elem['info']}")
                    st.checkbox(
                        f"✅ 🎯 今日はあと {elem['remaining']} ページ進める", 
                        key=f"check_{elem['id']}",
                        on_change=auto_fill_pace,
                        args=(elem['id'], elem['target_pace'], elem['today_done'])
                    )
                elif elem["type"] == "complete":
                    st.markdown(f"📘 **{elem['name']}** ｜ ✅ **今日のノルマ（{elem['pace']}ページ）達成！**")
    else:
        st.info("🎯 現在の期間（Day）に割り当てられたタスクはありません。次のフェーズに備えましょう！")

st.write("---")
st.subheader("📊 ミッション進捗の記録")
st.write("今日進めた「合計ページ数」を入力して保存します。")

with st.form("progress_update_form"):
    active_book_ids = [elem["id"] for elem in mission_ui_elements]
    
    if active_book_ids:
        for b_id in active_book_ids:
            book_name = books[b_id].get("official_name", "名称不明")
            total_pages = books[b_id].get("total_pages", 100)
            current_comp = updated_progress[b_id].get("completed", 0)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**{book_name}**")
                prog_ratio = min(current_comp / total_pages, 1.0)
                st.progress(prog_ratio)
                st.caption(f"<div style='text-align: right;'>累計進捗: {current_comp} / {total_pages} ページ</div>", unsafe_allow_html=True)
                
            with col2:
                st.number_input("今日の合計進捗（ページ）", min_value=0, key=f"input_{b_id}")
    else:
        st.write("現在報告できるタスクはありません。")
        
    submitted = st.form_submit_button("💾 記録を保存する", type="primary")

    if submitted and active_book_ids:
        for b_id in active_book_ids:
            new_today_val = st.session_state[f"input_{b_id}"]
            old_today_val = updated_progress[b_id].get("today_done", 0)
            difference = new_today_val - old_today_val
            
            updated_progress[b_id]["completed"] = max(0, updated_progress[b_id]["completed"] + difference)
            updated_progress[b_id]["today_done"] = new_today_val
            
        # 🌟 【新規追加】ストリーク（連続学習日数）の判定ロジック
        total_today_done = sum(updated_progress[b].get("today_done", 0) for b in active_book_ids)
        last_learned_str = updated_progress["_meta"].get("last_learned_date", "")
        current_streak = updated_progress["_meta"].get("streak_count", 0)
        
        # 今日、1ページでも進めていればストリーク判定へ
        if total_today_done > 0:
            if not last_learned_str:
                # 初めての記録！
                current_streak = 1
            elif last_learned_str != today_str:
                last_date = datetime.datetime.strptime(last_learned_str, "%Y-%m-%d").date()
                # 前回記録した日が「昨日」ならストリーク継続 (+1)
                if (datetime.date.today() - last_date).days == 1:
                    current_streak += 1
                # 2日以上空いていたら、残念ながらストリークは「1」にリセット
                else:
                    current_streak = 1
            
            # 最後に学習した日を「今日」に更新
            updated_progress["_meta"]["last_learned_date"] = today_str
            updated_progress["_meta"]["streak_count"] = current_streak

        save_data("data/progress.json", updated_progress)
        st.session_state.clear_inputs = True 
        st.balloons()
        time.sleep(1.5)
        st.rerun() 

st.divider()
if st.button("🏠 全体の進捗を確認しに行く"):
    st.switch_page("ダッシュボード.py")