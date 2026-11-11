# ⚡ 能量不平衡掃描器 (Volume & Momentum Scanner)

本專案是一個基於 `yfinance` 的自動化台美股量能監控腳本。透過每日定時掃描市場數據，篩選出符合「**爆量收紅**」的動能標的，並自動將符合條件的結果透過 **Discord Webhook** 發送通知。

---

## 📌 策略核心邏輯 (Strategy Rules)

### 📈 進場條件 (Entry Rules)
1. **量能異常**：當日成交量 ≥ 2 倍的昨日成交量 (`Volume_t > 2 * Volume_t-1`)。
2. **K棒方向**：收紅 K 線 (`Close > Open`)。

### 🛡️ 明日出場機制 (Exit Rules)
1. **成本守護**：若盤中跌破「今日收盤價（進場價）」，立即執行出清。
2. **慣性守護**：若開盤即轉黑（低於開盤價），立即撤退。

---

## 🚀 功能特色

* **自動抓取數據**：使用 `yfinance` 批量獲取多檔標的之歷史日 K 棒資料。
* **即時篩選計算**：自動計算量增倍數、漲跌幅與 K 棒型態。
* **Discord 警報推播**：整合 Webhook，自動排版發送強勢股清單與絕對防守位。
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

