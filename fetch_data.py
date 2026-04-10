import yfinance as yf
import pandas as pd
import json
import time
import os
from google import genai

# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("警告：找不到 GEMINI_API_KEY 環境變數！")
# ==========================================

def fetch_and_calculate_data():
    print("正在抓取金融資料...")
    mstr = yf.download("MSTR", period="1y")['Close']
    btc = yf.download("BTC-USD", period="1y")['Close']

    df = pd.DataFrame({
        'MSTR_Price': mstr.squeeze(),
        'BTC_Price': btc.squeeze()
    }).dropna()

    # 使用 2026 年最新數據計算
    MSTR_BTC_HOLDINGS = 766970 
    MSTR_SHARES_OUTSTANDING = 379425000 

    df['NAV_per_share'] = (MSTR_BTC_HOLDINGS * df['BTC_Price']) / MSTR_SHARES_OUTSTANDING
    df['Premium_Percent'] = ((df['MSTR_Price'] - df['NAV_per_share']) / df['NAV_per_share']) * 100

    df.index = df.index.astype(str)
    df = df.round(2)
    df_reset = df.reset_index()
    df_reset.rename(columns={'Date': 'date'}, inplace=True)
    
    # 輸出資料給圖表使用
    records = df_reset.to_dict(orient='records')
    with open('mstr_data.json', 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False)
        
    print("圖表資料已更新至 mstr_data.json")

    # ==========================================
    # 以下為新增的 AI 分析區塊
    # ==========================================
    print("正在請求 Gemini AI 產生分析報告...")
    
    # 取出最後一天的資料來讓 AI 分析
    latest_date = df_reset.iloc[-1]['date'].split(' ')[0]
    latest_mstr = df_reset.iloc[-1]['MSTR_Price']
    latest_btc = df_reset.iloc[-1]['BTC_Price']
    latest_nav = df_reset.iloc[-1]['NAV_per_share']
    latest_premium = df_reset.iloc[-1]['Premium_Percent']

    # 設定 AI 的 Prompt (提示詞)
    prompt = f"""
    你是一位專業的加密貨幣與傳統金融分析師。
    我正在製作一個追蹤 MicroStrategy (MSTR) 溢價的儀表板。
    以下是截至 {latest_date} 的最新數據：
    - 比特幣價格：{latest_btc} USD
    - MSTR 股價：{latest_mstr} USD
    - MSTR 每股淨值 (NAV)：{latest_nav} USD
    - 溢價比例：{latest_premium}%

    請根據上述數據，寫一段大約 150 字以內的分析摘要，給投資人參考。
    請注意：如果溢價比例小於 0，代表目前處於「折價」狀態；大於 0 則是「溢價」。
    請直接給出分析結論，不要講多餘的問候語。使用繁體中文。
    """

    try:
        # 使用新版 google-genai SDK 呼叫 Gemini 模型
        client = genai.Client(api_key=GEMINI_API_KEY)
        candidate_models = ['gemini-3-flash-preview', 'gemini-2.5-flash']
        response = None
        last_error = None

        # 先嘗試主要模型，遇到暫時性失敗時短暫重試，並可回退到次要模型。
        for model_name in candidate_models:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    break
                except Exception as model_error:
                    last_error = model_error
                    if attempt == 0:
                        time.sleep(2)
            if response is not None:
                break

        if response is None:
            raise last_error

        summary_text = response.text if getattr(response, 'text', None) else 'AI 未回傳可用文字內容。'
        
        # 將 AI 的回答存成文字檔
        with open('ai_summary.txt', 'w', encoding='utf-8') as f:
            f.write(summary_text)
        print("AI 分析報告已成功儲存至 ai_summary.txt！")

    except Exception as e:
        print(f"呼叫 AI 發生錯誤：{e}")

if __name__ == "__main__":
    fetch_and_calculate_data()