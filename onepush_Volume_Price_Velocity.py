"""
策略說明：
    "1. 黃金交叉：量線超車價線 > 蓄勢待發，準備進場
    "2. 同步飆升：雙線向上 > 真強勢，持股續抱
    "3. 價量背離：價漲量縮 > 動能耗盡，分批停利
    "4. 死亡交叉：量線墜落 > 買盤枯竭，反轉先兆
    --------------------------------------
    "1. 今天的V-Line要大於今天的P-Line
    "2. 昨天的V-Line要小於昨天的P-Line
    "3. 今日收紅K
    "4. 今日漲幅小於3趴
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
TARGET_MINUTE = 40

# 提醒：TICKERS 需包含 .TW 或 .TWO，例如 "2330.TW,2454.TW"
tickers_str = os.getenv("TICKERS", "")
tickers = [t.strip() for t in tickers_str.split(",")] if tickers_str else []

# ==========================================
# 2. 核心功能函式
# ==========================================

def send_to_discord(match_list):
    """將符合黃金交叉的標的推送到 Discord"""
    if not match_list:
        return
    
    # 策略圖解說明（放在報告最上方）
    header = (
        "🎯 **量價速率：【超車紅K】狙擊訊號** 🎯\n"
        "--------------------------------------\n"
        "```md\n"
        "【量價狀態定義】\n"
        "1. 黃金交叉：量線超車價線 > 蓄勢待發，準備進場\n"
        "2. 同步飆升：雙線向上 > 真強勢，持股續抱\n"
        "3. 價量背離：價漲量縮 > 動能耗盡，分批停利\n"
        "4. 死亡交叉：量線墜落 > 買盤枯竭，反轉先兆\n"
        "【進場條件】\n"
        "1. 今天的V-Line要大於今天的P-Line\n"
        "2. 昨天的V-Line要小於昨天的P-Line\n"
        "3. 今日收紅K\n"
        "4. 今日漲幅小於3趴\n"
        "```\n"
    )
    
    items = []
    for res in match_list:
        item = (f"🔥 **{res['標的']}** (動能超車 + 紅K)\n"
                f"> P-Line: `{res['P_Line']}` | V-Line: `{res['V_Line']}`\n"
                f"> 現價: `{res['現價']}` | 漲幅: `{res['漲幅']}`\n"
                f"```md\n"
                f"【鋼鐵防守規則】\n"
                f"1. 成本守護：跌破 {res['現價']} (進場價) 立即出清\n"
                f"2. 慣性守護：明日開盤轉黑 立即撤退\n"
                f"```\n")
        items.append(item)

    # 每 5 檔股票切分一則訊息，避免 Discord 字數限制
    for i in range(0, len(items), 5):
        chunk = items[i:i+5]
        content = (header if i == 0 else "") + "".join(chunk)
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
            time.sleep(1)
        except Exception as e:
            print(f"Discord 傳送失敗: {e}")

def run_scanner():
    """執行全狀態監控掃描"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 啟動量價速率全狀態掃描...")
    print(f"{'標的':<10} | {'P-Line':<8} | {'V-Line':<8} | {'K棒':<4} | {'狀態狀況'}")
    print("-" * 75)
    
    match_results = []
    chunk_size = 50 

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i : i + chunk_size]
        try:
            # 抓取最近 5 天數據以計算變動率
            all_data = yf.download(chunk, period="5d", interval="1d", group_by='ticker', threads=True, progress=False)
            
            for symbol in chunk:
                try:
                    # 處理單一標的或多標的的 Dataframe 格式
                    df = all_data[symbol].dropna() if len(chunk) > 1 else all_data.dropna()
                    if len(df) < 3: continue
                    
                    # --- 1天 PV 線速率計算 (當日 vs 昨日) ---
                    p_today = (df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1
                    p_yesterday = (df['Close'].iloc[-2] / df['Close'].iloc[-3]) - 1
                    v_today = (df['Volume'].iloc[-1] / df['Volume'].iloc[-2]) - 1
                    v_yesterday = (df['Volume'].iloc[-2] / df['Volume'].iloc[-3]) - 1
                    
                    # 判斷是否為紅K
                    is_red_k = df['Close'].iloc[-1] > df['Open'].iloc[-1]
                    status = "---"
                    
                    # --- 狀態判定邏輯 ---
                    
                    # 1. 黃金交叉 (量超車價)：今天 V > P，且昨天 V <= P
                    if (v_today > p_today) and (v_yesterday <= p_yesterday):
                        if is_red_k and 0 <= p_today <= 0.03:
                            status = "🎯 MATCH"
                            match_results.append({
                                "標的": symbol,
                                "P_Line": f"{p_today:+.2%}",
                                "V_Line": f"{v_today:+.2%}",
                                "現價": f"{df['Close'].iloc[-1]:.2f}",
                                "漲幅": f"{p_today:+.2%}"
                            })
                        else:
                            status = "✨ 超車(不符)"

                    # 2. 死亡交叉 (量線墜落快過價線)：今天 V < P，且昨天 V >= P
                    elif (v_today < p_today) and (v_yesterday >= p_yesterday):
                        status = "💀 死亡交叉"
                    
                    # 3. 價量背離 (價漲但量縮顯著)
                    elif p_today > 0 and v_today < -0.3:
                        status = "⚠️ 價量背離"
                    
                    # 4. 同步飆升 (強勢攻擊)
                    elif p_today > 0.03 and v_today > 0.5:
                        status = "🚀 同步飆升"

                    k_str = "紅" if is_red_k else "黑"
                    print(f"{symbol:<10} | {p_today:>8.2%} | {v_today:>8.2%} | {k_str:<4} | {status}")
                    
                except Exception as e:
                    continue
        except Exception as e:
            print(f"下載批次發生錯誤: {e}")
            continue

    if match_results:
        print(f"\n找到 {len(match_results)} 檔符合標的，正在推送到 Discord...")
        send_to_discord(match_results)
    else:
        print("掃描完成，今日無量能異常標的。")
        content = (
            f"🎯 **量價速率：【超車紅K】狙擊訊號** 🎯\n"
            f"--------------------------------------\n"
            f"【量價狀態定義】\n"
            f"1. 黃金交叉：量線超車價線 > 蓄勢待發，準備進場\n"
            f"2. 同步飆升：雙線向上 > 真強勢，持股續抱\n"
            f"3. 價量背離：價漲量縮 > 動能耗盡，分批停利\n"
            f"4. 死亡交叉：量線墜落 > 買盤枯竭，反轉先兆\n"
            f"【進場條件】\n"
            f"1. 今天的V-Line要大於今天的P-Line\n"
            f"2. 昨天的V-Line要小於昨天的P-Line\n"
            f"3. 今日收紅K\n"
            f"4. 今日漲幅小於3趴\n"
            f"--------------------------------------\n"
            f"掃描完成，今日無符合標的。"
        )         
       
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
        except Exception as e:
            print(f"空值報告傳送失敗: {e}")

# run_scanner()