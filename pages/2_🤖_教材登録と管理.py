import streamlit as st
import json
import os
import uuid
import time
import google.generativeai as genai
#from dotenv import load_dotenv
# 💡 utils.py から共通の関数をインポート
from utils import load_data, save_data, generate_ai_strategy
from utils import check_password

# パスワードが通るまで、この先の画面描画や処理をストップさせる
if not check_password():
    st.stop()

# --- 初期設定 ---
st.set_page_config(page_title="教材管理", layout="wide", page_icon="📚")
st.title("📚 教材の登録と管理")

#load_dotenv()
#api_key = os.environ.get("GEMINI_API_KEY")
api_key = st.secrets["GEMINI_API_KEY"]

if not api_key:
    st.error("⚠️ .envファイルに GEMINI_API_KEY が設定されていません。")
    st.stop()

genai.configure(api_key=api_key)

# 💡 load_data, save_data は utils.py のものを使うため、ここでの関数定義は削除

books_data = load_data("data/textbooks.json")

def generate_book_id():
    return f"book_{uuid.uuid4().hex[:8]}"

# 💡 recalculate_strategy 関数も丸ごと削除（utils.py の generate_ai_strategy に一本化したため）

def analyze_book_with_gemini(name, memo):
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    あなたはTOEIC教材の専門家です。以下の「教材名」と「メモ」から、この教材が対策するパートと到達レベルを推論してください。
    教材名: {name}
    メモ: {memo}
    
    【重要な制約】
    "categories" には、必ず以下の7つのリストの中から該当するものを「一言一句違わず」選んで配列にしてください。独自の表記（例：Part 1,2など）は絶対に禁止です。
    ["🎧 Part 1 (写真描写)", "🎧 Part 2 (応答)", "🎧 Part 3 (会話)", "🎧 Part 4 (説明文)", "📖 Part 5 (短文穴埋め)", "📖 Part 6 (長文穴埋め)", "📖 Part 7 (読解)"]
    
    【出力JSONフォーマット】
    {{
      "categories": ["🎧 Part 1 (写真描写)"],
      "total_pages": 300,
      "target_level": 700,
      "reason": "推論の理由"
    }}
    """
    try:
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# 🔔 画面上部での「確実な」フィードバック表示
# ==========================================
if st.session_state.get("add_success_name"):
    st.success(f"🎉 新しい教材「{st.session_state.add_success_name}」の登録が完了しました！")
    st.balloons()
    st.session_state.add_success_name = None

if st.session_state.get("edit_success"):
    st.success("✅ 登録済み教材の編集・削除を保存しました。")
    st.session_state.edit_success = False

if st.session_state.get("needs_recalc", False):
    st.warning("⚠️ 教材データが更新されました。デイリーミッションに反映させるため、最新のリストに合わせてAI戦略を再計算してください。")
    if st.button("🔄 AI戦略を再計算して反映する", type="primary", use_container_width=True):
        with st.spinner("AIが新しい教材構成で戦略を練り直しています..."):
            # 💡 ここで utils.py の共通関数を呼び出す！
            res = generate_ai_strategy() 
            if "error" in res:
                st.error(res["error"])
            else:
                st.session_state.needs_recalc = False
                st.success("✨ 戦略の再計算が完了しました！デイリーミッションが最新状態に更新されました。")
                time.sleep(1.5)
                st.rerun()

st.write("---")

# ==========================================
# 📑 画面UI（タブ）
# ==========================================
tab1, tab2 = st.tabs(["➕ 新規教材の登録", "⚙️ 登録済み教材の管理・編集"])

# ------------------------------------
# タブ1：新規登録
# ------------------------------------
with tab1:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. 教材情報の入力")
        book_name = st.text_input("教材の名称（必須）", placeholder="例：公式TOEIC Listening & Reading 問題集 10")
        book_memo = st.text_area("メモ（任意・AIのヒントになります）", placeholder="例：初心者向けの単語帳。まずはここからやる。")
        
        if "ai_result" not in st.session_state:
            st.session_state.ai_result = {"categories": [], "total_pages":10, "target_level":10, "reason": ""}

        if st.button("✨ AIでカテゴリーとレベルを自動判定"):
            if book_name:
                with st.spinner("Geminiが教材を分析中..."):
                    result = analyze_book_with_gemini(book_name, book_memo)
                    if "error" in result:
                        st.error(f"判定に失敗しました: {result['error']}")
                    else:
                        st.session_state.ai_result = result
                        st.toast("AIによる判定が完了しました！", icon="💡")
            else:
                st.warning("教材の名称を入力してください。")

    with col2:
        st.subheader("2. 判定結果の確認・登録")
        if st.session_state.ai_result.get("reason"):
            st.info(f"💡 **AIの推論理由:**\n{st.session_state.ai_result['reason']}")
        
        options = ["🎧 Part 1 (写真描写)", "🎧 Part 2 (応答)", "🎧 Part 3 (会話)", "🎧 Part 4 (説明文)", "📖 Part 5 (短文穴埋め)", "📖 Part 6 (長文穴埋め)", "📖 Part 7 (読解)"]
        ai_categories_str = " ".join(st.session_state.ai_result.get("categories", []))
        matched_defaults = []
        for opt in options:
            part_number_str = opt.split(" ")[1] + " " + opt.split(" ")[2]
            if part_number_str in ai_categories_str or part_number_str.replace(" ", "") in ai_categories_str.replace(" ", ""):
                matched_defaults.append(opt)

        categories = st.multiselect("ターゲットとするパート", options, default=matched_defaults)
        total_pages = st.number_input("総ページ数（またはレッスン数）", min_value=1, value=int(st.session_state.ai_result.get("total_pages", 100)), step=1)
        target_level = st.number_input("到達レベル（目安）", min_value=10, max_value=990, value=int(st.session_state.ai_result["target_level"]), step=10)

        st.divider()
        if st.button("💾 この内容で教材を追加する", type="primary"):
            if book_name and categories:
                with st.spinner("教材データを保存中..."):
                    new_id = generate_book_id()
                    books_data[new_id] = {
                        "official_name": book_name,
                        "カテゴリー": categories,
                        "total_pages": total_pages,
                        "target_level": target_level
                    }
                    save_data("data/textbooks.json", books_data)
                    st.session_state.needs_recalc = True
                    time.sleep(0.5)
                
                st.session_state.add_success_name = book_name
                st.rerun()
            else:
                st.error("⚠️ 名称とカテゴリーを設定してください。")

# ------------------------------------
# タブ2：管理・編集・削除
# ------------------------------------
with tab2:
    st.subheader("⚙️ 登録済みデータの一括編集・削除")
    st.write("表の数値を直接編集できます。削除したい場合は左端の「🗑️ 削除」にチェックを入れて保存してください。")
    
    if not books_data:
        st.info("現在登録されている教材はありません。")
    else:
        book_list = []
        for b_id, b_info in books_data.items():
            book_list.append({
                "_id": b_id,
                "🗑️ 削除": False,
                "教材名": b_info.get("official_name", ""),
                "総ページ数": b_info.get("total_pages", 100),
                "対象レベル": b_info.get("target_level", 500)
            })
            
        edited_list = st.data_editor(
            book_list,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "_id": None,
                "🗑️ 削除": st.column_config.CheckboxColumn("削除", default=False),
                "教材名": st.column_config.TextColumn("教材の正式名称", required=True),
                "総ページ数": st.column_config.NumberColumn("総ページ数", min_value=1, step=1, required=True),
                "対象レベル": st.column_config.NumberColumn("対象レベル", min_value=10, max_value=990, step=10)
            }
        )

        if st.button("💾 編集・削除の結果を保存する", type="primary"):
            with st.spinner("データを更新しています..."):
                new_books_data = {}
                for row in edited_list:
                    if row.get("🗑️ 削除", False):
                        continue
                        
                    b_id = row.get("_id")
                    if not b_id:
                         b_id = generate_book_id()
                         
                    old_categories = books_data.get(b_id, {}).get("カテゴリー", [])
                    
                    new_books_data[b_id] = {
                        "official_name": row["教材名"],
                        "total_pages": row["総ページ数"],
                        "target_level": row["対象レベル"],
                        "カテゴリー": old_categories
                    }
                
                save_data("data/textbooks.json", new_books_data)
                st.session_state.needs_recalc = True
                time.sleep(0.5)
            
                st.session_state.edit_success = True
                st.rerun()