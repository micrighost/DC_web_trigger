import os

from fastapi import FastAPI, BackgroundTasks
import uvicorn

# 使用「from 資料夾名稱 import 檔案名稱」
# 依分類匯入所有策略模組
# 【單次推播類】
from onepush_breakout import onepush_breakout
from onepush_abnormal_volume import onepush_abnormal_volume
from onepush_Volume_Price_Velocity import onepush_Volume_Price_Velocity
from onepush_Volume_Price_Velocity_10d import onepush_Volume_Price_Velocity_10d

# 【5分鐘高頻類】
from min5push_down_fractal_reversal import min5push_down_fractal_reversal
from min5push_volume_alert import min5push_volume_alert

# 【盤後定時類】
from afterpush_legal_person import afterpush_legal_person


app = FastAPI()



# ==========================================
# 🎯 任務區塊一：單次推播任務 (One-push)
# ==========================================
def run_onepush_tasks():
    print("\n🚀 [單次推播] 股票掃描開始執行...")
    onepush_breakout.run_scanner()
    # onepush_abnormal_volume.run_scanner()
    # onepush_Volume_Price_Velocity.run_scanner()
    # onepush_Volume_Price_Velocity_10d.run_scanner()
    print("🎉 [單次推播] 股票掃描與 Discord 發送完畢。")


# ==========================================
# ⚡ 任務區塊二：盤中 5 分鐘高頻任務 (Min5-push)
# ==========================================
def run_min5push_tasks():
    print("\n⚡ [5分K推播] 盤中高頻掃描開始執行...")
    min5push_down_fractal_reversal.run_spring_radar()
    # min5push_volume_alert.run_scanner()
    print("✅ [5分K推播] 盤中掃描與 Discord 發送完畢。")


# ==========================================
# 🌙 任務區塊三：盤後定時總結任務 (After-push)
# ==========================================
def run_afterpush_tasks():
    print("\n🌙 [盤後推播] 盤後籌碼與總結掃描開始執行...")
    afterpush_legal_person.run_scanner()
    print("🎉 [盤後推播] 盤後報告與 Discord 發送完畢。")

@app.get("/")
def home():
    return {
        "status": "系統正常運作中，請在網址後面加上對應路徑來觸發股票掃描：",
        "endpoints": {
            "/scan/onepush": "手動觸發單次推播掃描",
            "/scan/5m": "盤中每 5 分鐘高頻掃描",
            "/scan/after": "盤後定時總結與籌碼掃描"
        }
    }


@app.get("/scan/onepush")
def trigger_onepush(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_onepush_tasks)
    return {
        "status": "指令已接收",
        "type": "onepush 單次掃描",
        "msg": "單次掃描程式已在伺服器背景啟動，跑完會直接發送至 Discord，您可以直接關閉網頁了！"
    }

@app.get("/scan/5m")
def trigger_min5push(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_min5push_tasks)
    return {
        "status": "指令已接收",
        "type": "min5push 盤中5分K掃描",
        "msg": "5 分鐘高頻掃描已在背景啟動，如果有掃描到就會傳到 Discord，否則您可以直接關閉網頁五分鐘再來了！"
    }

@app.get("/scan/after")
def trigger_afterpush(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_afterpush_tasks)
    return {
        "status": "指令已接收",
        "type": "afterpush 盤後籌碼掃描",
        "msg": "盤後籌碼掃描已在背景啟動，跑完會直接發送至 Discord，您可以直接關閉網頁了！"
    }

# ==========================================
# 🎯 🎯 調整二：動態適應 Render 的開門暗號 ($PORT)
# ==========================================
if __name__ == "__main__":
    # Render 規定在雲端上必須自動抓取官方給的隨機 $PORT，本機執行則維持預設 8000
    cloud_port = int(os.getenv("PORT", 8000))
    
    # 這裡的 reload 維持 False (預防 Windows 衝突)，host 改為 0.0.0.0 讓外網可以連進來
    uvicorn.run("trigger:app", host="127.0.0.1", port=cloud_port, reload=False)
