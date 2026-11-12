import os
import requests

import datetime
import pandas as pd
import warnings
import time
from FinMind.data import DataLoader


# ==========================================
# 1. 基本設定區
# ==========================================

# 精選適合「波段動能策略」的高波動、中大型電子股名單

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

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 關閉不必要的警告
warnings.filterwarnings('ignore', category=FutureWarning)

def check_stock_signal_realtime(stock_id: str, dl: DataLoader):
    """
    實戰升級版：計算外資均線黃金交叉，並加入「外資買超佔總成交量比率 > 15%」的關鍵純度過濾
    """
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")
    
    FAST_MA = 5
    SLOW_MA = 20
    VOLUME_RATIO_THRESHOLD = 0.15  # 門檻設定：外資淨買超需佔當日總量 15% 以上

    try:
        # 1. 抓取法人籌碼數據
        chip_data = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date, end_date=end_date)
        if chip_data is None or len(chip_data) == 0:
            return 'ERROR', f"⚠️ 查無股票代碼 {stock_id} 的法人數據。"
            
        df_chip = pd.DataFrame(chip_data)
        df_chip['date'] = pd.to_datetime(df_chip['date'])
        
        df_foreign = df_chip[df_chip['name'] == 'Foreign_Investor'].copy()
        if df_foreign.empty:
            return 'ERROR', f"⚠️ 股票 {stock_id} 未找到外資數據。"
            
        df_foreign = df_foreign.sort_values('date').set_index('date')
        df_foreign['f_net'] = pd.to_numeric(df_foreign['buy']) - pd.to_numeric(df_foreign['sell'])
        
        # 2. 抓取個股總成交量（K線資料），用來計算佔比
        k_data = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
        if k_data is None or len(k_data) == 0:
            return 'ERROR', f"⚠️ 查無股票代碼 {stock_id} 的總成交量數據。"
            
        df_k = pd.DataFrame(k_data)
        df_k['date'] = pd.to_datetime(df_k['date'])
        df_k = df_k.sort_values('date').set_index('date')
        
        # 3. 合併籌碼與成交量
        df_merged = pd.merge(df_foreign[['f_net']], df_k[['Trading_Volume']], left_index=True, right_index=True, how='inner')
        
        # 計算外資淨買賣超佔當日成交量的比例
        df_merged['volume_ratio'] = df_merged['f_net'] / df_merged['Trading_Volume']
        
        # 計算外資籌碼均線
        df_merged['inst_fastma'] = df_merged['f_net'].rolling(FAST_MA).mean()
        df_merged['inst_slowma'] = df_merged['f_net'].rolling(SLOW_MA).mean()
        
        df_merged.dropna(subset=['inst_fastma', 'inst_slowma', 'volume_ratio'], inplace=True)
        
        if len(df_merged) < 21:
            return 'ERROR', f"⚠️ 股票 {stock_id} 資料不足 21 天，無法列印完整驗算明細。"

        last_21_days = df_merged.tail(21)
        
        history_lines = []
        for idx, row in last_21_days.iterrows():
            date_str = idx.strftime('%Y-%m-%d')
            is_latest = " (最新)" if idx == last_21_days.index[-1] else ""
            # 呈現外資買賣超與佔總成交量的百分比
            history_lines.append(f"   📅 【{date_str}】外資買賣超: {row['f_net']:+,} 股 (佔總量: {row['volume_ratio']:.2%}){is_latest}")
        
        history_log_str = "\n".join(history_lines)

        # 取得交叉判定所需數值
        latest_data = last_21_days.iloc[-1]
        yesterday_data = last_21_days.iloc[-2]
        
        fast_today = latest_data['inst_fastma']
        slow_today = latest_data['inst_slowma']
        fast_yesterday = yesterday_data['inst_fastma']
        slow_yesterday = yesterday_data['inst_slowma']
        ratio_today = latest_data['volume_ratio']

        # 組裝詳細日誌
        log_msg = (
            f"📊 股票代碼: {stock_id} | 盤後高純度籌碼追蹤\n"
            f"{history_log_str}\n"
            f"   --------------------------------------------------\n"
            f"   最新外資 5MA: {fast_today:,.2f} | 20MA: {slow_today:,.2f}\n"
            f"   今日外資買超佔比: {ratio_today:.2%} (精選門檻: {VOLUME_RATIO_THRESHOLD:.0%})\n"
            f"   前日外資 5MA: {fast_yesterday:,.2f} | 20MA: {slow_yesterday:,.2f}"
        )

        # 判斷黃金交叉與死亡交叉 (進場點額外加上外資買超佔比過濾)
        is_gold_cross = (fast_today > slow_today) and (fast_yesterday <= slow_yesterday)
        is_death_cross = (fast_today < slow_today) and (fast_yesterday >= slow_yesterday)

        if is_gold_cross:
            if ratio_today >= VOLUME_RATIO_THRESHOLD:
                return 'BUY', log_msg
            else:
                # 雖然黃金交叉，但外資買得不夠多，判定為虛胖盤，不發動攻擊
                return 'HOLD', log_msg + f"\n   ⚠️ 提示：雖觸發黃金交叉，但外資買超佔比僅 {ratio_today:.2%}，未達 {VOLUME_RATIO_THRESHOLD:.0%} 門檻，放棄進場。"
        elif is_death_cross:
            return 'SELL', log_msg
        else:
            return 'HOLD', log_msg

    except Exception as e:
        return 'ERROR', f"❌ 股票 {stock_id} 執行失敗: {e}"


