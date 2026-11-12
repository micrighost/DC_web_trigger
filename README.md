# 📈 DC Web Trigger — 台股自動化掃描與 Discord 推播系統

這是一個基於 **FastAPI** 建構的常駐型 Web 觸發服務。透過發送 HTTP 請求至指定端點（Endpoint），即可在伺服器背景非同步執行多組台股技術面與籌碼面掃描策略，並將篩選結果自動推播至指定的 Discord 頻道。

---

## 📁 專案目錄結構

本專案採用「策略獨立資料夾」結構，每個策略的程式碼、測試檔與專屬說明文件皆集中於同名資料夾內：

```text
DC_web_trigger/
├── trigger.py                              # FastAPI 主程式與 API 路由入口
├── requirements.txt                        # Python 套件相依清單
├── .env                                    # 本地環境變數設定（不上傳至 Git）
├── .env.example                            # 環境變數範本檔
├── README.md                               # 專案總覽說明文件（本檔案）
│
├── onepush_breakout/                       # 【策略】突破型態掃描
│   ├── onepush_breakout.py
│   ├── onepush_breakout_test.py
│   └── onepush_breakout_README.md
│
├── onepush_abnormal_volume/                # 【策略】異常爆量掃描
│   ├── onepush_abnormal_volume.py
│   ├── onepush_abnormal_volume_test.py
│   └── onepush_abnormal_volume_README.md
│
├── onepush_legal_person/                   # 【策略】法人籌碼動向掃描
│   ├── onepush_legal_person.py
│   ├── onepush_legal_person_test.py
│   └── onepush_legal_person_README.md
│
├── onepush_Volume_Price_Velocity/          # 【策略】量價動能速度掃描
│   ├── onepush_Volume_Price_Velocity.py
│   ├── onepush_Volume_Price_Velocity_test.py
│   └── onepush_Volume_Price_Velocity_README.md
│
├── onepush_Volume_Price_Velocity_10d/      # 【策略】10 日量價動能速度掃描
│   ├── onepush_Volume_Price_Velocity_10d.py
│   ├── onepush_Volume_Price_Velocity_10d_test.py
│   └── onepush_Volume_Price_Velocity_10d_README.md
│
├── down_fractal_reversal/                  # 【策略】底分型反轉監控
│   ├── down_fractal_reversal.py
│   └── down_fractal_reversal_README.md
│
└── volume_alert/                           # 【策略】即時成交量警示
    ├── volume_alert.py
    └── volume_alert_README.md
```

---

## 📚 策略模組索引

點擊下方連結可直接查閱各策略的詳細篩選邏輯與參數說明：

| 策略資料夾 | 執行類型 | 說明文件連結 |
| :--- | :--- | :--- |
| `onepush_breakout` | 單次觸發推播 | [查看說明](./onepush_breakout/onepush_breakout_README.md) |
| `onepush_abnormal_volume` | 單次觸發推播 | [查看說明](./onepush_abnormal_volume/onepush_abnormal_volume_README.md) |
| `onepush_legal_person` | 單次觸發推播 | [查看說明](./onepush_legal_person/onepush_legal_person_README.md) |
| `onepush_Volume_Price_Velocity` | 單次觸發推播 | [查看說明](./onepush_Volume_Price_Velocity/onepush_Volume_Price_Velocity_README.md) |
| `onepush_Volume_Price_Velocity_10d` | 單次觸發推播 | [查看說明](./onepush_Volume_Price_Velocity_10d/onepush_Volume_Price_Velocity_10d_README.md) |
| `down_fractal_reversal` | 型態反轉監控 | [查看說明](./down_fractal_reversal/down_fractal_reversal_README.md) |
| `volume_alert` | 即時量能警示 | [查看說明](./volume_alert/volume_alert_README.md) |

---

## ⚙️ 環境變數設定

1. 複製專案根目錄下的 `.env.example` 並重新命名為 `.env`。
2. 填入你的 Discord Webhook 網址與觀察標的名單（注意等號兩側勿留空格）：

```env
DISCORD_WEBHOOK_URL=你的_DISCORD_WEBHOOK_網址
TICKERS=2330.TW,2317.TW,2454.TW
```

---

## 🚀 本機開發與啟動方式

### 1. 安裝相依套件
建議先建立並啟動虛擬環境（`.venv`），再執行安裝指令：

```bash
pip install -r requirements.txt
```

### 2. 啟動常駐 Web 服務
於專案根目錄的終端機執行以下指令（請保持終端機視窗開啟）：

```bash
python trigger.py
```

服務啟動後，預設監聽於 `http://127.0.0.1:8000`。


---

## ☁️ 雲端部署注意事項（Render）

若要將本服務部署至 **Render (Web Service)**，請確認以下設定：

1. **修改監聽位址（Host）**：
   將 `trigger.py` 最底部的 `host` 由本機測試用的 `127.0.0.1` 改為 `0.0.0.0`，以允許外部網路連線：
   ```python
   uvicorn.run("trigger:app", host="0.0.0.0", port=cloud_port, reload=False)
   ```



