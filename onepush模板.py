"""
這是最簡單的DC訊息推送模板
把想要推送到DC的東西包到run_scanner裡面，並填好DISCORD_WEBHOOK_URL，執行就可以推送了
"""

import requests
import os

# ==========================================
# 1. 基本設定區
# ==========================================
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


# ==========================================
# 2. 核心功能函式
# ==========================================



def run_scanner():
    """執行程式區塊"""

    content = "測試要推送的訊息"
       
                
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    except Exception as e:
        print(f"空值報告傳送失敗: {e}")


run_scanner()


