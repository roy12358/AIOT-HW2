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
    從 F-D0047-091 JSON 中提取每縣市「未來一週、每日」的最高 / 最低氣溫。

    CWA 一週預報 JSON 結構（重點欄位）：
      records
        └─ Locations[0]                  # 整包資料，LocationsName = "台灣"
             └─ Location[]               # 22 個縣市
                  ├─ LocationName        # 縣市名，例如「臺中市」
                  └─ WeatherElement[]
                       ├─ ElementName    # "最高溫度" / "最低溫度" / "天氣現象" …
                       └─ Time[]         # 14 段（每段 12 小時，共約 7 天）
                            ├─ StartTime # 例如 "2026-06-09T12:00:00+08:00"
                            ├─ EndTime
                            └─ ElementValue[0]
                                 └─ MaxTemperature / MinTemperature  # 溫度字串

    原始資料是 12 小時一段（日 / 夜），這裡依日期彙整成「每日」：
      該日最高溫 = 當日各段最高溫的最大值
      該日最低溫 = 當日各段最低溫的最小值
    回傳：每縣市約 7 筆，每筆含 regionName, countyName, dataDate, mint, maxt
    """
    records = []

    for location in data["records"]["Locations"][0]["Location"]:
        county_name = location["LocationName"]
        region_name = get_region(county_name)

        # 找出「最高溫度」與「最低溫度」兩個 element 的時間序列
        maxt_times, mint_times = [], []
        for element in location["WeatherElement"]:
            if element["ElementName"] == "最高溫度":
                maxt_times = element["Time"]
            elif element["ElementName"] == "最低溫度":
                mint_times = element["Time"]

        # 依「日期」彙整各 12 小時時段（StartTime 前 10 碼 = YYYY-MM-DD）
        daily: dict[str, dict] = {}
        for maxt_t, mint_t in zip(maxt_times, mint_times):
            day = maxt_t["StartTime"][:10]            # "2026-06-09"
            try:
                maxv = int(maxt_t["ElementValue"][0]["MaxTemperature"])
                minv = int(mint_t["ElementValue"][0]["MinTemperature"])
            except (ValueError, KeyError, IndexError):
                continue                              # 跳過缺值（CWA 偶爾回傳 "-"）
            d = daily.setdefault(day, {"maxt": maxv, "mint": minv})
            d["maxt"] = max(d["maxt"], maxv)
            d["mint"] = min(d["mint"], minv)

        # 依日期排序後輸出每日一筆
        for day in sorted(daily):
            records.append({
                "regionName": region_name,
                "countyName":  county_name,
                "dataDate":    day,                   # "2026-06-09"
                "mint":        daily[day]["mint"],
                "maxt":        daily[day]["maxt"],
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
