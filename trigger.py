import os

from fastapi import FastAPI, BackgroundTasks
import uvicorn

import onepush_breakout
import onepush_abnormal_volume
import onepush_Volume_Price_Velocity_10d
import onepush_Volume_Price_Velocity


app = FastAPI()



def run_my_code():
    print("\n🚀 [背景任務] 股票掃描開始執行...")


    onepush_breakout.run_scanner()
    onepush_abnormal_volume.run_scanner()
    onepush_Volume_Price_Velocity_10d.run_scanner()
    onepush_Volume_Price_Velocity.run_scanner()

    
    print("🎉 [背景任務] 股票掃描與 Discord 發送完畢。")

@app.get("/")
def home():
    return {"status": "正常運作中，請在網址後面加上 /scan 來觸發股票掃描。"}

@app.get("/scan")
def scan(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_my_code)
    return {
        "status": "指令已接收",
        "msg": "掃描程式已在伺服器背景啟動，跑完會直接發送至 Discord，您可以直接關閉網頁了！"
    }

# ==========================================
# 🎯 🎯 調整二：動態適應 Render 的開門暗號 ($PORT)
# ==========================================
if __name__ == "__main__":
    # Render 規定在雲端上必須自動抓取官方給的隨機 $PORT，本機執行則維持預設 8000
    cloud_port = int(os.getenv("PORT", 8000))
    
    # 這裡的 reload 維持 False (預防 Windows 衝突)，host 改為 0.0.0.0 讓外網可以連進來
    uvicorn.run("trigger:app", host="127.0.0.1", port=cloud_port, reload=False)
