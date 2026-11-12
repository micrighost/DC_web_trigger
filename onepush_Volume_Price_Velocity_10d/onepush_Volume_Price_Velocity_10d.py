"""
策略說明：
    今10日均 V-Line > 今10日均P-Line 且昨日未超車，且P-Line > 0% (均價上揚)，
    但P-Line <= 1.5%拒絕追高。
"""
import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime
import os

# ==========================================
# 1. 設定區
# ==========================================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TARGET_HOUR = 12
TARGET_MINUTE = 45

pd.set_option('display.float_format', lambda x: '%.2f' % x)

tickers_str = os.getenv("TICKERS", "")
tickers = [t.strip() for t in tickers_str.split(",")] if tickers_str else []

# ==========================================
# 2. 核心功能函式
# ==========================================

def send_to_discord(match_list):
    if not match_list: return
    # 修正：確保文字都在引號內，並使用簡潔的描述
    header = (
        "📊 **量價速率：【10日結構版】報告** 📊\n"
        "--------------------------------------\n"
        "```md\n"
        "【進場條件】\n"
        "1. 首度超車：今10日均 V-Line > 今10日均P-Line 且昨日未超車\n"
        "2. 趨勢向上：P-Line > 0% (均價上揚)\n"
        "3. 拒絕追高：P-Line <= 1.5% (蓄勢區)\n"
        "```\n"
    )
    items = []
    for res in match_list:
        item = (f"🏛️ **{res['標的']}** (10D 結構超車)\n"
                f"> 10D P-Line: `{res['10D_P']}` | 10D V-Line: `{res['10D_V']}`\n"
                f"> 現價: `{res['現價']}` | 今日漲幅: `{res['今日漲幅']}`\n"
                f"```md\n"
                f"【鋼鐵防守規則】\n"
                f"1. 成本守護：跌破 {res['現價']} (進場價) 立即出清\n"
                f"2. 慣性守護：明日開盤轉黑 立即撤退\n"
                f"```\n")
        items.append(item)

    for i in range(0, len(items), 5):
        chunk = items[i:i+5]
        content = (header if i == 0 else "") + "".join(chunk)
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
            time.sleep(1)
        except Exception as e:
            print(f"Discord 傳送失敗: {e}")

def run_scanner():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 啟動 10D 結構速率掃描...")
    
    match_results = []
    summary_list = [] 
    chunk_size = 50 

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        try:
            all_data = yf.download(chunk, period="30d", interval="1d", group_by='ticker', threads=True, progress=False)
            
            for symbol in chunk:
                try:
                    df = all_data[symbol].dropna() if len(chunk) > 1 else all_data.dropna()
                    if len(df) < 15: continue
                    
                    ma_p = df['Close'].rolling(10).mean()
                    ma_v = df['Volume'].rolling(10).mean()
                    
                    # 診斷細節
                    print(f"\n[{symbol}] 10D 平均價格序列 (最近3日):")
                    print(ma_p.tail(3).map('{:,.2f}'.format)) 
                    print(f"[{symbol}] 10D 平均成交量序列 (最近3日):")
                    print(ma_v.tail(3).map('{:,.2f}'.format)) 

                    p_10d_today = (ma_p.iloc[-1] / ma_p.iloc[-2]) - 1
                    p_10d_yest = (ma_p.iloc[-2] / ma_p.iloc[-3]) - 1
                    v_10d_today = (ma_v.iloc[-1] / ma_v.iloc[-2]) - 1
                    v_10d_yest = (ma_v.iloc[-2] / ma_v.iloc[-3]) - 1
                    
                    is_red_k = df['Close'].iloc[-1] > df['Open'].iloc[-1]
                    is_10d_overtake = (v_10d_today > p_10d_today) and (v_10d_yest <= p_10d_yest)
                    
                    status_text = "---"
                    判定 = "❌"
                    if is_10d_overtake:
                        if is_red_k and 0 <= p_10d_today <= 0.015: 
                            status_text = "🎯 MATCH"
                            判定 = "✅"
                            match_results.append({
                                "標的": symbol,
                                "10D_P": f"{p_10d_today:+.4%}",
                                "10D_V": f"{v_10d_today:+.4%}",
                                "現價": f"{df['Close'].iloc[-1]:.2f}",
                                "今日漲幅": f"{(df['Close'].iloc[-1]/df['Close'].iloc[-2]-1):+.2%}"
                            })
                        else:
                            status_text = "✨ 超車"
                    
                    k_str = "紅K" if is_red_k else "非紅"
                    summary_list.append({
                        "標的": symbol, "判定": 判定, "P_Line": f"{p_10d_today:+.2%}",
                        "V_Line": f"{v_10d_today:+.2%}", "K棒": k_str,
                        "現價": f"{df['Close'].iloc[-1]:.2f}", "狀態": status_text
                    })
                    
                except Exception: continue
        except Exception: continue

    # === 最後印出總結表 ===
    print("\n" + "="*80)
    print(f" 🚀 掃描總表匯總 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("-" * 80)
    print(f"{'標的':<10} | {'判定':<4} | {'P-Line':>8} | {'V-Line':>8} | {'K棒':<5} | {'現價':>8} | {'狀態'}")
    print("-" * 80)
    for row in summary_list:
        print(f"{row['標的']:<10} | {row['判定']:<4} | {row['P_Line']:>8} | {row['V_Line']:>8} | {row['K棒']:<5} | {row['現價']:>8} | {row['狀態']}")
    
    print("-" * 80)
    print(f"📊 掃描完成：共計 {len(summary_list)} 檔 | 命中 {len(match_results)} 檔")
    print("="*80 + "\n")

    if match_results:
        send_to_discord(match_results)
    else:
        print("掃描完成，今日無量能異常標的。")
        content = (
            f"📊 **量價速率：【10日結構版】報告** 📊\n"
            f"--------------------------------------\n"
            f"【進場條件】\n"
            f"1. 首度超車：今10日均 V-Line > 今10日均P-Line 且昨日未超車\n"
            f"2. 趨勢向上：P-Line > 0% (均價上揚)\n"
            f"3. 拒絕追高：P-Line <= 1.5% (蓄勢區)\n"
            f"--------------------------------------\n"
            f"掃描完成，今日無符合標的。"
        )         
                
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
        except Exception as e:
            print(f"空值報告傳送失敗: {e}")


# run_scanner()