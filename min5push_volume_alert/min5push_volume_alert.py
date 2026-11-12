"""
策略說明：一次性批次下載所有股票的原生 5分鐘K線（5m）資料（保護 IP，防止被鎖）。
修正：完美解決非交易時段或盤後抓到 UTC 髒資料導致時間變成 21:15 的 bug，全面改用正確時區轉換。
"""
import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime, timedelta
import os

# ==========================================
# 1. 基本設定區與防錯參數
# ==========================================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
tickers = os.getenv("TICKERS", "NVDA,TSLA,8069.TWO,2330.TW,3576.TW").split(",")

MIN_VOLUME_SHARES = 100000  # 5分鐘成交量至少要 100,000股
MIN_PRICE_CHANGE = 0.6      # 5分鐘內價格振幅至少要大於 0.6%

# ==========================================
# 2. 核心功能函式
# ==========================================
def send_alert_to_discord(alert_data):
    """單檔股票觸發時，立即格式化發送到 Discord"""
    if not DISCORD_WEBHOOK_URL:
        return
    
    if alert_data['漲跌幅'] >= 0:
        direction_emoji = "🟩 紅棒拉抬"
        trend_arrow = "📈"
    else:
        direction_emoji = "🟥 黑棒下殺"
        trend_arrow = "📉"
        
    content = (
        f"🚨 **【5 分鐘量能突襲警報】**\n"
        f"• **股票代號**：`{alert_data['標的']}`\n"
        f"• **K線時間**：⏰ **`{alert_data['時間']}`**\n"
        f"• **即時狀態**：💥 交易量暴增 `{alert_data['量比']}` ({alert_data['當前量']:,} / 均量 {alert_data['均量']:,} 股)\n"
        f"• **該 5分K 收盤價**：`${alert_data['現價']:.2f}`\n"
        f"• **{alert_data['區間文字']} 走勢**：{trend_arrow} {direction_emoji} (`{alert_data['漲跌幅']:+.2f}%`)"
    )
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    except Exception as e:
        print(f"Discord 傳送失敗: {e}")

