# HW2 開發對話摘要

本文件摘錄開發過程中與 AI 助手（Claude）的主要對話紀錄，記錄需求決策與問題解決過程。

---

## 初始需求

**Q：作業規格**

> 作業分四個子任務：
> HW2-1 用 requests 抓 CWA API 資料
> HW2-2 解析 JSON 取出 MinT/MaxT
> HW2-3 存入 SQLite3
> HW2-4 Streamlit 視覺化，要有地圖、要帥一點

**決策**：使用 CWA F-C0032-001 資料集（36 小時縣市天氣預報），地圖使用 folium。

---

## API Key 取得

**Q：我註冊好了，但沒看到申請 API？**（附 CWA 網站截圖）

> 說明：CWA 開放資料平台帳號申請後，API Key 在「會員中心」→「我的 API 金鑰」取得。

**後續**：使用者提供 API Key，設定完成後開始開發。

---

## HW2-1 開發問題

**問題：SSL Certificate Error**
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
```
CWA 的 SSL 憑證在 Windows Python 3.13 環境驗證失敗。

**解法**：`requests.get(..., verify=False)` + `urllib3.disable_warnings(InsecureRequestWarning)`

---

## HW2-4 UI 迭代過程

### 第一版反饋

> 有些字都看不到，另外地圖中圓圈是啥

**問題 1：側欄文字不可見**
深藍色文字（`#1E3A8A`）與淺藍背景（`#F0F4FF`）對比不足，CSS 注入又被 Streamlit 內部樣式覆蓋。

**問題 2：地圖圓圈用途不明**
初版使用 Plotly Scattermapbox，圓點只是座標標記，沒有溫度資訊也不可互動。

---

### 第二版反饋

> 地圖切換沒成功，只有圖標有變，資料沒變

**根因**：地圖點擊後直接設定 `st.session_state.region_select`，但此時 selectbox widget 已渲染完畢，觸發 `StreamlitAPIException`。

**解法**：`pending_county` 中介變數，在 script 頂端、widget 渲染前套用：
```python
if st.session_state.pending_county:
    st.session_state.county_select = st.session_state.pending_county
    st.session_state.pending_county = None
# → 然後才渲染 st.selectbox(key="county_select")
```

地圖同步從 Plotly Scattermapbox 改為 **folium + streamlit-folium**，以座標距離判斷點擊目標，使用 `DivIcon` 自訂 HTML 標記。

---

### 第三版反饋

> 側欄配色再調一下，另外地圖希望互動性高一點。除此之外你覺得要加個按鈕可以重抓 API 更新資料嗎？

**側欄問題**：多次嘗試 CSS 注入均失效（Streamlit portal 渲染機制），最終改用 `.streamlit/config.toml` 在 framework 層設定 `textColor`。

**地圖互動強化**：DivIcon 改為溫度漸層圓圈（涼藍 → 熱紅），selected 縣市顯示大圓 + 光暈。

**更新資料按鈕**：決定加入，一鍵重抓 CWA API → 重建 DB → 清除快取。

---

### 第四版反饋

> 地圖還是一樣，側欄字還是不清楚

**地圖問題根因**：`prefer_canvas=True` 導致 DivIcon HTML 不渲染（canvas 模式不支援 HTML 標記）。移除後恢復正常。

**側欄文字**：`config.toml` 設定 `textColor = "#1E3A8A"` 終於生效，框架層覆蓋優先。

---

### 第五版反饋

> 側欄還是很糟 / 地圖一切換就崩潰了，而且變超醜

**崩潰根因**：地圖切換觸發 session_state 修改時機問題，與 selectbox key 衝突。`pending_county` 機制補強。

**視覺重構**：整體 Layout 改為三列式，KPI 卡片列、地圖＋折線圖、詳細表＋長條圖、全台摘要表。字型引入 Inter + Fira Code。

---

### 第六版反饋（部署前）

> 側欄還是看不到字，地圖圖標可以調漂亮一點嗎，另外整體布局再優化一下

**最終修法**：三個問題在同一版完整解決：
1. `config.toml` 確認生效 → 側欄文字正常
2. 地圖標記改為 CSS `linear-gradient` 溫度漸層圓圈
3. Layout 精調完成

---

## 部署過程問題

**Q：部署後地圖空白**

**根因**：`width=None` 在 Streamlit Cloud 無法自動偵測容器寬度。
**解法**：改為 `use_container_width=True`

**Q：部署後下拉還是舊的六大地區名稱**

**根因**：Cloud 上舊 DB 持久化，不觸發重建。
**解法**：啟動時偵測地區名稱，若含「北部/中部…」等舊版資料則自動重建：
```python
def _needs_init():
    names = {r[0] for r in conn.execute("SELECT DISTINCT regionName ...")}
    return bool(names & {"北部", "中部", "南部", ...})
```

---

## 資料架構決策

**Q：資料要以六大地區聚合，還是保留各縣市？**

> 我們的是各縣市資料好像不用硬分到6大區域

**決策**：改為儲存 22 縣市原始資料（66 筆），DB `regionName` 欄位直接存縣市名稱，移除聚合邏輯。

---

## 地圖互動設計決策

**Q：22 縣市同時顯示感覺很亂，有沒有更好的方式？**

> 若是像之前一樣聚合大區域點開在展開對應縣市會不會比較好？現在好像有點亂

**決策**：改為兩層互動設計：
- **預設**：顯示六大地區聚合圓圈（60-72px）
- **點擊地區**：`fit_bounds()` 縮放，展開顯示該地區各縣市（44-56px）
- **點擊縣市**：選取，更新 KPI / 折線圖 / 表格
- **「◀ 全台」**按鈕或點擊其他地區淡化圓圈（40px, opacity 0.45）可返回

---

## API Key 安全

**Q：API 有沒有洩漏？**

發現 `hw2_1_fetch.py` 中 API Key 直接硬編碼並已推上 GitHub。

**修正**：
- 改從 `st.secrets["CWA_API_KEY"]` 或環境變數讀取
- `.streamlit/secrets.toml` 加入 `.gitignore`，本地 key 不納入版控
- Streamlit Cloud 在 Settings → Secrets 填入 key

---

## 問題修正速查表

| 問題 | 根因 | 解法 |
|------|------|------|
| SSL 憑證錯誤 | Windows Python 3.13 與 CWA 憑證不相容 | `verify=False` + `disable_warnings` |
| 地圖點擊資料不更新 | session_state 在 widget 渲染後修改 | `pending_county` 中介變數 |
| 側欄文字看不到 | CSS 注入被 Streamlit 內部樣式覆蓋 | `.streamlit/config.toml` textColor |
| 地圖圓圈不顯示 | `prefer_canvas=True` 不支援 DivIcon HTML | 移除 prefer_canvas |
| Cloud 地圖空白 | `width=None` 無法偵測容器寬度 | `use_container_width=True` |
| Cloud 顯示舊資料 | 舊 DB 持久化不觸發重建 | 啟動時檢測地區名稱自動重建 |
| Dropdown 背景色異常 | popover 渲染為 portal，在 sidebar DOM 之外 | 全域 CSS `li[role="option"]` |
| pandas applymap 錯誤 | pandas 3.0 移除 applymap | 改用 `.map()` |
| API Key 暴露 | 硬編碼在程式碼中 | 改用 st.secrets / 環境變數 |
