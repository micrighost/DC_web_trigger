"""
這是最簡單的API模板
啟動後連上http://127.0.0.1:8000，因為是根目錄，
所以會顯示正常運作中，請在網址後面加上 /scan 來觸發股票掃描。

連上http://127.0.0.1:8000/scan，因為是/scan分支，所以會啟動run_my_code裡面寫的程式
並顯示"status": "指令已接收",
    "msg": "掃描程式已在伺服器背景啟動，跑完會直接發送至 Discord，您可以直接關閉網頁了！"
"""

from fastapi import FastAPI, BackgroundTasks
import os
import uvicorn

app = FastAPI()


def run_my_code():
    print("\n🚀 [背景任務] 股票掃描開始執行...")
    

    
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
# 🎯 加上下面這兩行，你就可以像一般 Python 檔案一樣直接執行了！
# ==========================================
if __name__ == "__main__":
    uvicorn.run("觸發器範例:app", host="127.0.0.1", port=8000, reload=True)
