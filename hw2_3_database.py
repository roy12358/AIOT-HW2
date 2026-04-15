# ============================================================
# HW2-3: 將氣溫資料儲存到 SQLite3 資料庫
# 資料庫：data.db   資料表：TemperatureForecasts
# ============================================================

import os
import sqlite3
from hw2_2_extract import load_weather_data, extract_temperatures
from hw2_1_fetch import fetch_weather_forecast, save_json

DB_NAME    = "data.db"
TABLE_NAME = "TemperatureForecasts"


# ── 建立資料庫與資料表 ─────────────────────────────────────
def create_table(conn: sqlite3.Connection) -> None:
    """建立 TemperatureForecasts 資料表（若已存在則略過）。"""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT    NOT NULL,
            dataDate   TEXT    NOT NULL,
            mint       INTEGER NOT NULL,
            maxt       INTEGER NOT NULL
        )
    """)
    conn.commit()
    print(f"[HW2-3] 資料表 [{TABLE_NAME}] 建立完成（或已存在）")


# ── 插入資料 ───────────────────────────────────────────────
def insert_temperatures(conn: sqlite3.Connection, temperatures: list[dict]) -> None:
    """
    將提取的縣市氣溫資料聚合為六大地區後存入資料庫。
    同一地區、同一時間段取所有縣市的氣溫平均值。
    """
    # 清空舊資料，確保每次執行結果乾淨
    conn.execute(f"DELETE FROM {TABLE_NAME}")

    # 按 (regionName, dataDate) 聚合
    aggregated: dict[tuple, dict] = {}
    for t in temperatures:
        key = (t["regionName"], t["dataDate"])
        if key not in aggregated:
            aggregated[key] = {"mint_list": [], "maxt_list": []}
        aggregated[key]["mint_list"].append(t["mint"])
        aggregated[key]["maxt_list"].append(t["maxt"])

    rows = [
        (
            region,
            date,
            round(sum(v["mint_list"]) / len(v["mint_list"])),
            round(sum(v["maxt_list"]) / len(v["maxt_list"])),
        )
        for (region, date), v in aggregated.items()
    ]

    conn.executemany(
        f"INSERT INTO {TABLE_NAME} (regionName, dataDate, mint, maxt) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    print(f"[HW2-3] 成功插入 {len(rows)} 筆資料")


# ── 查詢驗證 ───────────────────────────────────────────────
def verify_database(conn: sqlite3.Connection) -> None:
    """執行兩道查詢，確認資料已正確寫入。"""
    cursor = conn.cursor()

    # 查詢 1：列出所有地區名稱
    print("\n" + "=" * 60)
    print("【查詢 1：列出所有地區名稱】")
    print("=" * 60)
    cursor.execute(f"SELECT DISTINCT regionName FROM {TABLE_NAME} ORDER BY regionName")
    for (region,) in cursor.fetchall():
        print(f"  • {region}")

    # 查詢 2：中部地區氣溫資料
    print("\n" + "=" * 60)
    print("【查詢 2：中部地區的氣溫資料】")
    print("=" * 60)
    cursor.execute(f"""
        SELECT id, regionName, dataDate, mint, maxt
        FROM   {TABLE_NAME}
        WHERE  regionName = '中部'
        ORDER  BY dataDate
    """)
    rows = cursor.fetchall()
    header = f"{'ID':<5}  {'地區':<6}  {'時間':<22}  {'最低溫(°C)':<12}  {'最高溫(°C)':<12}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row[0]:<5}  {row[1]:<6}  {row[2]:<22}  {row[3]:<12}  {row[4]:<12}")

    # 查詢 3：各地區筆數確認
    print("\n" + "=" * 60)
    print("【查詢 3：各地區資料筆數】")
    print("=" * 60)
    cursor.execute(f"""
        SELECT regionName, COUNT(*) as cnt
        FROM   {TABLE_NAME}
        GROUP  BY regionName
        ORDER  BY regionName
    """)
    for region, cnt in cursor.fetchall():
        print(f"  {region:<6} : {cnt} 筆")


# ── 主程式 ──────────────────────────────────────────────────
if __name__ == "__main__":
    # 準備資料
    if not os.path.exists("weather_data.json"):
        print("[HW2-3] 重新呼叫 API 取得資料...")
        save_json(fetch_weather_forecast())

    raw_data = load_weather_data()
    temperatures = extract_temperatures(raw_data)

    # 操作資料庫
    with sqlite3.connect(DB_NAME) as conn:
        create_table(conn)
        insert_temperatures(conn, temperatures)
        verify_database(conn)

    print(f"\n[HW2-3] 完成！資料庫檔案：{DB_NAME}")