def run_minute_radar():
    """即時雷達掃描主邏輯"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 啟動 5分K 量能雷達掃描 (時區校正版)...")
    print(f"{'標的':<8} | {'判定':<4} | {'K線時間':<8} | {'當前5分K價格':<8} | {'5分K量比':<6} | {'當前量':<8} | {'漲跌%':<6}")
    print("-" * 95)
    
    valid_tickers = [s for s in tickers if len(s.split(".")) <= 4]
    if not valid_tickers:
        print("沒有有效的個股標的名單。")
        return
        
    try:
        all_data = yf.download(valid_tickers, period="7d", interval="5m", threads=True, progress=False)
        
        for symbol in valid_tickers:
            try:
                # 記憶體內安全抽離單檔股票數據
                if len(valid_tickers) == 1:
                    df = all_data.dropna().copy()
                else:
                    if symbol not in all_data.columns.get_level_values(1):
                        continue
                    df = all_data.xs(symbol, axis=1, level=1).dropna().copy()
                    
                if df.empty or len(df) < 22:
                    continue
                
                # 🌟 【時區修正核心】將 DataFrame 索引統一轉換為正確的在地時區
                if ".TW" in symbol or ".TWO" in symbol:
                    # 台股：若無時區先指定 UTC 再轉台北，已有時區就直接轉台北
                    if df.index.tz is None:
                        df.index = df.index.tz_localize('UTC').tz_convert('Asia/Taipei')
                    else:
                        df.index = df.index.tz_convert('Asia/Taipei')
                    
                    # 🌟 盤後防錯：過濾掉收盤交易時間（13:30）以後的異常髒資料
                    df = df[df.index.time <= datetime.strptime("13:35", "%H:%M").time()]
                else:
                    # 美股：轉換為紐約時區
                    if df.index.tz is None:
                        df.index = df.index.tz_localize('UTC').tz_convert('America/New_York')
                    else:
                        df.index = df.index.tz_convert('America/New_York')
                
                if len(df) < 22:
                    continue

                # 獲取最新一根已完整收盤的 5分K (倒數第二根)
                latest_k = df.iloc[-2]
                
                start_dt_fixed = latest_k.name
                end_dt_fixed = start_dt_fixed + timedelta(minutes=5)

                # 時間格式化
                tz_label = "(台股時間)" if (".TW" in symbol or ".TWO" in symbol) else "(美東時間)"
                k_time_with_date = start_dt_fixed.strftime('%Y-%m-%d %H:%M')
                interval_text = f"{start_dt_fixed.strftime('%H:%M')} ~ {end_dt_fixed.strftime('%H:%M')}"
                
                t_o = float(latest_k['Open'])
                t_h = float(latest_k['High'])
                t_l = float(latest_k['Low'])
                t_c = float(latest_k['Close'])
                t_v = float(latest_k['Volume'])
                
                # 歷史 20 根成交量均量計算
                past_20_rows = df.iloc[-22:-2]
                past_20_v_series = past_20_rows['Volume']
                clean_past_20 = past_20_v_series[past_20_v_series > 0]
                if len(clean_past_20) < 10:
                    continue
                v_ma_20 = clean_past_20.mean()
                
                ratio_vol = t_v / v_ma_20 if v_ma_20 > 0 else 0
                price_change = ((t_c - t_o) / t_o) * 100 if t_o > 0 else 0
                
                # 篩選條件
                is_match = (ratio_vol >= 3.5 and t_v >= MIN_VOLUME_SHARES and abs(price_change) >= MIN_PRICE_CHANGE)
                status_icon = "✅" if is_match else "❌"
                
                print(f"{symbol:<10} | {status_icon:<4} | {k_time_with_date:<16} | {t_c:>8.2f} | {ratio_vol:>5.1f}x | {int(t_v):>8} | {price_change:>+5.2f}%")
                
                if is_match:
                    print(f"\n🔍 [後台核對數據] >>> 標的: {symbol} 觸發警報！")
                    print(f" ┌── 當前 原生5分K 數據 (區間: {start_dt_fixed.strftime('%Y-%m-%d')} {interval_text}) ──┐")
                    print(f" │ 開盤價 (Open) : {t_o:.2f}")
                    print(f" │ 最高價 (High) : {t_h:.2f}")
                    print(f" │ 最低價 (Low)  : {t_l:.2f}")
                    print(f" │ 收盤價 (Close): {t_c:.2f}")
                    print(f" │ 當前量 (Volume): {int(t_v):,} 股")
                    print(f" └──────────────────────────────────┘")
                    print(f" ┌── 過去 20 根 原生 5分K 歷史清單 ──┐")
                    for idx, (timestamp, row) in enumerate(past_20_rows.iterrows(), 1):
                        vol = row['Volume']
                        hist_open = row['Open']
                        t_show = timestamp.strftime('%Y-%m-%d %H:%M')
                        print(f" │ {idx:02d}. [{t_show}] {int(vol):>9,} 股 | 開盤: {hist_open:.2f}")
                    print(f" │")
                    print(f" │ 計算所得 20 根 5分K 原始平均量 (MA20): {int(v_ma_20):,} 股")
                    print(f" │ 實際計算量比: {ratio_vol:.2f} 倍")
                    print(f" └──────────────────────────────────┘\n")
                    
                    alert_data = {
                        "標的": symbol,
                        "時間": f"{k_time_with_date} {tz_label}",
                        "現價": t_c,
                        "量比": f"{ratio_vol:.1f} 倍",
                        "當前量": int(t_v),
                        "均量": int(v_ma_20),
                        "漲跌幅": price_change,
                        "區間文字": interval_text
                    }
                    send_alert_to_discord(alert_data)
                    
            except Exception as e:
                continue
    except Exception as e:
        print(f"批次下載失敗: {e}")
        
    print("-" * 95)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 這一輪 5分K 掃描結束。")

if __name__ == "__main__":

    while True:
        try:
            run_minute_radar()
            print("😴 掃描完成，等待 5 分鐘...")
            time.sleep(300)  # 300 秒 = 5 分鐘
        except KeyboardInterrupt:
            print("\n👋 監控已手動停止。")
            break  

