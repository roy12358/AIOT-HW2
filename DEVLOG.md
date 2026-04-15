# HW2 Development Log

## 專案概覽
台灣氣溫預報 Web App，使用 CWA（中央氣象署）開放資料平台 API，
呈現台灣六大地區的 36 小時天氣預報，包含互動式地圖、折線圖、長條圖與資料表。

**技術棧**：Python 3.13 · requests · SQLite3 · pandas · plotly · folium · Streamlit

---

## 2026-04-15 — HW2-1：API 資料抓取

### 目標
使用 `requests` 呼叫 CWA F-C0032-001 API，取得台灣 22 縣市未來 36 小時天氣預報。

### 實作
- 定義 `REGION_COUNTIES` 對應表，將 22 縣市分為六大地區（北/中/南/東北/東/東南部）
- `fetch_weather_forecast()` 回傳完整 JSON dict
- `save_json()` 存檔至 `weather_data.json` 供後續步驟讀取

### 遭遇問題
**SSL Certificate Error**
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
```
CWA 的 SSL 憑證在 Windows Python 3.13 上驗證失敗。

**解法**：`requests.get(..., verify=False)` + `urllib3.disable_warnings(InsecureRequestWarning)`

---

## 2026-04-15 — HW2-2：JSON 解析與資料提取

### 目標
從 `weather_data.json` 解析 CWA 資料結構，提取各縣市各時間段的 MinT / MaxT。

### CWA JSON 結構
```
records.location[]
  ├─ locationName          # 縣市名
  └─ weatherElement[]
       ├─ elementName      # "MinT" / "MaxT" / "Wx" / "PoP" / "CI"
       └─ time[]
            ├─ startTime
            ├─ endTime
            └─ parameter.parameterName   # 溫度數值（字串）
```

### 實作
- `get_region()` 根據縣市名稱回傳所屬地區
- `extract_temperatures()` 逐縣市配對 MinT/MaxT，輸出結構化 list of dict
- 結果存至 `temperatures.json`，共 3 個時間段 × 22 縣市 = 66 筆

---

## 2026-04-15 — HW2-3：SQLite3 資料庫

### 目標
建立 `data.db`，資料表 `TemperatureForecasts`，儲存地區層級的聚合氣溫。

### 資料表 Schema
```sql
CREATE TABLE TemperatureForecasts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT    NOT NULL,
    dataDate   TEXT    NOT NULL,
    mint       INTEGER NOT NULL,
    maxt       INTEGER NOT NULL
)
```

### 實作
- 以 (regionName, dataDate) 為 key 聚合：取同地區所有縣市的 mint/maxt 平均值
- 每次執行先 `DELETE` 舊資料，確保結果乾淨
- 寫入後執行三道驗證查詢：地區列表、中部詳細資料、各地區筆數

### 結果
6 個地區 × 3 個時間段 = 18 筆資料

---

## 2026-04-15 ～ 2026-04-16 — HW2-4：Streamlit Web App

### 目標
建立互動式 Web App，包含：地區 dropdown、互動地圖、折線圖、長條圖、資料表。

### 版本演進

#### v1 — 初版
- 基本 Streamlit layout：sidebar selectbox + Plotly 折線圖 + st.dataframe
- Plotly Scattermapbox 顯示地圖點位

**問題**：地圖標記文字重疊、Scattermapbox 點擊事件不可靠

---

#### v2 — 地圖互動改良
改用 **folium + streamlit-folium**，以 `DivIcon` 自訂 HTML 標記。

**地圖點擊事件機制**：
```python
map_data = st_folium(taiwan_map, returned_objects=["last_object_clicked"])
# 以座標距離 < 0.25° 判斷點擊到哪個地區
```

**問題**：
- `st.session_state.region_select` 在 selectbox 渲染後被修改 → `StreamlitAPIException`
- 側欄文字不可見（深藍文字在淺藍背景上對比不足）

---

#### v3 — Session State 修正
**問題根因**：地圖點擊後直接設定 `st.session_state.region_select`，但此時 selectbox widget 已渲染完畢。

**解法**：`pending_region` 中介變數，在 script 頂端、widget 渲染前套用：
```python
if st.session_state.pending_region:
    st.session_state.region_select = st.session_state.pending_region
    st.session_state.pending_region = None
# → 然後才渲染 st.selectbox(key="region_select")
```

---

#### v4 — 主題與視覺優化（最終版）

**側欄文字問題根本修法**：
Streamlit CSS 注入無法穩定覆蓋 sidebar 樣式（選擇器優先權被 Streamlit 內部 CSS 覆蓋）。
改用 `.streamlit/config.toml` 在 framework 層設定：
```toml
[theme]
base            = "light"
primaryColor    = "#1E40AF"
backgroundColor = "#F0F4FF"
secondaryBackgroundColor = "#FFFFFF"
textColor       = "#1E3A8A"
font            = "sans serif"
```

**地圖標記重設計**：
- `temp_gradient()` 計算溫度對應的 CSS `linear-gradient`（涼藍 → 熱紅）
- 被選中地區：大圓（64px）+ 藍色邊框 + 光暈 box-shadow
- 未選中地區：小圓（52px）+ 白色邊框
- 白色粗體文字 + `text-shadow` 提升可讀性
- tooltip hover 顯示最高/最低溫與涵蓋縣市

**Layout 重構（三列式）**：
```
Header Banner
[KPI: 地區 | 最高均溫 | 最低均溫 | 日夜溫差]
[地圖 (50%)] [折線圖 (50%)]
[詳細表格 (40%)] [全台長條圖 (60%)]
[全台摘要表]
```

**Dropdown 選項白底修正**：
Streamlit 的 dropdown popover 渲染為 portal（超出 sidebar DOM），
sidebar-scoped CSS 無法套用，需全域選擇器：
```css
li[role="option"] { background: white !important; color: #1E3A8A !important; }
```

**pandas 3.0 相容性**：
`DataFrame.style.applymap()` 在 pandas 3.0 已移除，改用 `.map()`

---

## 部署

```bash
# 安裝相依套件
pip install -r requirements.txt

# 初始化資料庫（需有 weather_data.json 或可存取 CWA API）
python hw2_3_database.py

# 啟動 App
streamlit run hw2_4_app.py
```

### 檔案說明
| 檔案 | 說明 |
|------|------|
| `hw2_1_fetch.py` | HW2-1：呼叫 CWA API，存 `weather_data.json` |
| `hw2_2_extract.py` | HW2-2：解析 JSON，提取 MinT/MaxT |
| `hw2_3_database.py` | HW2-3：存入 SQLite3 `data.db` |
| `hw2_4_app.py` | HW2-4：Streamlit Web App |
| `requirements.txt` | Python 相依套件 |
| `.streamlit/config.toml` | Streamlit 主題設定 |

### 注意事項
- CWA SSL 憑證在 Windows Python 3.13 有相容問題，`hw2_1_fetch.py` 使用 `verify=False`
- `data.db` 與 `weather_data.json` 為執行期產生檔案，不納入版本控制
