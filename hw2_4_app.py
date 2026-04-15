# ============================================================
# HW2-4: 台灣氣溫預報 Web App  (Final)
# ============================================================

import os
import sqlite3

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

DB_NAME    = "data.db"
TABLE_NAME = "TemperatureForecasts"

REGION_INFO = {
    "北部":  {"lat": 25.05, "lon": 121.52, "counties": "臺北・新北・基隆・桃園・新竹"},
    "中部":  {"lat": 24.15, "lon": 120.68, "counties": "苗栗・臺中・彰化・南投・雲林"},
    "南部":  {"lat": 22.65, "lon": 120.35, "counties": "嘉義・臺南・高雄・屏東・澎湖"},
    "東北部": {"lat": 24.75, "lon": 121.75, "counties": "宜蘭縣"},
    "東部":  {"lat": 23.85, "lon": 121.55, "counties": "花蓮・臺東"},
    "東南部": {"lat": 22.35, "lon": 120.90, "counties": "金門・連江"},
}


# ── DB helpers ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all() -> pd.DataFrame:
    with sqlite3.connect(DB_NAME) as c:
        return pd.read_sql_query(
            f"SELECT * FROM {TABLE_NAME} ORDER BY regionName, dataDate", c)

@st.cache_data(ttl=300)
def load_region(region: str) -> pd.DataFrame:
    with sqlite3.connect(DB_NAME) as c:
        return pd.read_sql_query(
            f"SELECT * FROM {TABLE_NAME} WHERE regionName=? ORDER BY dataDate",
            c, params=(region,))

@st.cache_data(ttl=300)
def get_regions() -> list[str]:
    with sqlite3.connect(DB_NAME) as c:
        return [r[0] for r in c.execute(
            f"SELECT DISTINCT regionName FROM {TABLE_NAME} ORDER BY regionName")]

def region_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("regionName")
            .agg(avg_mint=("mint","mean"), avg_maxt=("maxt","mean"),
                 min_mint=("mint","min"), max_maxt=("maxt","max"))
            .reset_index())


# ── 溫度→漸層色 (藍→紅) ─────────────────────────────────────
def temp_color(t: float, lo=15.0, hi=35.0) -> str:
    p = max(0.0, min(1.0, (t - lo) / (hi - lo)))
    # 冷：#3B82F6 → 暖：#EF4444
    r = int(59  + p * 177)
    g = int(130 - p * 62)
    b = int(246 - p * 178)
    return f"#{r:02x}{g:02x}{b:02x}"

def temp_gradient(t: float) -> str:
    """回傳 CSS linear-gradient 字串"""
    base = temp_color(t)
    # 稍深一點當 gradient 結束色
    p = max(0.0, min(1.0, (t - 15) / 20))
    r2 = int(20  + p * 160)
    g2 = int(100 - p * 60)
    b2 = int(200 - p * 150)
    dark = f"#{r2:02x}{g2:02x}{b2:02x}"
    return f"linear-gradient(135deg, {base} 0%, {dark} 100%)"


# ── 地圖標記 HTML ────────────────────────────────────────────
def marker_html(region: str, maxt: float, mint: float, is_sel: bool) -> str:
    grad   = temp_gradient(maxt)
    w      = 64 if is_sel else 52
    ring   = (f"box-shadow:0 0 0 4px rgba(30,64,175,0.25),"
              f"0 4px 20px rgba(0,0,0,0.3);" if is_sel else
              f"box-shadow:0 2px 10px rgba(0,0,0,0.2);")
    border = "border:3px solid #1E40AF;" if is_sel else "border:2px solid rgba(255,255,255,0.8);"
    fsize  = 12 if is_sel else 10
    tsize  = 10 if is_sel else 9
    return (
        f'<div style="width:{w}px;height:{w}px;border-radius:50%;background:{grad};'
        f'{border}{ring}'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        f'cursor:pointer;transition:transform .15s;">'
        f'<span style="font-size:{fsize}px;font-weight:900;color:white;'
        f'text-shadow:0 1px 3px rgba(0,0,0,.7);line-height:1.2;">{region}</span>'
        f'<span style="font-size:{tsize}px;font-weight:700;color:rgba(255,255,255,.9);'
        f'text-shadow:0 1px 2px rgba(0,0,0,.6);">{mint:.0f}°~{maxt:.0f}°</span>'
        f'</div>'
    )


