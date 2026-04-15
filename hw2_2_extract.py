# ============================================================
# HW2-2: 分析資料，提取最高與最低氣溫
# 從 weather_data.json 中解析 MinT / MaxT，並對應到六大地區
# ============================================================

import json
from hw2_1_fetch import fetch_weather_forecast, save_json, REGION_COUNTIES


def load_weather_data(filepath: str = "weather_data.json") -> dict:
    """從本地 JSON 檔案載入天氣預報資料。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_region(county_name: str) -> str:
    """根據縣市名稱回傳所屬六大地區；找不到則回傳「其他」。"""
    for region, counties in REGION_COUNTIES.items():
        if county_name in counties:
            return region
    return "其他"


def extract_temperatures(data: dict) -> list[dict]:
    """
    從 F-C0032-001 JSON 中提取每縣市、每時間段的最高 / 最低氣溫。

    CWA JSON 結構（重點欄位）：
      records
        └─ location[]
             ├─ locationName          # 縣市名
             └─ weatherElement[]
                  ├─ elementName      # "MinT" / "MaxT" / "Wx" / "PoP" / "CI"
                  └─ time[]
                       ├─ startTime
                       ├─ endTime
                       └─ parameter
                            └─ parameterName   # 溫度數值（字串）

    回傳：每筆包含 regionName, countyName, dataDate, endTime, mint, maxt
    """
    records = []

    for location in data["records"]["location"]:
        county_name = location["locationName"]
        region_name = get_region(county_name)

        # 找出 MinT 與 MaxT 兩個 element
        mint_times, maxt_times = [], []
        for element in location["weatherElement"]:
            if element["elementName"] == "MinT":
                mint_times = element["time"]
            elif element["elementName"] == "MaxT":
                maxt_times = element["time"]

        # 逐時間段配對提取
        for mint_t, maxt_t in zip(mint_times, maxt_times):
            records.append({
                "regionName": region_name,
                "countyName":  county_name,
                "dataDate":    mint_t["startTime"],
                "endTime":     mint_t["endTime"],
                "mint":        int(mint_t["parameter"]["parameterName"]),
                "maxt":        int(maxt_t["parameter"]["parameterName"]),
            })

    return records


# ── 主程式 ──────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. 嘗試從本地檔案載入；若不存在則重新呼叫 API
    import os
    if not os.path.exists("weather_data.json"):
        print("[HW2-2] weather_data.json 不存在，重新呼叫 API...")
        raw = fetch_weather_forecast()
        save_json(raw)
    else:
        print("[HW2-2] 載入 weather_data.json...")
        raw = load_weather_data()

    # 2. 提取最高 / 最低氣溫
    print("[HW2-2] 開始提取 MinT / MaxT 資料...")
    temperatures = extract_temperatures(raw)

    # 3. 用 json.dumps 觀察提取結果
    print("\n" + "=" * 60)
    print("【提取結果（前 6 筆）】")
    print("=" * 60)
    print(json.dumps(temperatures[:6], ensure_ascii=False, indent=2))

    # 4. 統計摘要
    print("\n" + "=" * 60)
    print("【統計摘要】")
    print("=" * 60)
    print(f"總筆數   : {len(temperatures)}")
    regions = sorted(set(t["regionName"] for t in temperatures))
    print(f"地區列表 : {regions}")

    for region in regions:
        subset = [t for t in temperatures if t["regionName"] == region]
        avg_mint = sum(t["mint"] for t in subset) / len(subset)
        avg_maxt = sum(t["maxt"] for t in subset) / len(subset)
        print(f"  {region:<5} → 平均最低 {avg_mint:.1f}°C，平均最高 {avg_maxt:.1f}°C（共 {len(subset)} 筆）")

    # 5. 存檔
    with open("temperatures.json", "w", encoding="utf-8") as f:
        json.dump(temperatures, f, ensure_ascii=False, indent=2)
    print("\n[HW2-2] 提取結果已儲存至 temperatures.json")
