'''
### 📈 進場條件 (高純度黃金交叉)
同時滿足以下兩大條件，於**隔日開盤**直接進場做多：
1. **籌碼黃金交叉**：今日外資 5MA 爬到 20MA 之上，且昨日 5MA 小於或等於 20MA。
   - 今日：`外資 5MA > 外資 20MA`
   - 昨日：`外資 5MA_t-1 <= 外資 20MA_t-1`
2. **關鍵純度過濾**：觸發交叉當天，**外資淨買超張數必須佔當天個股總成交量的 15% 以上**。
   - \[\frac{\text{外資當日淨買超股數}}{\text{當日個股總成交股數}} \ge 15\%\]
   - **核心意義**：確保外資是這波追高行情的「絕對核心主角」，徹底過濾掉散戶熱炒、或隔日沖主力包裝的虛假交叉。

### 📉 出場機制 (死亡交叉)
滿足以下條件，於**隔日開盤**立即平倉（出場）不留戀：
* **籌碼死亡交叉**：今日外資 5MA 跌破 20MA 之下，且昨日 5MA 大於或等於 20MA。
  外資淨買超張數**不須**佔當天個股總成交量的 15% 以上
  - 今日：`外資 5MA < 外資 20MA`
  - 昨日：`外資 5MA_t-1 >= 外資 20MA_t-1`
  - **核心意義**：外資短期買盤枯竭或開始集體倒貨，波段慣性改變，迅速獲利了結或停損。
'''
  
import os
import time
import datetime
import warnings
import pandas as pd
import numpy as np
from FinMind.data import DataLoader

warnings.filterwarnings('ignore', category=FutureWarning)

# ==========================================
# 1. 回測基本設定與風控參數
# ==========================================
# 包含中大型指標權值股與高波動電子股

# stock_list = [
#     "2301", "2303", "2308", "2313", "2317", "2324", "2327", "2330", "2337", "2344",
#     "2345", "2347", "2352", "2353", "2354", "2356", "2357", "2360", "2368", "2371",
#     "2376", "2377", "2379", "2382", "2383", "2385", "2392", "2395", "2404", "2408",
#     "2409", "2412", "2449", "2451", "2454", "2455", "2457", "2458", "2474", "2481",
#     "2492", "2498", "3005", "3006", "3008", "3017", "3023", "3034", "3035", "3037",
#     "3044", "3045", "3105", "3189", "3227", "3231", "3264", "3293", "3324", "3406",
#     "3443", "3481", "3529", "3532", "3533", "3576", "3661", "3702", "3706", "3711",
#     "3714", "4904", "4906", "4919", "4938", "4958", "4966", "4967", "5274", "5347",
#     "5371", "5425", "5483", "6121", "6138", "6147", "6176", "6213", "6223", "6244",
#     "6257", "6269", "6274", "6278", "6285", "6290", "6411", "6415", "6456", "6488",
#     "6510", "6669", "6770", "8046", "8150", "8299", "8069", "8086"
# ]

# 測試組
stock_list = [
    "2301", "2303", "2308", "2313", "2317", "2324", "2327", "2330", "2337", "2344"
]

# 設定回測區間（過去 6 個月）
end_date = datetime.date.today().strftime("%Y-%m-%d")
start_date = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")

FAST_MA = 5
SLOW_MA = 20
VOLUME_RATIO_THRESHOLD = 0.15  # 進場：外資淨買超需佔當日總量 15% 以上（出場不設限）

# 100萬虛擬資金池與風控配置
INITIAL_CASH = 1000000.0
CASH = INITIAL_CASH
POSITION_LIMIT_PER_STOCK = 0.20  # 單檔股票最多配置總資金的 20% (上限20萬)，避免單壓爆倉

dl = DataLoader()
all_trades = []      # 儲存每筆交易明細
active_positions = {} # 記錄當前持股

print(f"🕵️‍♂️ 啟動【終極高純度外資籌碼回測系統（無摩擦成本純淨版）】...")
print(f"📅 回測區間: {start_date} ~ {end_date} (過去6個月)")
print(f"💰 初始模擬資金: {INITIAL_CASH:,.0f} 元 | 單檔持股上限: {POSITION_LIMIT_PER_STOCK*100:.0f}%")
print(f"🧾 交易成本狀態: 已關閉摩擦成本（不計手續費、不計證交稅）")
print(f"🛑 防鎖 IP 機制已啟動，每檔標的自動延遲... 請稍候。")
print("=" * 80)

# ==========================================
# 2. 歷史數據抓取、對齊與歷史序列生成
# ==========================================
raw_stock_data = {}

