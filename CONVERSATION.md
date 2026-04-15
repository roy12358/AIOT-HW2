# HW2 開發對話摘要

本文件摘錄開發過程中與 AI 助手（Claude）的主要對話紀錄，記錄需求決策與問題解決過程。

---

## 資料架構決策

**Q：資料要以六大地區聚合，還是保留各縣市？**

> 我們的是各縣市資料好像不用硬分到6大區域

**決策**：改為儲存 22 縣市原始資料（66 筆），DB `regionName` 欄位直接存縣市名稱，移除聚合邏輯。

---

## 地圖互動設計

**Q：22 縣市同時顯示在地圖上感覺很亂，有沒有更好的方式？**

> 若是像之前一樣聚合大區域點開在展開對應縣市會不會比較好？現在好像有點亂

**決策**：改為兩層互動設計：
- **預設**：顯示六大地區聚合圓圈
- **點擊地區**：zoom in，展開顯示該地區各縣市圓圈
- **點擊縣市**：選取，更新 KPI / 折線圖 / 表格
- **「◀ 全台」**按鈕或點擊其他地區淡化圓圈可返回

---

## API Key 安全

**Q：API 有沒有洩漏？**

發現 `hw2_1_fetch.py` 中 API Key 直接硬編碼並已推上 GitHub。

**修正**：
- 改從 `st.secrets["CWA_API_KEY"]` 或環境變數讀取
- `.streamlit/secrets.toml` 加入 `.gitignore`，本地 key 不納入版控
- Streamlit Cloud 在 Settings → Secrets 填入 key

---

## 視覺問題修正記錄

| 問題 | 根因 | 解法 |
|------|------|------|
| 側欄文字看不到 | CSS 注入選擇器被 Streamlit 內部樣式覆蓋 | 改用 `.streamlit/config.toml` 設定 `textColor` |
| 地圖圓圈不顯示 | `prefer_canvas=True` 干擾 DivIcon HTML 渲染 | 移除該參數 |
| Cloud 部署後地圖空白 | `width=None` 在雲端無法偵測容器寬度 | 改用 `use_container_width=True` |
| Cloud 還顯示舊六大地區資料 | 舊 DB 持久化，不觸發重建 | 啟動時檢測地區名稱，自動重建縣市版 DB |
| dropdown 選項背景色異常 | popover 渲染為 portal，在 sidebar DOM 之外 | 全域 CSS 選擇器 `li[role="option"]` |

---

## 部署

- **平台**：Streamlit Cloud
- **Live Demo**：[https://aiot-hw2-zhbpvcebxjznujmr6h3t7e.streamlit.app/](https://aiot-hw2-zhbpvcebxjznujmr6h3t7e.streamlit.app/)
- 首次啟動自動呼叫 CWA API 建立資料庫，無需手動初始化
