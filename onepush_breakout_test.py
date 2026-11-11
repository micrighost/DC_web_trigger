"""
### 📈 進場條件 (Entry Rules)
1. **波動爆發**：今日 K 棒的高低點差（波動幅度）大於 14 日平均真實波幅（ATR）的 2.0 倍。
   \[\text{High} - \text{Low} > 2.0 \times \text{ATR}(14)\]
2. **實體質量**：今日 K 棒實體部分（收盤與開盤的絕對差）佔整支 K 棒比例超過 80%，代表多頭氣勢強勁且無長上影線干擾。
   \[\frac{\vert{}\text{Close} - \text{Open}\vert{}}{\text{High} - \text{Low}} > 0.8\]
3. **量能背書**：當日成交量大於 20 日平均成交量的 1.5 倍（即爆出 20 日 1.5 倍均量）。
   \[\text{Volume} > 1.5 \times \text{Volume\_MA}(20)\]
4. **方向確認**：今日收盤價高於昨日收盤價（今日收紅）。

### 🛡️ 明日出場機制 (Exit Rules)
1. **成本守護**：若盤中跌破「今日收盤價（進場價）」，代表此攻擊為無效攻擊，立即執行出清。
2. **慣性守護**：若開盤即轉黑（低於開盤價），代表多頭慣性消失，立即撤退。
"""

