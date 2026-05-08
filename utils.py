# utils.py
import json
import os
import datetime
import google.generativeai as genai
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- スプレッドシート連携の設定 ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_resource
def get_gspread_client():
    """GCPの認証を行い、クライアントを取得する"""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_worksheet(sheet_name):
    """指定した名前のタブ（ワークシート）を取得。なければ新規作成する"""
    client = get_gspread_client()
    sheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])
    try:
        return sheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # タブが存在しなければ新しく作成して返す
        return sheet.add_worksheet(title=sheet_name, rows="100", cols="20")

# ==========================================
# 💡 クラウド版：データの読み書き関数
# ==========================================
def load_data(file_path):
    """スプレッドシートのタブのA1セルからJSONデータを読み込む"""
    # 例: "data/goals.json" から "goals" というタブ名を抽出
    sheet_name = os.path.basename(file_path).replace('.json', '')
    
    try:
        worksheet = get_worksheet(sheet_name)
        data_str = worksheet.acell('A1').value
        if data_str:
            return json.loads(data_str)
        return {}
    except Exception as e:
        st.error(f"データ読み込みエラー ({sheet_name}): {e}")
        return {}

def save_data(file_path, data):
    """スプレッドシートのタブのA1セルにJSONデータを保存する"""
    sheet_name = os.path.basename(file_path).replace('.json', '')
    try:
        worksheet = get_worksheet(sheet_name)
        data_str = json.dumps(data, ensure_ascii=False, indent=4)
        worksheet.update_acell('A1', data_str)
    except Exception as e:
        st.error(f"データ保存エラー ({sheet_name}): {e}")
        
def generate_ai_strategy():
    """目標と教材データから、AI戦略を生成して strategy.json に保存する共通関数"""
    goals = load_data("data/goals.json")
    books = load_data("data/textbooks.json")
    
    if not goals:
        return {"error": "目標データがありません。先に「🎯 目標設定」を行ってください。"}
        
    try:
        current_score = goals.get("current_score", 400)
        target_score = goals.get("target_score", 600)
        weekly_hours = goals.get("weekly_hours", 7)
        exam_date = datetime.datetime.strptime(goals.get("exam_date", "2025-01-01"), "%Y-%m-%d").date()
        days_left = (exam_date - datetime.date.today()).days
        if days_left <= 0: days_left = 1
        
        book_info = "\n".join([f"・{b['official_name']} (総ページ数: {b.get('total_pages', 100)})" for b in books.values()])
        
        # 💡 ここに最新の（開始日・終了日・出版社対応の）プロンプトを一本化！
        prompt = f"""
        あなたはTOEICの戦略コンサルタントです。以下のデータに基づき、学習戦略を策定してください。
        
        【ユーザーデータ】
        - 現在のスコア: {current_score}点
        - 目標スコア: {target_score}点
        - 試験までの日数: {days_left}日
        - 1日の平均学習可能時間: {round(weekly_hours / 7, 1)}時間
        - 現在持っている教材:
        {book_info if book_info else "未登録"}
        
        【出力制約】
        - schedule_timeline: 期間をフェーズに分けた具体的な工程表。必ず "start_day" と "end_day" の数値を持たせてください。
        - material_strategies: 手持ちの各教材の学習戦略。必ず紐づくフェーズに合わせて "start_day" (開始日) と "end_day" (終了日) を数値で持たせてください。allocated_daysは (end_day - start_day + 1) と一致させてください。
        - recommended_items: 不足パートを補うための具体的な市販教材やアプリ。
        - predicted_score: 予想スコア。

       【JSON出力フォーマット例】
        {{
          "schedule_timeline": [
            {{"period": "フェーズ1: 基礎固め", "start_day": 1, "end_day": 90, "focus": "文法", "description": "..."}}
          ],
          "material_strategies": [
            {{"material": "金のリスニング", "target_cycles": 3, "start_day": 91, "end_day": 180, "allocated_days": 90, "purpose": "..."}}
          ],
          "missing_parts": ["Part 5", "Part 7"],
          "recommended_items": [
            {{
              "item_name": "TOEIC L&R TEST 出る単特急 金のフレーズ", 
              "publisher": "朝日新聞出版", 
              "type": "book", 
              "reason": "語彙力強化に不可欠"
            }},
            {{
              "item_name": "TOEIC公式ボキャブラリー", 
              "publisher": "IIBC", 
              "type": "app", 
              "reason": "隙間時間の学習に最適"
            }}
          ],
          "predicted_score": 650,
          "strategy_advice": "アドバイスのテキスト..."
        }}
        """
        
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        strategy_data = json.loads(response.text)
        save_data("data/strategy.json", strategy_data)
        return {"success": True}
        
    except Exception as e:
        return {"error": f"APIエラーが発生しました: {str(e)}"}
   

def check_password():
    """シンプルなパスワード認証を行う関数"""
    def password_entered():
        # 入力されたパスワードと、secrets.tomlのパスワードを照合
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セキュリティのため入力値を削除
        else:
            st.session_state["password_correct"] = False

    # 既に認証済みならTrueを返す
    if st.session_state.get("password_correct"):
        return True

    # 未認証の場合は入力フォームを表示
    st.title("🔒 アプリのロック解除")
    st.write("ご家族専用のパスワードを入力してください。")
    st.text_input(
        "パスワード", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    # 間違えた場合のエラー表示
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 パスワードが間違っています。")
        
    return False
