# ============================================================
# HW2-1: 獲取天氣預報資料
# 使用 CWA API (F-C0032-001) 獲取台灣各縣市未來天氣預報
# ============================================================

import os
import requests
import json
import urllib3

# CWA 憑證在 Windows Python 3.13 有相容問題，暫時略過 SSL 驗證
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# CWA API 設定
# 優先從環境變數或 Streamlit Secrets 讀取；本地開發可在 .streamlit/secrets.toml 設定
try:
    import streamlit as st
    API_KEY = st.secrets["CWA_API_KEY"]
except Exception:
    API_KEY = os.environ.get("CWA_API_KEY", "")
BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
DATASET_ID = "F-C0032-001"   # 鄉鎮天氣預報－台灣未來 36 小時天氣預報

# 台灣六大地區縣市對應表
REGION_COUNTIES = {
    "北部":  ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣"],
    "中部":  ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
    "南部":  ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣", "澎湖縣"],
    "東北部": ["宜蘭縣"],
    "東部":  ["花蓮縣", "臺東縣"],
    "東南部": ["金門縣", "連江縣"],
}


def fetch_weather_forecast() -> dict:
    """
    調用 CWA API 獲取台灣各縣市天氣預報資料。
    回傳值為完整的 JSON 資料字典。
    """
    url = f"{BASE_URL}/{DATASET_ID}"
    params = {
        "Authorization": API_KEY,
        "format": "JSON",
    }

    print(f"[HW2-1] 正在調用 CWA API...")
    print(f"        URL     : {url}")
    print(f"        Dataset : {DATASET_ID}")

    response = requests.get(url, params=params, timeout=30, verify=False)
    response.raise_for_status()

    data = response.json()
    print(f"[HW2-1] 調用成功！success = {data.get('success')}")
    return data


def save_json(data: dict, filepath: str = "weather_data.json") -> None:
    """將原始資料存入 JSON 檔案以供後續步驟使用。"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[HW2-1] 原始資料已儲存至 {filepath}")


# ── 主程式 ──────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. 獲取資料
    weather_data = fetch_weather_forecast()

    # 2. 用 json.dumps 觀察完整資料結構（只印前 3000 字元避免洗版）
    print("\n" + "=" * 60)
    print("【原始 JSON 資料（節錄前 3000 字元）】")
    print("=" * 60)
    json_str = json.dumps(weather_data, ensure_ascii=False, indent=2)
    print(json_str[:3000])
    print("...\n（完整資料請見 weather_data.json）")

    # 3. 列出資料重點統計
    locations = weather_data["records"]["location"]
    print("\n" + "=" * 60)
    print("【資料結構分析】")
    print("=" * 60)
    print(f"總縣市數量  : {len(locations)}")

    first = locations[0]
    elements = [e["elementName"] for e in first["weatherElement"]]
    time_periods = len(first["weatherElement"][0]["time"])
    print(f"第一筆縣市  : {first['locationName']}")
    print(f"天氣要素    : {elements}")
    print(f"時間段數量  : {time_periods} 段")
    print(f"\n各時間段起訖：")
    for t in first["weatherElement"][0]["time"]:
        print(f"  {t['startTime']}  →  {t['endTime']}")

    # 4. 存檔供後續步驟讀取
    save_json(weather_data)