import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def backtest_trend_strategy():
    # 預設測試標的（可自行在環境變數或此處替換）
    tickers_str = os.getenv("TICKERS", "2330.TW,2603.TW,2317.TW,2454.TW")
    tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
    
    all_trades = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=182) # 半年
    
    print(f"📊 開始【長紅爆量+獲利奔騰機制】回測期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"📦 標的總數: {len(tickers)} 檔")
    print("-" * 75)
    
    try:
        # 單次打包下載，防止被 Yahoo Finance 鎖 IP
        print("📥 正在下載完整數據中...")
        all_data = yf.download(
            tickers, 
            start=(start_date - timedelta(days=40)).strftime('%Y-%m-%d'), # 多拉40天算ATR與均量
            end=end_date.strftime('%Y-%m-%d'), 
            group_by='ticker', 
            progress=False
        )
    except Exception as e:
        print(f"❌ 下載失敗: {e}")
        return

    # 標準化單檔股票欄位結構
    if len(tickers) == 1:
        symbol = tickers[0]
        all_data.columns = pd.MultiIndex.from_product([[symbol], all_data.columns])

    # 迴圈計算每檔股票
    for symbol in tickers:
        if symbol not in all_data.columns.get_level_values(0):
            continue
            
        df = all_data[symbol].dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        if len(df) < 21:
            continue
            
        # 計算最新技術指標：ATR 與 20日均量
        h, l, c, o, v = df['High'], df['Low'], df['Close'], df['Open'], df['Volume']
        tr = pd.concat([h-l, abs(h-c.shift(1)), abs(l-c.shift(1))], axis=1).max(axis=1)
        df['ATR14'] = tr.rolling(14).mean()
        df['V_MA20'] = v.rolling(20).mean()
        df = df.dropna(subset=['ATR14', 'V_MA20'])
        
        # 過濾出在半年回測區間內的時間數據
        df = df[df.index >= start_date.strftime('%Y-%m-%d')]
        
        # 開始逐日回測 (保留最後一天不進場，因為隔天沒數據出場)
        for i in range(0, len(df) - 1):
            # 昨日的收盤（用來判斷今日是否收紅比昨日高）
            # 需要回頭找原始 Data 才能拿到真正的昨日收盤
            current_date = df.index[i]
            original_idx = all_data[symbol].index.get_loc(current_date)
            p_c = float(all_data[symbol]['Close'].iloc[original_idx - 1])
            
            # 今日數據 (進場日)
            t_date = current_date.strftime('%Y-%m-%d')
            t_o = float(df['Open'].iloc[i])
            t_h = float(df['High'].iloc[i])
            t_l = float(df['Low'].iloc[i])
            t_c = float(df['Close'].iloc[i])
            t_v = float(df['Volume'].iloc[i])
            atr = float(df['ATR14'].iloc[i])
            v_ma = float(df['V_MA20'].iloc[i])
            
            # 明日數據 (出場日)
            n_date = df.index[i+1].strftime('%Y-%m-%d')
            n_o = float(df['Open'].iloc[i+1])
            n_h = float(df['High'].iloc[i+1])
            n_l = float(df['Low'].iloc[i+1])
            n_c = float(df['Close'].iloc[i+1])
            
            if atr <= 0 or v_ma <= 0:
                continue
                
            # 策略條件計算
            ratio_atr = (t_h - t_l) / atr
            ratio_body = (abs(t_c - t_o) / (t_h - t_l)) if (t_h - t_l) > 0 else 0
            ratio_vol = t_v / v_ma
            
            # 篩選條件：ATR爆發>2 + 實體>80% + 量>1.5倍 + 收盤高於昨收
            is_match = (ratio_atr > 2.0 and ratio_body > 0.8 and ratio_vol > 1.5 and t_c > p_c)
            
            if is_match:
                # 🌟【關鍵出場邏輯：讓獲利奔騰機制】🌟
                # 狀況 A：如果明天的最低價(n_l) 跌破或等於 明天的開盤價(n_o) -> 代表盤中轉黑，直接在開盤價被點到走人
                if n_l < n_o:
                    exit_price = n_o
                    exit_type = "❌ 盤中跌破開盤，一轉黑立即撤退"
                # 狀況 B：如果明天的最低價(n_l) 完全沒跌破開盤價 -> 獲利奔騰，抱到收盤價才出場
                else:
                    exit_price = n_c
                    exit_type = "🚀 盤中未曾轉黑，強勢抱到收盤走"
                    
                profit_loss_pct = (exit_price - t_c) / t_c * 100
                
                all_trades.append({
                    "股票代號": symbol,
                    "進場日期": t_date,
                    "今日收盤(進場價)": t_c,
                    "ATR倍數": round(ratio_atr, 2),
                    "實體%": f"{ratio_body*100:.0f}%",
                    "量增倍數": round(ratio_vol, 2),
                    "出場日期": n_date,
                    "明日開盤": n_o,
                    "明日最低": n_l,
                    "明日收盤": n_c,
                    "出場價格": exit_price,
                    "出場分類": exit_type,
                    "該筆損益": round(profit_loss_pct, 2)
                })

    # ==========================================
    # 3. 報告統計與最後 3 筆詳細列印
    # ==========================================
    print("\n" + "="*30 + " 回測報告統計 " + "="*30)
    if not all_trades:
        print("❌ 半年內此標的清單無任何符合最新策略（2倍ATR+長紅+1.5倍量）的進場訊號。")
        return
        
    trades_df = pd.DataFrame(all_trades)
    total_trades = len(trades_df)
    win_trades = len(trades_df[trades_df['該筆損益'] > 0])
    win_rate = (win_trades / total_trades) * 100
    avg_return = trades_df['該筆損益'].mean()
    
    # 計算奔騰成功的次數
    hold_to_close_count = len(trades_df[trades_df['出場分類'].str.contains("收盤")])
    
    print(f"總交易筆數: {total_trades} 筆")
    print(f"交易勝率  : {win_rate:.2f} %")
    print(f"單筆平均損益: {avg_return:+.2f} %")
    print(f"成功讓獲利奔騰（抱到收盤）的次數: {hold_to_close_count} 筆 (佔總交易 {hold_to_close_count/total_trades*100:.1f}%)")
    print("=" * 74 + "\n")

    print("🔍 【最後 3 筆新策略交易詳細結果核對】")
    print("-" * 75)
    
    last_3_trades = all_trades[-3:]
    for idx, trade in enumerate(reversed(last_3_trades)):
        print(f"【倒數第 {idx+1} 筆交易】 標的: {trade['股票代號']}")
        print(f" 📅 時程: 進場日 {trade['進場日期']}  --> 出場日 {trade['出場日期']}")
        print(f" 📊 [進場訊號檢驗]")
        print(f"   - 波動幅: 今天是{trade['ATR倍數']}倍的ATR  | K棒實體: {trade['實體%']}  | 量能比: 量是MA20的{trade['量增倍數']}倍")
        print(f" 🛡️ [明日盤中動態與防守檢驗]")
        print(f"   - 明日開盤價: {trade['明日開盤']}  | 明日最低價: {trade['明日最低']}  | 明日收盤價: {trade['明日收盤']}")
        print(f"   - 💡 判斷機制: {trade['出場分類']}")
        print(f" 💰 [交易損益]")
        print(f"   - 進場成本: {trade['今日收盤(進場價)']}  --> 最終出場價: {trade['出場價格']}")
        print(f"   - 💥 該筆交易報酬率: {trade['該筆損益']:+.2f}%")
        print("-" * 75)

# 執行奔騰版回測
backtest_trend_strategy()
