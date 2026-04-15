# ============================================================
# HW2-4: 台灣氣溫預報 Web App
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

# 六大地區 → 縣市對應
REGION_COUNTIES = {
    "北部":  ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣"],
    "中部":  ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
    "南部":  ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣", "澎湖縣"],
    "東北部": ["宜蘭縣"],
    "東部":  ["花蓮縣", "臺東縣"],
    "東南部": ["金門縣", "連江縣"],
}

# 六大地區地圖中心座標
REGION_INFO = {
    "北部":  {"lat": 25.00, "lon": 121.30},
    "中部":  {"lat": 24.10, "lon": 120.70},
    "南部":  {"lat": 22.90, "lon": 120.30},
    "東北部": {"lat": 24.70, "lon": 121.80},
    "東部":  {"lat": 23.80, "lon": 121.55},
    "東南部": {"lat": 23.50, "lon": 119.80},
}

# 22 縣市座標
COUNTY_INFO = {
    "臺北市": {"lat": 25.04, "lon": 121.51, "short": "北市"},
    "新北市": {"lat": 24.98, "lon": 121.46, "short": "新北"},
    "基隆市": {"lat": 25.13, "lon": 121.74, "short": "基隆"},
    "桃園市": {"lat": 24.99, "lon": 121.30, "short": "桃園"},
    "新竹市": {"lat": 24.80, "lon": 120.97, "short": "竹市"},
    "新竹縣": {"lat": 24.63, "lon": 121.02, "short": "竹縣"},
    "苗栗縣": {"lat": 24.56, "lon": 120.82, "short": "苗栗"},
    "臺中市": {"lat": 24.15, "lon": 120.68, "short": "中市"},
    "彰化縣": {"lat": 24.07, "lon": 120.54, "short": "彰化"},
    "南投縣": {"lat": 23.96, "lon": 120.97, "short": "南投"},
    "雲林縣": {"lat": 23.71, "lon": 120.43, "short": "雲林"},
    "嘉義市": {"lat": 23.48, "lon": 120.45, "short": "嘉市"},
    "嘉義縣": {"lat": 23.45, "lon": 120.63, "short": "嘉縣"},
    "臺南市": {"lat": 23.00, "lon": 120.21, "short": "南市"},
    "高雄市": {"lat": 22.62, "lon": 120.30, "short": "高雄"},
    "屏東縣": {"lat": 22.55, "lon": 120.62, "short": "屏東"},
    "澎湖縣": {"lat": 23.57, "lon": 119.58, "short": "澎湖"},
    "宜蘭縣": {"lat": 24.75, "lon": 121.75, "short": "宜蘭"},
    "花蓮縣": {"lat": 23.97, "lon": 121.60, "short": "花蓮"},
    "臺東縣": {"lat": 22.75, "lon": 121.14, "short": "臺東"},
    "金門縣": {"lat": 24.43, "lon": 118.32, "short": "金門"},
    "連江縣": {"lat": 26.16, "lon": 119.95, "short": "馬祖"},
}

# 縣市 → 地區反查
COUNTY_TO_REGION = {c: r for r, cs in REGION_COUNTIES.items() for c in cs}


# ── DB helpers ───────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_all() -> pd.DataFrame:
    with sqlite3.connect(DB_NAME) as c:
        return pd.read_sql_query(
            f"SELECT * FROM {TABLE_NAME} ORDER BY regionName, dataDate", c)

@st.cache_data(ttl=300)
def load_county(county: str) -> pd.DataFrame:
    with sqlite3.connect(DB_NAME) as c:
        return pd.read_sql_query(
            f"SELECT * FROM {TABLE_NAME} WHERE regionName=? ORDER BY dataDate",
            c, params=(county,))

@st.cache_data(ttl=300)
def get_counties() -> list[str]:
    with sqlite3.connect(DB_NAME) as c:
        rows = c.execute(
            f"SELECT DISTINCT regionName FROM {TABLE_NAME}").fetchall()
    order = list(COUNTY_INFO.keys())
    names = [r[0] for r in rows]
    return sorted(names, key=lambda x: order.index(x) if x in order else 99)

def county_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("regionName")
            .agg(avg_mint=("mint","mean"), avg_maxt=("maxt","mean"),
                 min_mint=("mint","min"), max_maxt=("maxt","max"))
            .reset_index())


