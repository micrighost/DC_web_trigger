"""
## 📌 策略核心邏輯 (Strategy Rules)

### 📈 進場條件 (Entry Rules)
1. **量能異常**：當日成交量 ≥ 2 倍的昨日成交量 (`Volume_t > 2 * Volume_t-1`)。
2. **K棒方向**：收紅 K 線 (`Close > Open`)。

### 🛡️ 明日出場機制 (Exit Rules)
1. **成本守護**：若盤中跌破「今日收盤價（進場價）」，立即執行出清。
2. **慣性守護**：若開盤即轉黑（低於開盤價），立即撤退。
"""

import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def backtest_strategy_let_profit_run():
    # 預設測試標的
    tickers_str = os.getenv("TICKERS", "2330.TW,2603.TW,2317.TW,2454.TW")
    tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
    
    all_trades = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=182) # 半年回測
    
    print(f"📊 開始【讓獲利奔騰版】回測: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"📦 標的總數: {len(tickers)} 檔")
    print("-" * 70)
    
    try:
        # 單次請求打包下載所有股票資料，防止鎖 IP
        all_data = yf.download(
            tickers, 
            start=start_date.strftime('%Y-%m-%d'), 
            end=end_date.strftime('%Y-%m-%d'), 
            group_by='ticker', 
            progress=False
        )
    except Exception as e:
        print(f"❌ 下載失敗: {e}")
        return

    if len(tickers) == 1:
        symbol = tickers
        all_data.columns = pd.MultiIndex.from_product([[symbol], all_data.columns])

    # 開始在本機記憶體中跑迴圈
    for symbol in tickers:
        if symbol not in all_data.columns.get_level_values(0):
            continue
            
        df = all_data[symbol].dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        if len(df) < 3:
            continue
            
        for i in range(1, len(df) - 1):
            # 今日進場點數據
            t_date = df.index[i].strftime('%Y-%m-%d')
            t_o = float(df['Open'].iloc[i])
            t_c = float(df['Close'].iloc[i])
            t_v = float(df['Volume'].iloc[i])
            
            p_v = float(df['Volume'].iloc[i-1]) # 昨日量
            
            # 明日出場點數據 (需觀察明日全天的 Open, Low, Close)
            n_date = df.index[i+1].strftime('%Y-%m-%d')
            n_o = float(df['Open'].iloc[i+1])
            n_l = float(df['Low'].iloc[i+1])
            n_c = float(df['Close'].iloc[i+1])
            
            if p_v <= 0:
                continue
                
            vol_ratio = t_v / p_v
            is_red_k = t_c > t_o
            
            # 觸發進場訊號：爆量2倍 + 收紅K
            if vol_ratio >= 2.0 and is_red_k:
                
                # 🌟【全新核心邏輯：奔騰機制】
                # 如果隔天「最低價」大於或等於「開盤價」，代表盤中從未跌破開盤，我們撐到「收盤」才走
                if n_l >= n_o:
                    exit_price = n_c
                    exit_type = "🚀 獲利奔騰 (無跌破開盤，持有至收盤賣出)"
                # 如果隔天「最低價」小於「開盤價」，代表盤中曾經跌破開盤，一跌破立刻以「開盤價」走人
                else:
                    exit_price = n_o
                    exit_type = "🛡️ 觸發防守 (盤中跌破開盤，以開盤價撤退)"
                
                # 計算損益
                profit_loss_pct = (exit_price - t_c) / t_c * 100
                
                all_trades.append({
                    "股票代號": symbol,
                    "進場日期(今日)": t_date,
                    "昨日成交量": p_v,
                    "今日開盤價": t_o,
                    "今日收盤價(進場價)": t_c,
                    "今日成交量": t_v,
                    "量增倍數": round(vol_ratio, 2),
                    "出場日期(明日)": n_date,
                    "明日開盤價": n_o,
                    "明日最低價": n_l,
                    "明日收盤價": n_c,
                    "實際出場價": exit_price,
                    "出場型態": exit_type,
                    "該筆損益": round(profit_loss_pct, 2)
                })

    # ========================================== #
    # 3. 輸出結果與最後三筆核對
    # ========================================== #
    print("\n" + "="*30 + " 回測報告統計 (奔騰版) " + "="*30)
    if not all_trades:
        print("❌ 半年內此標的清單無任何符合策略之進場訊號。")
        return
        
    trades_df = pd.DataFrame(all_trades)
    total_trades = len(trades_df)
    win_trades = len(trades_df[trades_df['該筆損益'] > 0])
    win_rate = (win_trades / total_trades) * 100
    avg_return = trades_df['該筆損益'].mean()
    
    print(f"總交易筆數: {total_trades} 筆")
    print(f"交易勝率  : {win_rate:.2f} %")
    print(f"單筆平均損益: {avg_return:+.2f} %")
    print("=" * 74 + "\n")

    print("🔍 【最後 3 筆交易詳細成交明細核對】")
    print("-" * 74)
    
    last_3_trades = all_trades[-3:]
    for idx, trade in enumerate(reversed(last_3_trades)):
        print(f"【倒數第 {idx+1} 筆交易】 標的: {trade['股票代號']}")
        print(f" 📅 進場日: {trade['進場日期(今日)']}  --> 出場日: {trade['出場日期(明日)']}")
        print(f" 📊 [進場數據] 昨日量: {trade['昨日成交量']:,} | 今日量: {trade['今日成交量']:,} (量增 {trade['量增倍數']} 倍)")
        print(f" 🔍 [明日盤中動態驗證]")
        print(f"   - 明日開盤價: {trade['明日開盤價']} | 明日最低價: {trade['明日最低價']} | 明日收盤價: {trade['明日收盤價']}")
        print(f"   - 💡 判定結果: {trade['出場型態']}")
        print(f" 💰 [交易損益]")
        print(f"   - 進場成本: {trade['今日收盤價(進場價)']} | 實際出場價: {trade['實際出場價']}")
        print(f"   - 💥 該筆交易報酬率: {trade['該筆損益']:+.2f}%")
        print("-" * 74)

# 執行奔騰版回測
backtest_strategy_let_profit_run()
