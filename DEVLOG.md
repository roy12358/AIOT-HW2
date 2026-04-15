# HW2 Development Log

## 專案概覽
台灣氣溫預報 Web App，使用 CWA（中央氣象署）開放資料平台 API，
呈現台灣 22 縣市的 36 小時天氣預報，包含兩層互動地圖、折線圖、長條圖與資料表。

**技術棧**：Python 3.13 · requests · SQLite3 · pandas · plotly · folium · Streamlit

---

## 2026-04-15 — HW2-1：API 資料抓取

### 目標
使用 `requests` 呼叫 CWA F-C0032-001 API，取得台灣 22 縣市未來 36 小時天氣預報。

### 實作
- `fetch_weather_forecast()` 回傳完整 JSON dict
- `save_json()` 存檔至 `weather_data.json` 供後續步驟讀取
- API Key 從 `st.secrets["CWA_API_KEY"]` 或環境變數讀取，不硬編碼在程式中

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
- `get_region()` 根據縣市名稱回傳所屬六大地區（供內部分類參考）
- `extract_temperatures()` 逐縣市配對 MinT/MaxT，輸出結構化 list of dict
- 每筆包含 `countyName`、`regionName`、`dataDate`、`mint`、`maxt`
- 結果存至 `temperatures.json`，共 22 縣市 × 3 時間段 = 66 筆

---

## 2026-04-15 — HW2-3：SQLite3 資料庫

### 目標
建立 `data.db`，資料表 `TemperatureForecasts`，以縣市為單位儲存氣溫資料。

### 資料表 Schema
```sql
CREATE TABLE TemperatureForecasts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT    NOT NULL,   -- 縣市名稱
    dataDate   TEXT    NOT NULL,   -- 時間段起始時間
    mint       INTEGER NOT NULL,   -- 最低氣溫 (°C)
    maxt       INTEGER NOT NULL    -- 最高氣溫 (°C)
)
```

### 實作
- `insert_temperatures()` 直接存入各縣市原始資料，不做地區聚合
- 每次執行先 `DELETE` 舊資料，確保結果乾淨
- 寫入後執行三道驗證查詢：縣市列表、臺北市詳細資料、各縣市筆數

### 結果
22 個縣市 × 3 個時間段 = 66 筆資料

---

## 2026-04-15 ～ 2026-04-16 — HW2-4：Streamlit Web App

### 目標
建立互動式 Web App，包含：縣市 dropdown、互動地圖、折線圖、長條圖、資料表。

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
# 以座標距離判斷點擊到哪個地區
```

**問題**：
- `st.session_state.region_select` 在 selectbox 渲染後被修改 → `StreamlitAPIException`
- 側欄文字不可見（深藍文字在淺藍背景上對比不足）

---

#### v3 — Session State 修正
**問題根因**：地圖點擊後直接設定 `st.session_state.county_select`，但此時 selectbox widget 已渲染完畢。

**解法**：`pending_county` 中介變數，在 script 頂端、widget 渲染前套用：
```python
if st.session_state.pending_county:
    st.session_state.county_select = st.session_state.pending_county
    st.session_state.pending_county = None
# → 然後才渲染 st.selectbox(key="county_select")
```

---

#### v4 — 主題與視覺優化

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
- 被選中縣市：大圓（56px）+ 藍色邊框 + 光暈 box-shadow
- 未選中縣市：小圓（44px）+ 白色邊框
- 白色粗體文字 + `text-shadow` 提升可讀性

**Layout 架構**：
```
Header Banner
[KPI: 縣市 | 最高均溫 | 最低均溫 | 日夜溫差]
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

#### v5 — 縣市層級化

原本以六大地區聚合儲存（18 筆），改為直接儲存各縣市原始資料（66 筆）。

- DB `insert_temperatures()` 移除聚合邏輯，改存 `countyName`
- App dropdown 改為 22 縣市；地圖加入 `COUNTY_INFO`（22 縣市座標）
- 長條圖、摘要表改以縣市為單位顯示
- `prefer_canvas=True` 導致 DivIcon HTML 不渲染，移除後恢復正常

**雲端資料版本遷移**：
Cloud 上若 DB 為舊版（含「北部」等地區名），啟動時自動重建：
```python
def _needs_init():
    names = {r[0] for r in conn.execute("SELECT DISTINCT regionName ...")}
    return bool(names & {"北部", "中部", "南部", ...})
```

---

#### v6 — 兩層互動地圖（最終版）

22 縣市圓圈同時顯示在地圖上視覺混亂，改為兩層互動設計：

**地區總覽模式**（預設）：
- 顯示六大地區聚合圓圈（60-72px）
- 點擊地區 → 切換至縣市展開模式

**縣市展開模式**：
- `folium.Map.fit_bounds()` 縮放至該地區範圍
- 顯示該地區各縣市圓圈（44-56px）
- 其他五個地區以淡化小圓（40px, opacity 0.45）顯示，可點擊切換
- 「◀ 全台」按鈕返回地區總覽

**側欄與地圖同步**：
從 dropdown 選取縣市時，`map_expanded_region` 自動更新為對應地區，地圖即時展開。