for stock_id in stock_list:
    try:
        # 抓取法人籌碼
        chip_data = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date, end_date=end_date)
        time.sleep(0.5)
        
        if chip_data is None or len(chip_data) == 0: continue
        df_chip = pd.DataFrame(chip_data)
        df_chip['date'] = pd.to_datetime(df_chip['date'])
        df_foreign = df_chip[df_chip['name'] == 'Foreign_Investor'].copy()
        if df_foreign.empty: continue
            
        df_foreign = df_foreign.sort_values('date').set_index('date')
        df_foreign['f_net'] = pd.to_numeric(df_foreign['buy']) - pd.to_numeric(df_foreign['sell'])
        
        # 抓取歷史 K 線
        k_data = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
        time.sleep(0.5)
        
        if k_data is None or len(k_data) == 0: continue
        df_k = pd.DataFrame(k_data)
        df_k['date'] = pd.to_datetime(df_k['date'])
        df_k = df_k.sort_values('date').set_index('date')
        
        # 合併數據
        df_merged = pd.merge(df_foreign[['f_net']], df_k[['open', 'close', 'Trading_Volume']], left_index=True, right_index=True, how='inner')
        
        # 計算籌碼動能均線與純度佔比
        df_merged['volume_ratio'] = df_merged['f_net'] / df_merged['Trading_Volume']
        df_merged['inst_fastma'] = df_merged['f_net'].rolling(FAST_MA).mean()
        df_merged['inst_slowma'] = df_merged['f_net'].rolling(SLOW_MA).mean()
        df_merged.dropna(subset=['inst_fastma', 'inst_slowma', 'volume_ratio'], inplace=True)
        
        if len(df_merged) >= 3:
            raw_stock_data[stock_id] = df_merged
            print(f"✅ 股票 {stock_id} 數據載入成功，共 {len(df_merged)} 個交易日。")
    except Exception as e:
        print(f"❌ 股票 {stock_id} 數據下載失敗: {e}")
        continue

# 建立所有股票共同擁有的交易日時間軸
all_dates = sorted(list(set([d for stock_df in raw_stock_data.values() for d in stock_df.index])))

print("\n" + "="*80)
print("⏳ 開始進行時間軸逐日交叉模擬...")
print("="*80)

# ==========================================
# 3. 時間軸逐日模擬（模擬資金水位與實戰買賣）
# ==========================================
for date_idx in range(1, len(all_dates) - 1):
    current_date = all_dates[date_idx]
    next_date = all_dates[date_idx + 1]
    
    # --- A. 優先處理今日需要平倉（出場）的股票 ---
    stocks_to_sell = []
    for stock_id, pos_info in list(active_positions.items()):
        df = raw_stock_data[stock_id]
        if current_date not in df.index: continue
        
        loc_today = df.index.get_loc(current_date)
        if loc_today < 1: continue
        row_today = df.iloc[loc_today]
        row_yesterday = df.iloc[loc_today - 1]
        
        fast_today, slow_today = row_today['inst_fastma'], row_today['inst_slowma']
        fast_yest, slow_yest = row_yesterday['inst_fastma'], row_yesterday['inst_slowma']
        
        # 死亡交叉觸發（無任何限制，果斷撤退）
        if (fast_today < slow_today) and (fast_yest >= slow_yest):
            stocks_to_sell.append(stock_id)

    # 執行隔日開盤平倉動作（純淨版：無摩擦成本）
    for stock_id in stocks_to_sell:
        df = raw_stock_data[stock_id]
        if next_date not in df.index: continue
        
        row_tomorrow = df.loc[next_date]
        exit_price = float(row_tomorrow['open']) # 隔日開盤價出場
        pos_info = active_positions.pop(stock_id)
        
        # 純淨版直接回補總回收金額
        net_return = pos_info['shares'] * exit_price
        CASH += net_return # 資金回補資金池
        
        # 計算這筆交易的淨報酬率
        net_roi = (exit_price - pos_info['buy_price']) / pos_info['buy_price']
        
        all_trades.append({
            "Stock_ID": stock_id,
            "Buy_Date": pos_info['buy_date'],
            "Buy_Price": pos_info['buy_price'],
            "Sell_Date": next_date.strftime('%Y-%m-%d'),
            "Sell_Price": exit_price,
            "Net_ROI": net_roi
        })

    # --- B. 處理今日觸發黃金交叉、明日需要進場的股票 ---
    for stock_id, df in raw_stock_data.items():
        if stock_id in active_positions: continue # 已持股的不重複買進
        if current_date not in df.index: continue
        
        loc_today = df.index.get_loc(current_date)
        if loc_today < 1: continue
        row_today = df.iloc[loc_today]
        row_yesterday = df.iloc[loc_today - 1]
        
        fast_today, slow_today = row_today['inst_fastma'], row_today['inst_slowma']
        fast_yest, slow_yest = row_yesterday['inst_fastma'], row_yesterday['inst_slowma']
        ratio_today = row_today['volume_ratio']
        
        is_gold_cross = (fast_today > slow_today) and (fast_yest <= slow_yest)
        
        # 嚴格進場：黃金交叉 且 外資佔比大於等於 15%
        if is_gold_cross and (ratio_today >= VOLUME_RATIO_THRESHOLD):
            # 計算配置資金上限（目前總淨值的 20%）
            current_portfolio_value = CASH + sum([p['shares'] * float(raw_stock_data[sid].loc[current_date]['close']) for sid, p in active_positions.items() if current_date in raw_stock_data[sid].index])
            invest_capital_target = current_portfolio_value * POSITION_LIMIT_PER_STOCK
            
            # 確保手頭現金足夠配置
            invest_capital = min(invest_capital_target, CASH)
            if invest_capital < 10000: continue # 資金過低不建立倉位
            
            if next_date not in df.index: continue
            row_tomorrow = df.loc[next_date]
            buy_price = float(row_tomorrow['open']) # 隔日開盤價進場
            
            # 純 K 線計算股數（無手續費干擾）
            shares = np.floor(invest_capital / buy_price)
            if shares <= 0: continue
            
            actual_spend = shares * buy_price
            CASH -= actual_spend # 從現金池扣除
            
            active_positions[stock_id] = {
                "buy_date": next_date.strftime('%Y-%m-%d'),
                "buy_price": buy_price,
                "shares": shares,
                "invest_capital": actual_spend
            }

