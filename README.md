# HW2 — 台灣氣溫預報 Web App

**Live Demo：[https://aiot-hw2-zhbpvcebxjznujmr6h3t7e.streamlit.app/](https://aiot-hw2-zhbpvcebxjznujmr6h3t7e.streamlit.app/)**

[開發日誌 →](DEVLOG.md)　·　[對話摘要 →](CONVERSATION.md)

---

## 作業說明

本作業分為四個子任務，使用中央氣象署（CWA）開放資料平台 API，完成從資料抓取、解析、儲存到視覺化呈現的完整流程。

### HW2-1：獲取天氣預報資料

使用 `requests` 呼叫 CWA Open Data API（資料集 `F-C0032-001`），取得台灣 22 縣市未來 36 小時天氣預報 JSON 資料，並儲存至本地 `weather_data.json`。

- API 端點：`https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001`
- 每筆資料包含：天氣現象（Wx）、降雨機率（PoP）、最低氣溫（MinT）、舒適度（CI）、最高氣溫（MaxT）
- 共 3 個時間段（每段 12 小時），涵蓋未來 36 小時

**程式：** `hw2_1_fetch.py`

---

### HW2-2：分析資料，提取最高與最低氣溫

解析 HW2-1 取得的 JSON，從各縣市各時間段提取 MinT / MaxT 數值。

- 使用 `json.dumps` 觀察原始資料結構
- 輸出結構化資料存至 `temperatures.json`（22 縣市 × 3 時間段 = 66 筆）

**程式：** `hw2_2_extract.py`

---

### HW2-3：將氣溫資料儲存到 SQLite3 資料庫

將 HW2-2 提取的各縣市氣溫存入 SQLite3 資料庫 `data.db`。

**資料表：** `TemperatureForecasts`

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | INTEGER | 主鍵（自動遞增） |
| regionName | TEXT | 縣市名稱 |
| dataDate | TEXT | 時間段起始時間 |
| mint | INTEGER | 最低氣溫（°C） |
| maxt | INTEGER | 最高氣溫（°C） |

執行後以三道 SQL 查詢驗證寫入結果：縣市列表、臺北市詳細資料、各縣市筆數。

**程式：** `hw2_3_database.py`

---

### HW2-4：Streamlit 視覺化 Web App

以 Streamlit 建立互動式儀表板，從 SQLite3 讀取資料並呈現以下內容：

| 元件 | 說明 |
|------|------|
| 側欄 Dropdown | 選擇 22 縣市 |
| KPI 卡片列 | 縣市名稱、平均最高溫、平均最低溫、日夜溫差 |
| 互動地圖 | folium 兩層互動：點擊地區展開縣市 → 點擊縣市選取資料 |
| 折線圖 | 所選縣市 36 小時最高 / 最低溫趨勢 |
| 詳細資料表 | 所選縣市各時間段數據 |
| 長條圖 | 全台 22 縣市平均溫度並排比較 |
| 全台摘要表 | 各縣市均溫與極值一覽 |

**程式：** `hw2_4_app.py`

---

## 專案結構

```
hw2/
├── hw2_1_fetch.py          # HW2-1：呼叫 CWA API
├── hw2_2_extract.py        # HW2-2：解析 JSON，提取 MinT/MaxT
├── hw2_3_database.py       # HW2-3：存入 SQLite3
├── hw2_4_app.py            # HW2-4：Streamlit Web App
├── requirements.txt        # Python 相依套件
├── .streamlit/
│   └── config.toml         # Streamlit 主題設定（secrets.toml 不納入版控）
├── DEVLOG.md               # 開發日誌
└── CONVERSATION.md         # 開發對話摘要
```

---

**資料來源：** [中央氣象署開放資料平台](https://opendata.cwa.gov.tw)（資料集 F-C0032-001）