# ── 溫度→色彩 ────────────────────────────────────────────────
def temp_color(t: float, lo=15.0, hi=35.0) -> str:
    p = max(0.0, min(1.0, (t - lo) / (hi - lo)))
    r = int(59  + p * 177)
    g = int(130 - p * 62)
    b = int(246 - p * 178)
    return f"#{r:02x}{g:02x}{b:02x}"

def temp_gradient(t: float) -> str:
    base = temp_color(t)
    p = max(0.0, min(1.0, (t - 15) / 20))
    r2 = int(20  + p * 160)
    g2 = int(100 - p * 60)
    b2 = int(200 - p * 150)
    return f"linear-gradient(135deg, {base} 0%, #{r2:02x}{g2:02x}{b2:02x} 100%)"


# ── 地圖標記 HTML ────────────────────────────────────────────
def marker_html_region(region: str, maxt: float, mint: float,
                       is_sel: bool, faded: bool = False) -> str:
    grad    = temp_gradient(maxt)
    w       = 72 if is_sel else (40 if faded else 60)
    opacity = "0.45" if faded else "1"
    ring    = ("box-shadow:0 0 0 4px rgba(30,64,175,0.25),0 4px 20px rgba(0,0,0,0.3);"
               if is_sel else "box-shadow:0 2px 12px rgba(0,0,0,0.2);")
    border  = "border:3px solid #1E40AF;" if is_sel else "border:2px solid rgba(255,255,255,0.8);"
    fs1     = 14 if is_sel else (8 if faded else 11)
    fs2     = 11 if is_sel else (7 if faded else 9)
    return (
        f'<div style="width:{w}px;height:{w}px;border-radius:50%;background:{grad};'
        f'{border}{ring}opacity:{opacity};'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;">'
        f'<span style="font-size:{fs1}px;font-weight:900;color:white;'
        f'text-shadow:0 1px 3px rgba(0,0,0,.8);line-height:1.2;">{region}</span>'
        f'<span style="font-size:{fs2}px;font-weight:700;color:rgba(255,255,255,.9);'
        f'text-shadow:0 1px 2px rgba(0,0,0,.7);">{mint:.0f}~{maxt:.0f}°</span>'
        f'</div>'
    )

def marker_html_county(short: str, maxt: float, mint: float, is_sel: bool) -> str:
    grad   = temp_gradient(maxt)
    w      = 56 if is_sel else 44
    ring   = ("box-shadow:0 0 0 3px rgba(30,64,175,0.3),0 3px 14px rgba(0,0,0,0.3);"
              if is_sel else "box-shadow:0 2px 8px rgba(0,0,0,0.2);")
    border = "border:3px solid #1E40AF;" if is_sel else "border:2px solid rgba(255,255,255,0.8);"
    return (
        f'<div style="width:{w}px;height:{w}px;border-radius:50%;background:{grad};'
        f'{border}{ring}'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;">'
        f'<span style="font-size:{11 if is_sel else 9}px;font-weight:900;color:white;'
        f'text-shadow:0 1px 3px rgba(0,0,0,.7);line-height:1.2;">{short}</span>'
        f'<span style="font-size:{9 if is_sel else 8}px;font-weight:700;'
        f'color:rgba(255,255,255,.9);text-shadow:0 1px 2px rgba(0,0,0,.6);">'
        f'{mint:.0f}~{maxt:.0f}°</span>'
        f'</div>'
    )