# ==========================================
# 3. 核心功能函式
# ==========================================
def run_scanner():
    buy_list = []
    sell_list = []
    keypoints = []

    dl = DataLoader()

    print(f"🚀 啟動高純度籌碼波段掃描（加入 15% 外資成交量佔比過濾）...")
    print("=" * 60)

    for stock in stock_list:
        status, message = check_stock_signal_realtime(stock, dl)
        print(message)
        
        if status == 'BUY':
            buy_list.append(stock)
            print(f"📈 實戰提示：股票 {stock} 最新籌碼【高純度黃金交叉】！請於【明天開盤】進場做多。")
            keypoints.append(message)
        elif status == 'SELL':
            sell_list.append(stock)
            print(f"📉 實戰提示：股票 {stock} 最新籌碼【死亡交叉】！請於【明天開盤】立即出場。")
            keypoints.append(message)
        elif status == 'HOLD':
            print(f"🔍 實戰提示：股票 {stock} 未達進場標準或維持原趨勢，明早開盤不需動作。")
            
        print("=" * 60)
        time.sleep(0.5)

    print("\n" + "🌟" * 10 + " 符合買賣訊號個股・高純度籌碼驗算明細總整理 " + "🌟" * 10 + "\n")
    for detail_msg in keypoints:
        print(detail_msg)
        print("-" * 60)
        
    print("\n🏁 今日高純度籌碼掃描完畢！")
    print("🌟 ================= 明日開盤操作指引清單 =================")
    
    if buy_list:
        print(f"📈 【💡 明早開盤 務必進場做多】共有 {len(buy_list)} 檔：")
        print(f"    ➡️  " + ", ".join(buy_list))
    else:
        print("📈 【明早開盤 做多清單】：目前無股票觸發高純度黃金交叉。")
        
    print("-" * 58)
    
    if sell_list:
        print(f"📉 【⚠️ 明早開盤 務必立即出場】共有 {len(sell_list)} 檔：")
        print(f"    ➡️  " + ", ".join(sell_list))
    else:
        print("📉 【明早開盤 出場清單】：目前無股票觸發死亡交叉。")
        
    print("==========================================================")

    # 最終決策總結輸出至 Discord
    lines = [
        f"🏁 今日盤後【高純度外資籌碼】掃描完畢！",
        f"🌟 ================= 明日開盤操作指引清單 ================="
    ]
    
    if buy_list:
        lines.append(f"📈 【💡 明早開盤 務必進場做多】共有 {len(buy_list)} 檔 (交叉且外資量佔比 > 15%)：")
        lines.append(f"    ➡️  " + ", ".join(buy_list))
    else:
        lines.append("📈 【明早開盤 做多清單】：目前無股票觸發高純度黃金交叉。")
        
    lines.append("==========================================================")
    
    if sell_list:
        lines.append(f"📉 【⚠️ 明早開盤 務必立即出場】共有 {len(sell_list)} 檔：")
        lines.append(f"    ➡️  " + ", ".join(sell_list))
    else:
        lines.append("📉 【明早開盤 出場清單】：目前無股票觸發死亡交叉。")
        
    lines.append("==========================================================")
    
    content = "\n".join(lines)
        
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    except Exception as e:
        print(f"Discord 報告傳送失敗: {e}")


if __name__ == "__main__":
    run_scanner()