# ── Folium 台灣地圖 ──────────────────────────────────────────
def build_map(df_all: pd.DataFrame, selected: str) -> folium.Map:
    summ = region_summary(df_all)
    m = folium.Map(location=[23.7, 121.0], zoom_start=7,
                   tiles="CartoDB positron", prefer_canvas=True)

    # 隱藏 zoom control（讓地圖更乾淨）
    m.options["zoomControl"] = False

    for _, row in summ.iterrows():
        region = row["regionName"]
        info   = REGION_INFO.get(region)
        if not info:
            continue
        maxt   = float(row["avg_maxt"])
        mint   = float(row["avg_mint"])
        is_sel = (region == selected)
        w      = 64 if is_sel else 52

        tooltip_html = (
            f"<div style='font-family:sans-serif;min-width:130px;'>"
            f"<b style='font-size:15px;color:#1E40AF'>{region}</b><hr style='margin:4px 0'>"
            f"🌡 最高：<b style='color:#DC2626'>{maxt:.1f}°C</b><br>"
            f"❄️ 最低：<b style='color:#2563EB'>{mint:.1f}°C</b><br>"
            f"<small style='color:#64748B'>{info['counties']}</small></div>"
        )

        folium.Marker(
            location=[info["lat"], info["lon"]],
            icon=folium.DivIcon(
                html=marker_html(region, maxt, mint, is_sel),
                icon_size=(w, w),
                icon_anchor=(w // 2, w // 2),
            ),
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
        ).add_to(m)

    return m


# ── 折線圖 ────────────────────────────────────────────────────
def build_line(df: pd.DataFrame, region: str) -> go.Figure:
    def fmt(s):
        p = str(s).split(" ")
        return f"{p[0][5:].replace('-','/')} {p[1][:5]}" if len(p)==2 else s
    labels = [fmt(t) for t in df["dataDate"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=df["mint"], name="最低氣溫",
        mode="lines+markers",
        line=dict(color="#3B82F6", width=3),
        marker=dict(size=10, color="#3B82F6", line=dict(color="white", width=2)),
        fill="tozeroy", fillcolor="rgba(59,130,246,0.07)",
        hovertemplate="最低：%{y}°C<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=df["maxt"], name="最高氣溫",
        mode="lines+markers",
        line=dict(color="#EF4444", width=3),
        marker=dict(size=10, color="#EF4444", line=dict(color="white", width=2)),
        fill="tonexty", fillcolor="rgba(239,68,68,0.08)",
        hovertemplate="最高：%{y}°C<extra></extra>",
    ))
    for i, row in df.reset_index(drop=True).iterrows():
        fig.add_annotation(x=labels[i], y=row["maxt"]+0.7,
            text=f"<b>{row['maxt']}°</b>", showarrow=False,
            font=dict(size=12, color="#DC2626"))
        fig.add_annotation(x=labels[i], y=row["mint"]-0.9,
            text=f"<b>{row['mint']}°</b>", showarrow=False,
            font=dict(size=12, color="#1D4ED8"))
    fig.update_layout(
        plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#E9EEF6",
                   tickfont=dict(size=11, color="#64748B")),
        yaxis=dict(showgrid=True, gridcolor="#E9EEF6", ticksuffix="°",
                   tickfont=dict(size=11, color="#64748B")),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=12)),
        margin=dict(l=40, r=10, t=40, b=40), height=300,
    )
    return fig


# ── 長條圖 ────────────────────────────────────────────────────
def build_bar(df_all: pd.DataFrame, selected: str) -> go.Figure:
    s = region_summary(df_all)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=s["regionName"], y=s["avg_maxt"], name="平均最高",
        marker_color=["#1E40AF" if r==selected else "#93C5FD"
                      for r in s["regionName"]],
        text=[f"{v:.1f}°" for v in s["avg_maxt"]],
        textposition="outside", textfont=dict(size=10),
        hovertemplate="%{x} 最高：%{y:.1f}°C<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=s["regionName"], y=s["avg_mint"], name="平均最低",
        marker_color=["#D97706" if r==selected else "#FCD34D"
                      for r in s["regionName"]],
        text=[f"{v:.1f}°" for v in s["avg_mint"]],
        textposition="outside", textfont=dict(size=10),
        hovertemplate="%{x} 最低：%{y:.1f}°C<extra></extra>",
    ))
    fig.update_layout(
        barmode="group", plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#334155")),
        yaxis=dict(showgrid=True, gridcolor="#E9EEF6", ticksuffix="°"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    font=dict(size=11)),
        margin=dict(l=30, r=10, t=30, b=30), height=250,
    )
    return fig