# ── Folium 台灣地圖 ──────────────────────────────────────────
def build_map(df_all: pd.DataFrame, selected_county: str,
              expanded_region: str | None) -> folium.Map:
    summ = county_summary(df_all).set_index("regionName")
    selected_region = COUNTY_TO_REGION.get(selected_county, "")

    if expanded_region is None:
        # ── 地區總覽 ─────────────────────────────────────────
        m = folium.Map(location=[23.8, 120.9], zoom_start=7,
                       tiles="CartoDB positron")
        m.options["zoomControl"] = False

        for region, info in REGION_INFO.items():
            cs = [c for c in REGION_COUNTIES[region] if c in summ.index]
            if not cs:
                continue
            avg_maxt = float(sum(summ.loc[c, "avg_maxt"] for c in cs) / len(cs))
            avg_mint = float(sum(summ.loc[c, "avg_mint"] for c in cs) / len(cs))
            is_sel   = (region == selected_region)
            w        = 72 if is_sel else 60

            folium.Marker(
                location=[info["lat"], info["lon"]],
                icon=folium.DivIcon(
                    html=marker_html_region(region, avg_maxt, avg_mint, is_sel),
                    icon_size=(w, w), icon_anchor=(w // 2, w // 2),
                ),
                tooltip=folium.Tooltip(
                    f"<b style='color:#1E40AF'>{region}</b><br>"
                    f"🌡 {avg_maxt:.1f}° / ❄️ {avg_mint:.1f}°<br>"
                    f"<small style='color:#64748B'>點擊展開縣市</small>",
                    sticky=True,
                ),
            ).add_to(m)

    else:
        # ── 縣市展開 ─────────────────────────────────────────
        ri   = REGION_INFO[expanded_region]
        cs   = [c for c in REGION_COUNTIES[expanded_region] if c in COUNTY_INFO]
        lats = [COUNTY_INFO[c]["lat"] for c in cs]
        lons = [COUNTY_INFO[c]["lon"] for c in cs]
        pad  = 0.35
        m = folium.Map(location=[ri["lat"], ri["lon"]], zoom_start=9,
                       tiles="CartoDB positron")
        if lats:
            m.fit_bounds([[min(lats)-pad, min(lons)-pad],
                          [max(lats)+pad, max(lons)+pad]])
        m.options["zoomControl"] = False

        # 展開區域的縣市
        for county in cs:
            if county not in summ.index:
                continue
            info   = COUNTY_INFO[county]
            maxt   = float(summ.loc[county, "avg_maxt"])
            mint   = float(summ.loc[county, "avg_mint"])
            is_sel = (county == selected_county)
            w      = 56 if is_sel else 44
            folium.Marker(
                location=[info["lat"], info["lon"]],
                icon=folium.DivIcon(
                    html=marker_html_county(info["short"], maxt, mint, is_sel),
                    icon_size=(w, w), icon_anchor=(w // 2, w // 2),
                ),
                tooltip=folium.Tooltip(
                    f"<b style='color:#1E40AF'>{county}</b><br>"
                    f"🌡 {maxt:.1f}° / ❄️ {mint:.1f}°",
                    sticky=True,
                ),
            ).add_to(m)

        # 其他地區：小圓（淡化），點擊可切換
        for region, info in REGION_INFO.items():
            if region == expanded_region:
                continue
            cs_r = [c for c in REGION_COUNTIES[region] if c in summ.index]
            if not cs_r:
                continue
            avg_maxt = float(sum(summ.loc[c, "avg_maxt"] for c in cs_r) / len(cs_r))
            avg_mint = float(sum(summ.loc[c, "avg_mint"] for c in cs_r) / len(cs_r))
            w = 40
            folium.Marker(
                location=[info["lat"], info["lon"]],
                icon=folium.DivIcon(
                    html=marker_html_region(region, avg_maxt, avg_mint,
                                            False, faded=True),
                    icon_size=(w, w), icon_anchor=(w // 2, w // 2),
                ),
                tooltip=folium.Tooltip(
                    f"<b>{region}</b><br><small>點擊切換地區</small>",
                    sticky=True,
                ),
            ).add_to(m)

    return m


# ── 折線圖 ────────────────────────────────────────────────────
def build_line(df: pd.DataFrame, county: str) -> go.Figure:
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
def build_bar(df_all: pd.DataFrame, selected_county: str) -> go.Figure:
    s = county_summary(df_all)
    order = list(COUNTY_INFO.keys())
    s["_ord"] = s["regionName"].apply(lambda x: order.index(x) if x in order else 99)
    s = s.sort_values("_ord").reset_index(drop=True)

    colors_hi = ["#1E40AF" if r == selected_county else "#93C5FD" for r in s["regionName"]]
    colors_lo = ["#D97706" if r == selected_county else "#FCD34D" for r in s["regionName"]]
    short_names = [COUNTY_INFO.get(r, {}).get("short", r) for r in s["regionName"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=short_names, y=s["avg_maxt"], name="平均最高",
        marker_color=colors_hi,
        text=[f"{v:.0f}°" for v in s["avg_maxt"]],
        textposition="outside", textfont=dict(size=9),
        hovertemplate="%{x} 最高：%{y:.1f}°C<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=short_names, y=s["avg_mint"], name="平均最低",
        marker_color=colors_lo,
        text=[f"{v:.0f}°" for v in s["avg_mint"]],
        textposition="outside", textfont=dict(size=9),
        hovertemplate="%{x} 最低：%{y:.1f}°C<extra></extra>",
    ))
    fig.update_layout(
        barmode="group", plot_bgcolor="#FAFCFF", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#334155"),
                   tickangle=-45),
        yaxis=dict(showgrid=True, gridcolor="#E9EEF6", ticksuffix="°"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
        margin=dict(l=30, r=10, t=30, b=60), height=270,
    )
    return fig


# ── CSS ──────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

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

.card-title {
  font-family:'Fira Code',monospace; font-size:.78rem; font-weight:700;
  color:#1E40AF; text-transform:uppercase; letter-spacing:.07em;
  padding-bottom:10px; border-bottom:2px solid #DBEAFE; margin-bottom:12px;
}

/* Dropdown 選項白底（全域） */
div[data-baseweb="popover"] > div { background:white !important; }
ul[data-baseweb="menu"], [data-baseweb="menu"] ul { background:white !important; }
li[role="option"]              { background:white !important; color:#1E3A8A !important; }
li[role="option"]:hover        { background:#EFF6FF !important; }
li[aria-selected="true"]       { background:#DBEAFE !important;
                                  color:#1E40AF !important; font-weight:700 !important; }

thead th { background:#1E40AF !important; color:white !important;
           font-family:'Fira Code',monospace !important; }

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

    # 雲端部署時自動初始化資料庫；若為舊版六大地區也重建
    def _needs_init() -> bool:
        if not os.path.exists(DB_NAME):
            return True
        try:
            with sqlite3.connect(DB_NAME) as c:
                names = {r[0] for r in c.execute(
                    f"SELECT DISTINCT regionName FROM {TABLE_NAME} LIMIT 10")}
                return bool(names & {"北部", "中部", "南部", "東部", "東北部", "東南部"})
        except Exception:
            return True

    if _needs_init():
        with st.spinner("正在從 CWA API 取得資料並建立資料庫…"):
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
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"資料庫初始化失敗：{e}")
                st.stop()

    # ── Session state ─────────────────────────────────────────
    counties = get_counties()
    if "county_select" not in st.session_state:
        st.session_state.county_select = counties[0]
    if "pending_county" not in st.session_state:
        st.session_state.pending_county = None
    if "map_expanded_region" not in st.session_state:
        st.session_state.map_expanded_region = None   # None = 地區總覽

    if st.session_state.pending_county:
        st.session_state.county_select = st.session_state.pending_county
        st.session_state.pending_county = None

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

        selected = st.selectbox("選擇縣市", counties, key="county_select")

        # 選縣市時自動展開對應地區
        auto_region = COUNTY_TO_REGION.get(selected)
        if auto_region and st.session_state.map_expanded_region != auto_region:
            st.session_state.map_expanded_region = auto_region

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
    df_county = load_county(selected)

    # ── KPI ──────────────────────────────────────────────────
    if not df_county.empty:
        avg_hi = df_county["maxt"].mean()
        avg_lo = df_county["mint"].mean()
        diff   = avg_hi - avg_lo
        st.markdown(
            f"<div class='kpi-wrap'>"
            f"<div class='kpi'><div class='kpi-lbl'>📍 縣市</div>"
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
    exp_region = st.session_state.map_expanded_region

    with c1:
        st.markdown("<div class='card-title'>📍 台灣即時氣溫地圖</div>",
                    unsafe_allow_html=True)

        # 地圖模式提示 + 返回按鈕
        col_cap, col_back = st.columns([3, 1])
        with col_cap:
            if exp_region:
                st.caption(f"📂 {exp_region} ‧ 點擊縣市選取 ‧ 顏色：🔵涼→🔴熱")
            else:
                st.caption("點擊地區展開縣市 ‧ 顏色：🔵 涼 → 🔴 熱")
        with col_back:
            if exp_region:
                if st.button("◀ 全台", use_container_width=True):
                    st.session_state.map_expanded_region = None
                    st.rerun()

        taiwan_map = build_map(df_all, selected, exp_region)
        map_data = st_folium(
            taiwan_map, height=430,
            use_container_width=True,
            returned_objects=["last_object_clicked"],
            key="folium_map",
        )

        if map_data and map_data.get("last_object_clicked"):
            c = map_data["last_object_clicked"]
            lat_c = c.get("lat", 0)
            lng_c = c.get("lng", 0)

            if exp_region is None:
                # 地區總覽模式：點擊展開地區
                for region, info in REGION_INFO.items():
                    if abs(info["lat"] - lat_c) < 0.4 and abs(info["lon"] - lng_c) < 0.4:
                        st.session_state.map_expanded_region = region
                        first = next((x for x in REGION_COUNTIES[region]
                                      if x in set(counties)), None)
                        if first and first != selected:
                            st.session_state.pending_county = first
                        st.rerun()
                        break
            else:
                # 縣市展開模式：點縣市選取 / 點地區切換
                clicked = False
                for county in REGION_COUNTIES.get(exp_region, []):
                    if county not in COUNTY_INFO:
                        continue
                    info = COUNTY_INFO[county]
                    if abs(info["lat"] - lat_c) < 0.18 and abs(info["lon"] - lng_c) < 0.18:
                        if county != selected:
                            st.session_state.pending_county = county
                            st.rerun()
                        clicked = True
                        break
                if not clicked:
                    for region, info in REGION_INFO.items():
                        if region == exp_region:
                            continue
                        if abs(info["lat"] - lat_c) < 0.4 and abs(info["lon"] - lng_c) < 0.4:
                            st.session_state.map_expanded_region = region
                            first = next((x for x in REGION_COUNTIES[region]
                                          if x in set(counties)), None)
                            if first and first != selected:
                                st.session_state.pending_county = first
                            st.rerun()
                            break

    with c2:
        st.markdown(f"<div class='card-title'>📈 {selected} 氣溫趨勢</div>",
                    unsafe_allow_html=True)
        if not df_county.empty:
            st.plotly_chart(build_line(df_county, selected),
                            use_container_width=True,
                            config={"displayModeBar": False})

    # ── Row 2：詳細表格 + 長條圖 ─────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c3, c4 = st.columns([4, 6], gap="medium")

    with c3:
        st.markdown(f"<div class='card-title'>📋 {selected} 詳細資料</div>",
                    unsafe_allow_html=True)
        if not df_county.empty:
            df_show = df_county[["dataDate","mint","maxt"]].copy()
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
                         hide_index=True, height=165)

    with c4:
        st.markdown("<div class='card-title'>📊 全台各縣市溫度對比</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(build_bar(df_all, selected),
                        use_container_width=True,
                        config={"displayModeBar": False})

    # ── Row 3：全台摘要 ───────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='card-title'>🌏 全台縣市溫度摘要</div>",
                unsafe_allow_html=True)
    summ = county_summary(df_all)
    order = list(COUNTY_INFO.keys())
    summ["_ord"] = summ["regionName"].apply(lambda x: order.index(x) if x in order else 99)
    summ = summ.sort_values("_ord").drop(columns="_ord").round(1).reset_index(drop=True)
    summ.columns = ["縣市","平均最低(°C)","平均最高(°C)","最低極值(°C)","最高極值(°C)"]

    def hl(row):
        bg = "background:#DBEAFE;font-weight:700" if row["縣市"]==selected else "background:white"
        return [bg]*len(row)

    styled_s = (
        summ.style
        .apply(hl, axis=1)
        .map(lambda _: "color:#1D4ED8;font-weight:600;font-family:'Fira Code',monospace",
             subset=["平均最低(°C)","最低極值(°C)"])
        .map(lambda _: "color:#DC2626;font-weight:600;font-family:'Fira Code',monospace",
             subset=["平均最高(°C)","最高極值(°C)"])
        .map(lambda _: "color:#1E40AF;font-weight:700", subset=["縣市"])
        .format({"平均最低(°C)":"{:.1f}","平均最高(°C)":"{:.1f}",
                 "最低極值(°C)":"{:.0f}","最高極值(°C)":"{:.0f}"})
        .set_properties(**{"text-align":"center","font-size":"13px"})
    )
    st.dataframe(styled_s, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