# 回測結束，若手頭仍有持股，以最後一天的收盤價進行強制未實現清算
last_date = all_dates[-1]
for stock_id, pos_info in list(active_positions.items()):
    df = raw_stock_data[stock_id]
    last_row = df.iloc[-1]
    exit_price = float(last_row['close'])
    
    net_return = pos_info['shares'] * exit_price
    CASH += net_return
    
    net_roi = (exit_price - pos_info['buy_price']) / pos_info['buy_price']
    all_trades.append({
        "Stock_ID": stock_id,
        "Buy_Date": pos_info['buy_date'],
        "Buy_Price": pos_info['buy_price'],
        "Sell_Date": f"{last_date.strftime('%Y-%m-%d')}(未實現)",
        "Sell_Price": exit_price,
        "Net_ROI": net_roi
    })

# ==========================================
# 4. 績效統計與報告輸出
# ==========================================
print("\n" + "="*80)
print("🏁 【真實回測報告：純淨無摩擦成本交易明細】")
print("-"*80)

if len(all_trades) == 0:
    print("😭 過去 6 個月內，高純度篩選門檻過於嚴格，沒有觸發任何完整的買賣交易。")
else:
    df_results = pd.DataFrame(all_trades)
    print(f"{'股票':<6} | {'進場日期':<10} | {'進場價':>7} | {'出場日期':<12} | {'出場價':>7} | {'淨報酬率':>12}")
    print("-"*80)
    for _, trade in df_results.iterrows():
        print(f"{trade['Stock_ID']:<6} | {trade['Buy_Date']:<10} | {trade['Buy_Price']:>7.2f} | {trade['Sell_Date']:<12} | {trade['Sell_Price']:>7.2f} | {trade['Net_ROI']:>14.2%}")
    
    total_trades = len(df_results)
    win_trades = len(df_results[df_results['Net_ROI'] > 0])
    win_rate = win_trades / total_trades if total_trades > 0 else 0
    avg_roi = df_results['Net_ROI'].mean()
    max_profit = df_results['Net_ROI'].max()
    max_loss = df_results['Net_ROI'].min()
    
    final_net_worth = CASH
    total_profit_rate = (final_net_worth - INITIAL_CASH) / INITIAL_CASH

    print("="*80)
    print("📊 【核心策略績效總體檢報告（純淨版）】")
    print("-"*80)
    print(f"💵 初始配置總資金 (Initial Cash)   : {INITIAL_CASH:,.0f} 元")
    print(f"💰 最終資產總淨值 (Final Capital)   : {final_net_worth:,.0f} 元")
    print(f"🔥 過去6個月總投報率 (Total Return)  : {total_profit_rate:+.2%}")
    print("-"*80)
    print(f"📈 總交易次數 (Total Trades)       : {total_trades} 次")
    print(f"🎯 獲利交易次數 (Win Trades)        : {win_trades} 次")
    print(f"🏆 策略總勝率 (Win Rate)            : {win_rate:.2%}")
    print(f"💎 平均單筆淨報酬率 (Avg Net ROI)   : {avg_roi:+.2%}")
    print(f"🚀 單筆最大獲利 (Max Profit)        : {max_profit:+.2%}")
    print(f"📉 單筆最大損失 (Max Loss)          : {max_loss:+.2%}")
print("="*80 + "\n")
