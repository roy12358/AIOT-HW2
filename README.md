# HW2 — 台灣氣溫預報 Web App

使用中央氣象署（CWA）開放資料平台 API，呈現台灣六大地區未來 36 小時氣溫預報的互動式儀表板。

## 功能

- **互動地圖** — folium 地圖顯示六大地區溫度圓圈，點擊即切換地區（顏色：🔵 涼 → 🔴 熱）
- **氣溫趨勢折線圖** — 所選地區的最高/最低溫走勢，含填色溫差區間
- **全台溫度對比長條圖** — 六大地區平均溫度並排比較
- **詳細資料表** — 所選地區各時間段數據
- **全台摘要表** — 一眼掌握各地區溫差
- **📡 更新天氣資料** — 一鍵重新呼叫 API 取得最新預報

## 專案結構

```
hw2/
├── hw2_1_fetch.py          # HW2-1：呼叫 CWA API，存 weather_data.json
├── hw2_2_extract.py        # HW2-2：解析 JSON，提取 MinT/MaxT
├── hw2_3_database.py       # HW2-3：存入 SQLite3 data.db
├── hw2_4_app.py            # HW2-4：Streamlit Web App（主程式）
├── requirements.txt        # Python 相依套件
├── .streamlit/
│   └── config.toml         # Streamlit 主題設定
└── DEVLOG.md               # 開發日誌
```

## 本地執行

### 1. 安裝相依套件
```bash
pip install -r requirements.txt
```

### 2. 初始化資料庫
```bash
python hw2_3_database.py
```
> 若 `weather_data.json` 不存在，會自動呼叫 CWA API 取得資料。

### 3. 啟動 App
```bash
streamlit run hw2_4_app.py
```

瀏覽器開啟 `http://localhost:8501`

> **注意**：CWA SSL 憑證在 Windows Python 3.13 上有相容問題，`hw2_1_fetch.py` 使用 `verify=False` 繞過，屬已知限制。

## Streamlit Cloud 部署

1. Fork 或 clone 此 repo 至你的 GitHub
2. 前往 [share.streamlit.io](https://share.streamlit.io)，選擇此 repo
3. Main file path 填入：`hw2_4_app.py`
4. 點擊 **Deploy**

首次啟動時 App 會自動呼叫 CWA API 初始化資料庫，無需手動執行任何腳本。

## API 說明

| 項目 | 說明 |
|------|------|
| 資料集 | CWA `F-C0032-001`（台灣未來 36 小時天氣預報） |
| 來源 | [中央氣象署開放資料平台](https://opendata.cwa.gov.tw) |
| 更新頻率 | 每 6 小時更新一次（App 快取 5 分鐘） |

## 六大地區對應

| 地區 | 涵蓋縣市 |
|------|---------|
| 北部 | 臺北市、新北市、基隆市、桃園市、新竹市、新竹縣 |
| 中部 | 苗栗縣、臺中市、彰化縣、南投縣、雲林縣 |
| 南部 | 嘉義市、嘉義縣、臺南市、高雄市、屏東縣、澎湖縣 |
| 東北部 | 宜蘭縣 |
| 東部 | 花蓮縣、臺東縣 |
| 東南部 | 金門縣、連江縣 |

## 資料庫 Schema

```sql
CREATE TABLE TemperatureForecasts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT    NOT NULL,   -- 地區名稱
    dataDate   TEXT    NOT NULL,   -- 時間段起始時間
    mint       INTEGER NOT NULL,   -- 最低溫 (°C)，縣市平均
    maxt       INTEGER NOT NULL    -- 最高溫 (°C)，縣市平均
);
```