# ── CSS ──────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* Header */
.hdr {
  background: linear-gradient(135deg,#1E40AF 0%,#2563EB 60%,#3B82F6 100%);
  border-radius:16px; padding:20px 28px; margin-bottom:20px;
  display:flex; align-items:center; gap:16px;
  box-shadow:0 4px 24px rgba(30,64,175,.3);
}
.hdr h1 {
  color:white !important; font-family:'Fira Code',monospace !important;
  font-size:1.55rem !important; margin:0 !important;
}
.hdr .sub { color:rgba(255,255,255,.78); font-size:.82rem; margin-top:3px; }

/* KPI row */
.kpi-wrap { display:flex; gap:14px; margin-bottom:18px; }
.kpi {
  flex:1; background:white; border-radius:14px;
  padding:16px 20px; border-top:4px solid #3B82F6;
  box-shadow:0 2px 10px rgba(30,64,175,.07);
  transition:transform .15s,box-shadow .15s;
}
.kpi:hover { transform:translateY(-2px); box-shadow:0 6px 18px rgba(30,64,175,.13); }
.kpi.amb  { border-top-color:#D97706; }
.kpi-lbl  { font-size:.72rem; color:#64748B; font-weight:600;
             text-transform:uppercase; letter-spacing:.06em; margin-bottom:6px; }
.kpi-val  { font-family:'Fira Code',monospace; font-size:1.8rem; font-weight:700; line-height:1.1; }
.kpi-val.r  { color:#DC2626; }
.kpi-val.b  { color:#1E40AF; }
.kpi-val.i  { color:#4338CA; }
.kpi-val.a  { color:#B45309; }

/* Section card */
.card {
  background:white; border-radius:14px; padding:18px;
  box-shadow:0 2px 10px rgba(30,64,175,.07);
  border:1px solid #E2EAFF; height:100%;
}
.card-title {
  font-family:'Fira Code',monospace; font-size:.78rem; font-weight:700;
  color:#1E40AF; text-transform:uppercase; letter-spacing:.07em;
  padding-bottom:10px; border-bottom:2px solid #DBEAFE; margin-bottom:12px;
}

/* Folium map container: 移除預設白底 */
.folium-map { border-radius:10px; overflow:hidden; }

/* ── Dropdown 選項白底（全域）── */
div[data-baseweb="popover"] > div { background:white !important; }
ul[data-baseweb="menu"], [data-baseweb="menu"] ul { background:white !important; }
li[role="option"]              { background:white !important; color:#1E3A8A !important; }
li[role="option"]:hover        { background:#EFF6FF !important; }
li[aria-selected="true"]       { background:#DBEAFE !important;
                                  color:#1E40AF !important; font-weight:700 !important; }

/* Table header */
thead th { background:#1E40AF !important; color:white !important;
           font-family:'Fira Code',monospace !important; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility:hidden; }
.block-container { padding-top:.8rem !important; }
</style>
"""


# ── Main ─────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="台灣氣溫預報",
        page_icon="🌡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    # 雲端部署時自動初始化資料庫
    if not os.path.exists(DB_NAME):
        with st.spinner("首次啟動，正在從 CWA API 取得資料並建立資料庫…"):
            try:
                from hw2_1_fetch import fetch_weather_forecast, save_json
                from hw2_2_extract import extract_temperatures
                from hw2_3_database import create_table, insert_temperatures
                raw = fetch_weather_forecast()
                save_json(raw)
                temps = extract_temperatures(raw)
                with sqlite3.connect(DB_NAME) as conn:
                    create_table(conn)
                    insert_temperatures(conn, temps)
                st.rerun()
            except Exception as e:
                st.error(f"資料庫初始化失敗：{e}")
                st.stop()

    # ── Session state ─────────────────────────────────────────
    regions = get_regions()
    if "region_select" not in st.session_state:
        st.session_state.region_select = regions[0]
    if "pending_region" not in st.session_state:
        st.session_state.pending_region = None

    # 地圖點擊後 pending → 在 widget 渲染前套用
    if st.session_state.pending_region:
        st.session_state.region_select = st.session_state.pending_region
        st.session_state.pending_region = None

    # ── Sidebar ───────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center;padding:8px 0 18px'>"
            "<div style='font-size:2.4rem'>🌡️</div>"
            "<div style='font-family:Fira Code,monospace;font-weight:700;"
            "font-size:1rem;color:#1E40AF'>台灣氣溫預報</div>"
            "<div style='font-size:.72rem;color:#94A3B8;margin-top:2px'>"
            "CWA Open Data</div></div>",
            unsafe_allow_html=True
        )

        selected = st.selectbox("選擇地區", regions, key="region_select")

        counties = REGION_INFO.get(selected, {}).get("counties", "")
        st.markdown(
            f"<div style='background:#EFF6FF;border-radius:10px;padding:12px 14px;"
            f"border:1px solid #BFDBFE;margin-top:4px'>"
            f"<div style='font-size:.67rem;color:#64748B;text-transform:uppercase;"
            f"letter-spacing:.05em;margin-bottom:5px'>📌 涵蓋縣市</div>"
            f"<div style='font-size:.85rem;font-weight:600;color:#1E40AF'>"
            f"{counties}</div></div>",
            unsafe_allow_html=True
        )

        st.markdown("<div style='margin:16px 0 8px;border-top:1px solid #E2EAFF'></div>",
                    unsafe_allow_html=True)

        if st.button("📡 更新天氣資料", use_container_width=True, type="primary"):
            with st.spinner("從 CWA API 取得資料中…"):
                try:
                    from hw2_1_fetch import fetch_weather_forecast, save_json
                    from hw2_2_extract import extract_temperatures
                    from hw2_3_database import create_table, insert_temperatures
                    raw   = fetch_weather_forecast()
                    save_json(raw)
                    temps = extract_temperatures(raw)
                    with sqlite3.connect(DB_NAME) as conn:
                        create_table(conn)
                        insert_temperatures(conn, temps)
                    st.cache_data.clear()
                    st.success("✅ 更新完成！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")

        if st.button("🔄 重新整理畫面", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown(
            "<div style='font-size:.68rem;color:#94A3B8;text-align:center;"
            "margin-top:12px'>資料集：CWA F-C0032-001</div>",
            unsafe_allow_html=True
        )

    # ── Header ────────────────────────────────────────────────
    st.markdown(
        "<div class='hdr'>"
        "<div style='font-size:2.2rem'>🗺️</div>"
        "<div><h1>台灣氣溫預報 Web App</h1>"
        "<div class='sub'>中央氣象署（CWA）開放資料平台 ‧ 即時天氣預報</div></div>"
        "</div>",
        unsafe_allow_html=True
    )

    # ── 載入資料 ──────────────────────────────────────────────
    df_all    = load_all()
    df_region = load_region(selected)

    # ── KPI ──────────────────────────────────────────────────
    if not df_region.empty:
        avg_hi = df_region["maxt"].mean()
        avg_lo = df_region["mint"].mean()
        diff   = avg_hi - avg_lo
        st.markdown(
            f"<div class='kpi-wrap'>"
            f"<div class='kpi'><div class='kpi-lbl'>📍 地區</div>"
            f"<div class='kpi-val b'>{selected}</div></div>"
            f"<div class='kpi'><div class='kpi-lbl'>🌡 最高溫（均）</div>"
            f"<div class='kpi-val r'>{avg_hi:.1f}°C</div></div>"
            f"<div class='kpi'><div class='kpi-lbl'>❄️ 最低溫（均）</div>"
            f"<div class='kpi-val i'>{avg_lo:.1f}°C</div></div>"
            f"<div class='kpi amb'><div class='kpi-lbl'>↕️ 日夜溫差</div>"
            f"<div class='kpi-val a'>{diff:.1f}°C</div></div>"
            f"</div>",
            unsafe_allow_html=True
        )

    # ── Row 1：地圖 + 折線圖 ──────────────────────────────────
    c1, c2 = st.columns([1, 1], gap="medium")

    with c1:
        st.markdown("<div class='card-title'>📍 台灣即時氣溫地圖</div>",
                    unsafe_allow_html=True)
        st.caption("點擊圓圈切換地區 ‧ 顏色：🔵 涼 → 🔴 熱 ‧ 大圈＝目前選擇")
        taiwan_map = build_map(df_all, selected)
        map_data = st_folium(
            taiwan_map, height=420,
            use_container_width=True,
            returned_objects=["last_object_clicked"],
            key="folium_map",
        )
        if map_data and map_data.get("last_object_clicked"):
            c = map_data["last_object_clicked"]
            for r, info in REGION_INFO.items():
                if (abs(info["lat"] - c.get("lat",0)) < 0.25 and
                        abs(info["lon"] - c.get("lng",0)) < 0.25):
                    if r != st.session_state.region_select:
                        st.session_state.pending_region = r
                        st.rerun()
                    break

    with c2:
        st.markdown(f"<div class='card-title'>📈 {selected} 氣溫趨勢</div>",
                    unsafe_allow_html=True)
        if not df_region.empty:
            st.plotly_chart(build_line(df_region, selected),
                            use_container_width=True,
                            config={"displayModeBar": False})

    # ── Row 2：詳細表格 + 長條圖 ─────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c3, c4 = st.columns([4, 6], gap="medium")

    with c3:
        st.markdown(f"<div class='card-title'>📋 {selected} 詳細資料</div>",
                    unsafe_allow_html=True)
        if not df_region.empty:
            df_show = df_region[["dataDate","mint","maxt"]].copy()
            df_show["dataDate"] = df_show["dataDate"].apply(
                lambda s: s.split(" ")[1][:5] if " " in str(s) else s)
            df_show.columns = ["時段", "最低(°C)", "最高(°C)"]
            styled = (
                df_show.style
                .map(lambda _: "color:#1D4ED8;font-weight:700;"
                               "font-family:'Fira Code',monospace",
                     subset=["最低(°C)"])
                .map(lambda _: "color:#DC2626;font-weight:700;"
                               "font-family:'Fira Code',monospace",
                     subset=["最高(°C)"])
                .format({"最低(°C)": "{:.0f}", "最高(°C)": "{:.0f}"})
                .set_properties(**{"text-align":"center","font-size":"13px",
                                   "background-color":"white"})
            )
            st.dataframe(styled, use_container_width=True,
                         hide_index=True, height=190)

    with c4:
        st.markdown("<div class='card-title'>📊 全台各地區溫度對比</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(build_bar(df_all, selected),
                        use_container_width=True,
                        config={"displayModeBar": False})

    # ── Row 3：全台摘要 ───────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🌏 全台地區溫度摘要</div>",
                unsafe_allow_html=True)
    summ = region_summary(df_all).round(1)
    summ.columns = ["地區","平均最低(°C)","平均最高(°C)","最低極值(°C)","最高極值(°C)"]

    def hl(row):
        bg = "background:#DBEAFE;font-weight:700" if row["地區"]==selected else "background:white"
        return [bg]*len(row)

    styled_s = (
        summ.style
        .apply(hl, axis=1)
        .map(lambda _: "color:#1D4ED8;font-weight:600;font-family:'Fira Code',monospace",
             subset=["平均最低(°C)","最低極值(°C)"])
        .map(lambda _: "color:#DC2626;font-weight:600;font-family:'Fira Code',monospace",
             subset=["平均最高(°C)","最高極值(°C)"])
        .map(lambda _: "color:#1E40AF;font-weight:700",
             subset=["地區"])
        .format({"平均最低(°C)":"{:.1f}","平均最高(°C)":"{:.1f}",
                 "最低極值(°C)":"{:.0f}","最高極值(°C)":"{:.0f}"})
        .set_properties(**{"text-align":"center","font-size":"13px"})
    )
    st.dataframe(styled_s, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
