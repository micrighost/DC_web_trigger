# 📊 量價速率掃描器 (10D Structure Overtake Scanner)

本專案是一個基於 `yfinance` 的自動化量價速率監控腳本。透過計算 10 日移動平均的價格與產值速率（P-Line / V-Line），動態篩選出符合「**首度超車、趨勢向上、拒絕追高**」的蓄勢爆發標的，並自動將篩選結果透過 **Discord Webhook** 發送通知。

---

## 📌 策略核心邏輯 (Strategy Rules)

### 📈 進場條件 (Entry Rules)
1. **首度超車**：今日 10 日均量變化率（V-Line）大於 10 日均價變化率（P-Line），且昨日未發生超車（黃金交叉起漲點）。
   - 今日：`V-Line_t > P-Line_t`
   - 昨日：`V-Line_t-1 <= P-Line_t-1`
2. **趨勢向上**：10 日均價變化率（P-Line）大於 0%，確認均價結構處於上揚階段。
   - `P-Line > 0%`
3. **拒絕追高（蓄勢區）**：P-Line 小於或等於 1.5%，有效過濾過度噴出、有追高風險的標的。
   - `P-Line <= 1.5%`
4. **型態確認**：當日必須收紅 K 線 (`Close > Open`)。

### 🛡️ 明日出場機制 (Exit Rules)
1. **成本守護**：若盤中跌破「今日收盤價（進場價）」，代表動能未能延續，立即執行出清。
2. **慣性守護**：若明日開盤即轉黑（低於開盤價），多頭慣性消失，立即撤退。

---

## 🚀 功能特色

* **量價動態速率計算**：以 10 日價格均線與 10 日成交量均線的斜率/變化率作為判斷基準（P-Line / V-Line）。
* **終端機細節診斷**：即時輸出每檔標的最近 3 日的 10D 平均序列與詳細比對總表，便於盤後檢視。
* **Discord 警報推播**：整合 Webhook，自動進行 5 檔一組的批量分流排版，並清晰標示鋼鐵防守價位。
* **空值防護**：當日若無符合標的，也會發送友善的「無符合標的」狀態報告。

---

## ⚙️ 環境變數設定 (Environment Variables)

在執行腳本前，請確保在系統或 `.env` 中設定以下環境變數：

| 變數名稱 | 說明 | 範例格式 |
| :--- | :--- | :--- |
| `DISCORD_WEBHOOK_URL` | 用於接收通知的 Discord 頻道 Webhook 網址 | `https://discord.com...` |
| `TICKERS` | 欲掃描的股票代號清單（以逗號分隔） | `2330.TW,2317.TW,AAPL,TSLA` |

> ⚠️ **台股特別注意**：若要掃描台股，股票代號後方**必須加上 `.TW` 或 `.TWO`**（例如：`2330.TW`、`3105.TWO`），否則 `yfinance` 將無法正確抓取。

---

## 📦 依賴套件 (Requirements)

請先安裝 Python 必要套件：

```bash
pip install yfinance pandas numpy requests
```

---

## ▶️ 如何執行 (Usage)

程式最底下的run_scanner()註釋要打開
如果要掛到trigger.py來統一PUSH要註釋掉run_scanner()：

```bash
# run_scanner()
```
設定好後，直接執行主程式即可：

```bash
python your_script_name.py
```