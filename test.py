import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# ==== 完整套用你的自訂清單（支援環境變數） ====
tickers = os.getenv("TICKERS", "NVDA,TSLA,2330.TW,3576.TW,1101.TW,3227.TWO,2889.TW,6488.TWO").split(",")

# ==== 回測核心參數設定 ====
LOOKBACK_PERIOD = 60
MAX_BASE_PRICE_GAP_PCT = 1.0
MIN_FRACT_COUNT = 1
MONITOR_FRACT_LIMIT = 3  # 限定存活大底必須累積滿 3 個強分型才允許進場
MIN_SHADOW_PCT = 0.3

def run_backtest():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 啟動 5分K 破底翻歷史回測引擎 (分型門檻={MONITOR_FRACT_LIMIT})...")
    print("-" * 90)
    print(f"{'標的':<10} | {'總交易':<6} | {'獲利次數':<6} | {'失敗次數':<6} | {'勝率':<8} | {'累計報酬率'}")
    print("-" * 90)
    
    valid_tickers = [s for s in tickers if len(s.split(".")) <= 4]
    if not valid_tickers:
        print("沒有有效的標的清單！")
        return
        
    # 🌟 用於統計全體總績效的計數器
    all_symbols_trades_count = 0
    all_symbols_wins_count = 0
    all_symbols_losses_count = 0
    pnl_list_for_summary = [] # 收集各檔股票的報酬率來算平均總報酬
        
    try:
        # 下載 14 天的完整 5分K 資料進行滾動歷史回測
        all_data = yf.download(valid_tickers, period="14d", interval="5m", threads=True, progress=False)
        
        for symbol in valid_tickers:
            try:
                # 擷取單一標的資料
                if len(valid_tickers) == 1:
                    df = all_data.dropna(subset=['Close', 'Volume']).copy()
                else:
                    if symbol not in all_data.columns.get_level_values(1):
                        continue
                    df = all_data.xs(symbol, axis=1, level=1).dropna(subset=['Close', 'Volume']).copy()
                
                if df.empty or len(df) < (LOOKBACK_PERIOD + 10):
                    continue
                
                # 時區修復：統一轉為該商品在地時間並移除時區標籤
                if df.index.tz is not None:
                    df.index = df.index.tz_convert(df.index.tz).tz_localize(None)

                # 根據市場動態調整停利基準 (台股 1.0%，美股 1.5%)
                is_tw = ".TW" in symbol or ".TWO" in symbol
                take_profit_pct = 1.0 if is_tw else 1.5

                # ---- 開始模擬時間軸滾動歷史回測 ----
                trades = [] 
                in_position = False
                entry_price = 0
                stop_loss = 0
                entry_time = None
                
                for idx in range(LOOKBACK_PERIOD + 2, len(df) - 2):
                    current_time = df.index[idx]
                    current_k = df.iloc[idx]
                    
                    # 🛑 持倉狀態：執行出場清算檢查
                    if in_position:
                        # 鋼鐵停損
                        if current_k['Low'] < stop_loss:
                            pnl = ((stop_loss - entry_price) / entry_price) * 100
                            trades.append({'entry_time': entry_time, 'exit_time': current_time, 'pnl': pnl, 'result': 'LOSS'})
                            in_position = False
                            continue
                        # 智慧停利
                        elif current_k['High'] >= entry_price * (1 + take_profit_pct / 100):
                            pnl = take_profit_pct
                            trades.append({'entry_time': entry_time, 'exit_time': current_time, 'pnl': pnl, 'result': 'WIN'})
                            in_position = False
                            continue
                        else:
                            continue 
                    
                    # 🔍 空倉狀態：尋找進場訊號 (嚴格防範未來數據)
                    sub_df = df.iloc[:idx]
                    all_raw_fracts = []
                    for i in range(2, len(sub_df) - 2):
                        if (sub_df.iloc[i]['Low'] < sub_df.iloc[i-1]['Low'] and sub_df.iloc[i]['Low'] < sub_df.iloc[i-2]['Low'] and 
                            sub_df.iloc[i]['Low'] < sub_df.iloc[i+1]['Low'] and sub_df.iloc[i]['Low'] < sub_df.iloc[i+2]['Low']):
                            all_raw_fracts.append({'time': sub_df.index[i], 'low': sub_df.iloc[i]['Low']})
                    
                    history_df = sub_df.iloc[-(LOOKBACK_PERIOD + 1):]
                    h_list = [{'Time': t, 'Open': r['Open'], 'Low': r['Low'], 'Close': r['Close']} for t, r in history_df.iterrows()]
                    
                    # 依時序演進分型（套用最新核心邏輯）
                    valid_fracts = []
                    for k_line in h_list:
                        if valid_fracts:
                            valid_fracts = [x for x in valid_fracts if x['low'] <= k_line['Low']]
                            
                        for raw_f in all_raw_fracts:
                            if raw_f['time'] == k_line['Time']:
                                if not valid_fracts:
                                    valid_fracts.append(raw_f)
                                else:
                                    min_e = min([x['low'] for x in valid_fracts])
                                    if abs(((raw_f['low'] - min_e) / min_e) * 100) <= MAX_BASE_PRICE_GAP_PCT:
                                        valid_fracts.append(raw_f)
                                    else:
                                        valid_fracts = [raw_f]
                    
                    if len(valid_fracts) < MONITOR_FRACT_LIMIT:
                        continue
                        
                    all_lows = [x['low'] for x in valid_fracts]
                    base_support = np.mean(all_lows)
                    abs_bottom = np.min(all_lows)
                    
                    t_o, t_l, t_c = float(current_k['Open']), float(current_k['Low']), float(current_k['Close'])
                    shadow_pct = ((min(t_o, t_c) - t_l) / t_l) * 100 if t_l > 0 else 0
                    
                    is_spring_match = (t_l < abs_bottom) and (t_c >= base_support) and (shadow_pct >= MIN_SHADOW_PCT)
                    
                    if is_spring_match:
                        in_position = True
                        entry_price = t_c
                        stop_loss = t_l  
                        entry_time = current_time
                
                # ---- 統計單檔標 結果 ----
                total_trades = len(trades)
                if total_trades == 0:
                    print(f"{symbol:<10} | {'0':^6} | {'0':^6} | {'0':^6} | {'0.0%':^8} | 0.00%")
                    pnl_list_for_summary.append(0.0) # 沒交易視為 0% 報酬
                    continue
                    
                wins = len([x for x in trades if x['result'] == 'WIN'])
                losses = len([x for x in trades if x['result'] == 'LOSS'])
                win_rate = (wins / total_trades) * 100
                total_pnl = sum([x['pnl'] for x in trades])
                
                print(f"{symbol:<10} | {total_trades:^6} | {wins:^6} | {losses:^6} | {win_rate:>6.1f}% | {total_pnl:>+6.2f}%")
                
                # 🌟 累加到全體統計變數中
                all_symbols_trades_count += total_trades
                all_symbols_wins_count += wins
                all_symbols_losses_count += losses
                pnl_list_for_summary.append(total_pnl)
                
            except Exception:
                continue
                
    except Exception as e:
        print(f"回測批次下載失敗: {e}")
        
    # ==== 🌟 新增：全體總體報酬率加總統計報表 ====
    print("-" * 90)
    if all_symbols_trades_count > 0:
        global_win_rate = (all_symbols_wins_count / all_symbols_trades_count) * 100
        # 總體投資組合報酬率為各商品累計報酬之平均
        global_avg_pnl = np.mean(pnl_list_for_summary) if pnl_list_for_summary else 0.0
        
        print(f"{'TOTAL (全部)':<10} | {all_symbols_trades_count:^6} | {all_symbols_wins_count:^6} | {all_symbols_losses_count:^6} | {global_win_rate:>6.1f}% | {global_avg_pnl:>+6.2f}%")
    else:
        print(f"{'TOTAL (全部)':<10} | {'0':^6} | {'0':^6} | {'0':^6} | {'0.0%':^8} | 0.00%")
    print("-" * 90)

if __name__ == "__main__":
    run_backtest()
