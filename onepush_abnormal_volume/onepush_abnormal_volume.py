"""
策略說明：當日交易量大於昨天兩倍，且收紅。
"""
import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime
import os

# ==========================================
# 1. 基本設定區
# ==========================================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TARGET_HOUR = 12
TARGET_MINUTE = 35
# 提醒：代號若為台股，請確保 TICKERS 來源包含 .TW 或 .TWO
tickers = os.getenv("TICKERS", "").split(",")

# ==========================================
# 2. 核心功能函式
# ==========================================

def send_to_discord(match_list):
    """將符合條件的列表格式化後發送到 Discord"""
    if not match_list:
        return
    
    header = (
        "🔔 **今日能量不平衡掃描報告** 🔔\n"
        "--------------------------------------\n"
        "```md\n"
        "【策略進場規則】\n"
        "1. 量能異常：當日量 > 2 * 昨日量\n"
        "2. K棒方向：收紅 K (Close > Open)\n"
        "\n"
        "【明日出場機制】\n"
        "1. 成本守護：跌破「今日收盤(進場價)」立即出清\n"
        "2. 慣性守護：開盤即轉黑(低於開盤)立即撤退\n"
        "```\n"
    )
    
    items = []
    for res in match_list:
        item = (f"🚀 **{res['標的']}**\n"
                f"> 現價: `{res['現價']}` | 量比: `{res['量增倍數']}x` | 漲幅: `{res['漲幅']}`\n"
                f"> **🛡️ 明日絕對防守位 (成本價): {res['現價']}**\n\n")
        items.append(item)

    for i in range(0, len(items), 5):
        chunk = items[i:i+5]
        content = header if i == 0 else "" 
        content += "".join(chunk)
        if i + 5 >= len(items):
            content += "\n⚠️ *提醒：量能異常代表動能爆發，若跌破今日收盤代表此量能為無效攻擊。*"
            
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
            time.sleep(1) 
        except Exception as e:
            print(f"Discord 傳送失敗: {e}")

def run_scanner():
    """執行量能不平衡掃描邏輯"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 啟動能量不平衡掃描...")
    print(f"{'標的':<10} | {'判定':<4} | {'量增倍數':<6} | {'K棒':<5} | {'現價':<7}")
    print("-" * 60)
    
    chunk_size = 50 
    match_results = []

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        try:
            all_data = yf.download(chunk, period="10d", interval="1d", group_by='ticker', threads=True, progress=False)
            for symbol in chunk:
                try:
                    if symbol not in all_data.columns.get_level_values(0): continue
                    df = all_data[symbol].dropna()
                    if len(df) < 2: continue
                    
                    # 取得今日與昨日數據
                    t_o, t_h, t_l, t_c, t_v = float(df['Open'].iloc[-1]), float(df['High'].iloc[-1]), float(df['Low'].iloc[-1]), float(df['Close'].iloc[-1]), float(df['Volume'].iloc[-1])
                    p_c, p_v = float(df['Close'].iloc[-2]), float(df['Volume'].iloc[-2])
                    
                    # 邏輯計算
                    vol_ratio = t_v / p_v if p_v > 0 else 0
                    is_red_k = t_c > t_o  # 收紅K
                    pct_change = (t_c - p_c) / p_c * 100
                    
                    # 篩選條件：1. 量能 > 2倍昨日量 2. 收紅K 
                    is_match = (vol_ratio > 2.0 and is_red_k)
                    
                    status_icon = "✅" if is_match else "❌"
                    k_status = "紅K" if is_red_k else "非紅"
                    print(f"{symbol:<10} | {status_icon:<4} | {vol_ratio:>7.2f}x | {k_status:<5} | {t_c:>7.2f}")

                    if is_match:
                        match_results.append({
                            "標的": symbol,
                            "現價": f"{t_c:.2f}",
                            "量增倍數": f"{vol_ratio:.2f}",
                            "漲幅": f"{pct_change:+.2f}%"
                        })
                except: continue
            time.sleep(1) 
        except: continue

    print("-" * 60)
    if match_results:
        print(f"掃描完成！找到 {len(match_results)} 檔符合標的。正在推送 Discord...")
        send_to_discord(match_results)
    else:
        print("掃描完成，今日無量能異常標的。")
        content = (
            f"🔔 **今日能量不平衡掃描報告** 🔔\n"
            f"--------------------------------------\n"
            f"【策略進場規則】\n"
            f"1. 量能異常：當日量 > 2 * 昨日量\n"
            f"2. K棒方向：收紅 K (Close > Open)\n"
            f"【明日出場機制】\n"
            f"1. 成本守護：跌破「今日收盤(進場價)」立即出清\n"
            f"2. 慣性守護：開盤即轉黑(低於開盤)立即撤退\n"
            f"--------------------------------------\n"
            f"掃描完成，今日無符合標的。"
        )         
                
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
        except Exception as e:
            print(f"空值報告傳送失敗: {e}")


# run_scanner()