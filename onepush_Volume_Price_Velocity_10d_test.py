import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def backtest_volume_price_velocity_final():
    # 預設測試標的
    tickers_str = os.getenv("TICKERS", "2330.TW,2603.TW,2317.TW,2454.TW")
    tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]
    
    all_trades = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=182) # 半年
    
    print(f"📊 開始【10D 量價速率超車策略】完整最終版回測...")
    print(f"📦 標的總數: {len(tickers)} 檔")
    print("-" * 75)
    
    try:
        # 多往前拉 60 天，確保 10日滾動、shift(1) 與 shift(2) 計算基期絕對完全正確
        fetch_start = (start_date - timedelta(days=60)).strftime('%Y-%m-%d')
        fetch_end = end_date.strftime('%Y-%m-%d')
        
        all_data = yf.download(
            tickers, 
            start=fetch_start, 
            end=fetch_end, 
            group_by='ticker', 
            progress=False
        )
    except Exception as e:
        print(f"❌ 下載失敗: {e}")
        return

    # 修正單檔股票時的欄位多重索引結構不一致問題
    if len(tickers) == 1:
        symbol = tickers[0]
        all_data.columns = pd.MultiIndex.from_product([[symbol], all_data.columns])

    for symbol in tickers:
        # 安全取得單一股票 DataFrame
        if symbol not in all_data.columns.get_level_values(0):
            continue
        df_symbol = all_data[symbol].copy()
        
        # 排除完全空白的列，確保日期的連續性
        df = df_symbol.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume']).copy()
        if len(df) < 20:
            continue
            
        # 1. 嚴謹計算 10 日均價與 10 日均量 (均線基期)
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MV10'] = df['Volume'].rolling(10).mean()
        
        # 2. 精準計算 P-Line 與 V-Line 速率序列 (利用 shift 對齊，徹底解決跨週末 Bug)
        df['P_Line'] = (df['MA10'] / df['MA10'].shift(1)) - 1
        df['V_Line'] = (df['MV10'] / df['MV10'].shift(1)) - 1
        
        # 預先為歷史回溯對齊建立「前天、昨天」的平移序列
        df['MA10_Yest'] = df['MA10'].shift(1)
        df['MV10_Yest'] = df['MV10'].shift(1)
        df['P_Line_Yest'] = df['P_Line'].shift(1)
        df['V_Line_Yest'] = df['V_Line'].shift(1)
        
        df['MA10_Fore'] = df['MA10'].shift(2)
        df['MV10_Fore'] = df['MV10'].shift(2)
        
        # 篩選真正要評估進場的半年區間 (且確保明日有數據可判定出場)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        for i in range(0, len(df) - 1):
            current_date = df.index[i]
            # 限制在回測時間區間內
            if current_date < pd.to_datetime(start_date_str):
                continue
                
            # 確保前方基期資料足夠
            if i < 15: 
                continue
            
            p_today = float(df['P_Line'].iloc[i])
            v_today = float(df['V_Line'].iloc[i])
            p_yest = float(df['P_Line_Yest'].iloc[i])
            v_yest = float(df['V_Line_Yest'].iloc[i])
            
            # 策略核心三條件
            is_10d_overtake = (v_today > p_today) and (v_yest <= p_yest)
            is_red_k = float(df['Close'].iloc[i]) > float(df['Open'].iloc[i])
            is_p_limit = 0.0 <= p_today <= 0.015
            
            if is_10d_overtake and is_red_k and is_p_limit:
                # 明日數據 (隔日出場決策)
                n_o = float(df['Open'].iloc[i + 1])
                n_h = float(df['High'].iloc[i + 1])
                n_l = float(df['Low'].iloc[i + 1])
                n_c = float(df['Close'].iloc[i + 1])
                
                if n_l < n_o:
                    exit_price = n_o
                    exit_type = "❌ 盤中跌破開盤 (以明日開盤價出場)"
                else:
                    exit_price = n_c
                    exit_type = "🚀 盤中守住開盤 (以明日收盤價出場)"
                    
                profit_loss_pct = (exit_price - float(df['Close'].iloc[i])) / float(df['Close'].iloc[i]) * 100
                
                # 嚴格切片原始歷史資料 (包含今天與明天)
                raw_history_df = df.iloc[i-13 : i+2][['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                
                all_trades.append({
                    "股票代號": symbol,
                    "進場日期": current_date.strftime('%Y-%m-%d'),
                    "原始歷史資料": raw_history_df,
                    "該筆損益": round(profit_loss_pct, 2),
                    "出場決策簡述": exit_type,
                    "關鍵4日詳細計算": {
                        "前天": {
                            "日期": df.index[i-2].strftime('%Y-%m-%d'),
                            "MA10": float(df['MA10_Fore'].iloc[i]),
                            "MV10": float(df['MV10_Fore'].iloc[i]),
                        },
                        "昨天": {
                            "日期": df.index[i-1].strftime('%Y-%m-%d'),
                            "MA10": float(df['MA10_Yest'].iloc[i]),
                            "MV10": float(df['MV10_Yest'].iloc[i]),
                            "P_Line": p_yest,
                            "V_Line": v_yest
                        },
                        "今天": {
                            "日期": current_date.strftime('%Y-%m-%d'),
                            "開盤價": float(df['Open'].iloc[i]),
                            "收盤價": float(df['Close'].iloc[i]),
                            "MA10": float(df['MA10'].iloc[i]),
                            "MV10": float(df['MV10'].iloc[i]),
                            "P_Line": p_today,
                            "V_Line": v_today
                        },
                        "明天": {
                            "日期": df.index[i+1].strftime('%Y-%m-%d'),
                            "開盤價": n_o, "最高價": n_h, "最低價": n_l, "收盤價": n_c,
                            "出場價": exit_price, "決策": exit_type, "損益": round(profit_loss_pct, 2)
                        }
                    }
                })

    # ==========================================
    # 3. 輸出：總體績效統計報告
    # ==========================================
    print("\n" + "="*30 + " 📊 最終策略回測總績效 📊 " + "="*30)
    if not all_trades:
        print("❌ 半年內此標的清單無任何符合策略的進場訊號。")
        return
        
    trades_df = pd.DataFrame(all_trades)
    total_trades = len(trades_df)
    win_trades = len(trades_df[trades_df['該筆損益'] > 0])
    win_rate = (win_trades / total_trades) * 100
    avg_return = trades_df['該筆損益'].mean()
    total_return = trades_df['該筆損益'].sum()
    
    hold_to_close_count = len(trades_df[trades_df['出場決策簡述'].str.contains("收盤")])
    
    print(f" 📈 回測期間 : {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} (半年)")
    print(f" 🎯 總交易筆數 : {total_trades} 筆")
    print(f" 🏆 策略總勝率 : {win_rate:.2f} %")
    print(f" 💰 單筆平均損益 : {avg_return:+.2f} %")
    print(f" 總累積損益 (未複利) : {total_return:+.2f} %")
    print(f" 🚀 成功讓獲利奔騰 (守住開盤抱到收盤) : {hold_to_close_count} 筆 (佔總交易 {hold_to_close_count/total_trades*100:.1f}%)")
    print(f" ❌ 觸發轉黑風控 (開盤即走或盤中跌破) : {total_trades - hold_to_close_count} 筆")
    print("=" * 86 + "\n")

    # ==========================================
    # 4. 輸出：最後 3 筆詳細數據核對
    # ==========================================
    print("🔍 【最後 3 筆交易之『原始下載資料清單』與『速率線公式推導』】")
    
    last_3_trades = all_trades[-3:]
    for idx, trade in enumerate(reversed(last_3_trades)):
        seq = trade['關鍵4日詳細計算']
        print("=" * 86)
        print(f"【倒數第 {idx+1} 筆交易訊號】 標的股票: {trade['股票代號']}")
        print(f" 🎯 訊號進場日: {trade['進場日期']} | 💡 隔日出場決策: {seq['明天']['決策']} | 💰 報酬率: {seq['明天']['損益']:+.2f}%\n")
        
        print(" 📄 [區塊 A : 最原始下載歷史數據流水帳] (供直接核對看盤軟體)")
        print(f"  {'交易日期':<12} | {'開盤價':>8} | {'最高價':>8} | {'最低價':>8} | {'收盤價':>8} | {'當日成交量':>12}")
        print("  " + "-" * 72)
        for date, row in trade['原始歷史資料'].iterrows():
            date_str = date.strftime('%Y-%m-%d')
            marker = ""
            if date_str == trade['進場日期']:
                marker = " 👈 ★【今天：進場訊號日】"
            elif date_str == seq['明天']['日期']:
                marker = " 👈 🏃【明天：出場履約日】"
            print(f"  {date_str:<12} | {row['Open']:>8.2f} | {row['High']:>8.2f} | {row['Low']:>8.2f} | {row['Close']:>8.2f} | {int(row['Volume']):>12,}{marker}")
        print("\n")
        
        print(" 📊 [區塊 B : 均線數值與 P-Line / V-Line 公式推導驗收]")
        print(f"  ● 前天 ({seq['前天']['日期']}) 數據 : MA10 均價 = {seq['前天']['MA10']:.2f} | MV10 均量 = {seq['前天']['MV10']:,.2f}")
        print(f"  ● 昨天 ({seq['昨天']['日期']}) 數據 : MA10 均價 = {seq['昨天']['MA10']:.2f} | MV10 均量 = {seq['昨天']['MV10']:,.2f}")
        print(f"    * 昨天 P-Line 速率 = ({seq['昨天']['MA10']:.4f} / {seq['前天']['MA10']:.4f}) - 1 = {seq['昨天']['P_Line']:+.4%}")
        print(f"    * 昨天 V-Line 速率 = ({seq['昨天']['MV10']:.2f} / {seq['前天']['MV10']:.2f}) - 1 = {seq['昨天']['V_Line']:+.4%}")
        print(f"    📢 昨天交叉判定: 昨天 V-Line ({seq['昨天']['V_Line']:+.4%}) <= P-Line ({seq['昨天']['P_Line']:+.4%}) --> 【昨日未超車：符合】")
        print(f"  " + "-" * 72)
        print(f"  ● 今天 ({seq['今天']['日期']}) 數據 : MA10 均價 = {seq['今天']['MA10']:.2f} | MV10 均量 = {seq['今天']['MV10']:,.2f}")
        print(f"    * 今天 P-Line 速率 = ({seq['今天']['MA10']:.4f} / {seq['昨天']['MA10']:.4f}) - 1 = {seq['今天']['P_Line']:+.4%}")
        print(f"    * 今天 V-Line 速率 = ({seq['今天']['MV10']:.2f} / {seq['昨天']['MV10']:.2f}) - 1 = {seq['今天']['V_Line']:+.4%}")
        print(f"    📢 今天交叉判定: 今天 V-Line ({seq['今天']['V_Line']:+.4%}) > P-Line ({seq['今天']['P_Line']:+.4%}) --> 【今日首度超車成功：符合 ✅】")
        print(f"    📢 蓄勢限制判定: 今天 P-Line 速率為 {seq['今天']['P_Line']:+.4%} (大於 0% 且小於 1.5% 天花板 --> 【蓄勢不追高：符合 ✅】")
        print(f"  " + "-" * 72)
        print(f"  ● 明天 ({seq['明天']['日期']}) 出場損益實踐 :")
        print(f"    * 明日開盤價: {seq['明天']['開盤價']} | 最低價: {seq['明天']['最低價']} | 收盤價: {seq['明天']['收盤價']}")
        print(f"    * 💡 出場邏輯判定: {seq['明天']['決策']}")
        print(f"    * 💰 損益計算公式: ({seq['明天']['出場價']} - {seq['今天']['收盤價']}) / {seq['今天']['收盤價']} = {seq['明天']['損益']:+.2f}%")
        print("=" * 86 + "\n")

# 執行修復後的完美版回測
backtest_volume_price_velocity_final()
