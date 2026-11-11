"""
策略說明：今日漲幅>兩倍14日atr，且長紅棒還爆20日的1.5倍量。
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
# 請在此處貼上你的 Discord Webhook 網址
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 執行時間設定 (24小時制)
TARGET_HOUR = 12
TARGET_MINUTE = 30

# 清潔後的標的名單 (共 193 檔)
# 讀取後直接轉成 list
tickers = os.getenv("TICKERS", "").split(",")


# ==========================================
# 2. 核心功能函式
# ==========================================

def send_to_discord(match_list):
    """將符合條件的列表格式化後發送到 Discord"""
    if not match_list:
        return
    
    header = (
        "🔔 **今日能量慣性掃描報告** 🔔\n"
        "--------------------------------------\n"
        "```md\n"
        "【策略進場規則】\n"
        "1. 波動爆發：(H-L) > 2.0 * ATR(14)\n"
        "2. 實體質量：K棒實體 > 80% (無長上影)\n"
        "3. 量能背書：當日量 > 1.5 * 20日均量\n"
        "【明日出場機制】\n"
        "1. 成本守護：跌破「今日收盤(進場價)」立即出清\n"
        "2. 慣性守護：開盤即轉黑(低於開盤)立即撤退\n"
        "```\n"
    )
    
    
    items = []
    for res in match_list:
        item = (f"🚀 **{res['標的']}**\n"
                f"> 現價: `{res['現價']}` | 波幅: `{res['ATR倍數']}x` | 實體: `{res['實體%']}`\n"
                f"> **🛡️ 明日絕對防守位 (成本價): {res['現價']}**\n\n")
        items.append(item)

    for i in range(0, len(items), 5):
        chunk = items[i:i+5]
        content = header if i == 0 else "" 
        content += "".join(chunk)
        if i + 5 >= len(items):
            content += "\n⚠️ *提醒：爆發股不應回頭，跌破進場成本代表慣性消失。*"
            
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
            time.sleep(1) 
        except Exception as e:
            print(f"Discord 傳送失敗: {e}")

def run_scanner():
    """執行批量掃描邏輯並在終端機顯示完整過程"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 啟動掃描儀...")
    print(f"{'標的':<10} | {'判定':<4} | {'ATR倍數':<6} | {'實體%':<5} | {'量比':<5} | {'收盤價':<7}")
    print("-" * 60)
    
    chunk_size = 50 
    match_results = []

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        try:
            all_data = yf.download(chunk, period="60d", interval="1d", group_by='ticker', threads=True, progress=False)
            for symbol in chunk:
                try:
                    if symbol not in all_data.columns.get_level_values(0): continue
                    df = all_data[symbol].dropna()
                    if df.empty or len(df) < 21: continue
                    
                    h, l, c, o, v = df['High'], df['Low'], df['Close'], df['Open'], df['Volume']
                    tr = pd.concat([h-l, abs(h-c.shift(1)), abs(l-c.shift(1))], axis=1).max(axis=1)
                    atr = tr.rolling(14).mean().iloc[-1]
                    v_ma = v.rolling(20).mean().iloc[-1]
                    
                    t_h, t_l, t_c, t_o, t_v = float(h.iloc[-1]), float(l.iloc[-1]), float(c.iloc[-1]), float(o.iloc[-1]), float(v.iloc[-1])
                    p_c = float(c.iloc[-2])
                    
                    ratio_atr = (t_h - t_l) / atr if atr > 0 else 0
                    ratio_body = (abs(t_c - t_o) / (t_h - t_l)) if (t_h - t_l) > 0 else 0
                    ratio_vol = t_v / v_ma if v_ma > 0 else 0
                    
                    is_match = (ratio_atr > 2.0 and ratio_body > 0.8 and ratio_vol > 1.5 and t_c > p_c)
                    
                    # 終端機即時反饋
                    status_icon = "✅" if is_match else "❌"
                    print(f"{symbol:<10} | {status_icon:<4} | {ratio_atr:>6.2f}x | {ratio_body*100:>4.0f}% | {ratio_vol:>5.2f}x | {t_c:>7.2f}")

                    if is_match:
                        match_results.append({
                            "標的": symbol,
                            "現價": f"{t_c:.2f}",
                            "ATR倍數": f"{ratio_atr:.2f}",
                            "實體%": f"{ratio_body*100:.0f}%",
                            "量比": f"{ratio_vol:.2f}x"
                        })
                except: continue
            time.sleep(1) 
        except: continue

    print("-" * 60)
    if match_results:
        print(f"掃描完成！找到 {len(match_results)} 檔符合標的。正在推送 Discord...")
        send_to_discord(match_results)
    else:
        print("掃描完成，今日無符合標的。")
        content = (
            f"🔔 **今日能量慣性掃描報告** 🔔\n"
            f"--------------------------------------\n"
            f"【策略進場規則】\n"
            f"1. 波動爆發：(H-L) > 2.0 * ATR(14)\n"
            f"2. 實體質量：K棒實體 > 80% (無長上影)\n"
            f"3. 量能背書：當日量 > 1.5 * 20日均量\n"
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