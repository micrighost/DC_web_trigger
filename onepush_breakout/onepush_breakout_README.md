# ⚡ 能量慣性掃描器 (ATR Volatility & Momentum Scanner)

本專案是一個基於 `yfinance` 的自動化台美股動能監控腳本。透過每日定時掃描市場數據，篩選出符合「**波動爆發、強勢實體、量能背書**」的強勢股標的，並自動將符合條件的結果透過 **Discord Webhook** 發送通知。

---

## 📌 策略核心邏輯 (Strategy Rules)

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

---

## 🚀 功能特色

* **自動抓取數據**：使用 `yfinance` 批量獲取多檔標的之 60 日歷史日 K 棒資料，並自動計算 14 日 ATR 與 20 日均量。
* **即時篩選計算**：自動計算 ATR 倍數、K 棒實體比例、量增倍數與漲跌幅。
* **Discord 警報推播**：整合 Webhook，自動進行 5 檔一組的批量分流排版，並發送強勢股清單與絕對防守位。
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

直接執行主程式即可：

```bash
python your_script_name.py
```