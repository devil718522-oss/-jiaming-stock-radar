import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import date, timedelta

st.set_page_config(page_title="家銘台股趨勢雷達 V1", page_icon="📡", layout="wide")
st.title("📡 家銘台股趨勢雷達 V1")
st.caption("V1：日K趨勢分析｜5/10/20/60MA｜量價｜趨勢評分｜5MA進 / 10MA出回測")

API = "https://api.finmindtrade.com/api/v4/data"

@st.cache_data(ttl=3600)
def get_price(stock_id, start_date, end_date, token=""):
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": str(start_date),
        "end_date": str(end_date),
    }
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(API, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    payload = r.json()
    df = pd.DataFrame(payload.get("data", []))
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df.rename(columns={
        "open":"Open", "max":"High", "min":"Low", "close":"Close",
        "Trading_Volume":"Volume"
    })
    return df

def indicators(df):
    d = df.copy()
    for n in [5,10,20,60]:
        d[f"MA{n}"] = d["Close"].rolling(n).mean()
    d["VOL20"] = d["Volume"].rolling(20).mean()
    d["VOL_RATIO"] = d["Volume"] / d["VOL20"]
    d["MA5_UP"] = d["MA5"] > d["MA5"].shift(1)
    d["MA10_UP"] = d["MA10"] > d["MA10"].shift(1)
    return d

def score_row(r):
    score = 0
    reasons = []
    if r["Close"] > r["MA5"]:
        score += 20; reasons.append("股價站上5MA")
    if r["MA5"] > r["MA10"]:
        score += 20; reasons.append("5MA > 10MA")
    if r["MA10"] > r["MA20"]:
        score += 15; reasons.append("10MA > 20MA")
    if r["MA20"] > r["MA60"]:
        score += 15; reasons.append("20MA > 60MA")
    if bool(r["MA5_UP"]):
        score += 10; reasons.append("5MA上彎")
    if bool(r["MA10_UP"]):
        score += 5; reasons.append("10MA上彎")
    vr = r.get("VOL_RATIO", np.nan)
    if pd.notna(vr) and vr >= 1.5:
        score += 15; reasons.append("量能≥20日均量1.5倍")
    elif pd.notna(vr) and vr >= 1.0:
        score += 8; reasons.append("量能高於20日均量")
    return min(score,100), "、".join(reasons)

def backtest(df, entry_ma=5, exit_ma=10):
    d = df.dropna(subset=[f"MA{entry_ma}", f"MA{exit_ma}"]).copy()
    d["entry"] = (d["Close"] > d[f"MA{entry_ma}"]) & (d["Close"].shift(1) <= d[f"MA{entry_ma}"].shift(1))
    d["exit"] = (d["Close"] < d[f"MA{exit_ma}"]) & (d["Close"].shift(1) >= d[f"MA{exit_ma}"].shift(1))
    trades, holding = [], False
    entry_price = entry_date = None
    for _, r in d.iterrows():
        if not holding and r["entry"]:
            holding, entry_price, entry_date = True, r["Close"], r["date"]
        elif holding and r["exit"]:
            ret = r["Close"]/entry_price - 1
            trades.append([entry_date, r["date"], entry_price, r["Close"], ret])
            holding = False
    t = pd.DataFrame(trades, columns=["進場日","出場日","進場價","出場價","報酬率"])
    return t

with st.sidebar:
    st.header("設定")
    stock_id = st.text_input("股票代號", "2409")
    years = st.slider("歷史資料（年）", 1, 5, 3)
    token = st.text_input("FinMind Token（可留空）", type="password")
    st.divider()
    st.caption("V1 預設策略：收盤突破5MA進場；收盤跌破10MA出場。")

end = date.today()
start = end - timedelta(days=365*years + 120)

if st.button("開始分析", type="primary", use_container_width=True):
    try:
        raw = get_price(stock_id, start, end, token)
        if raw.empty:
            st.error("查無資料。請確認股票代號或 API 狀態。")
            st.stop()
        df = indicators(raw)
        latest = df.dropna(subset=["MA60"]).iloc[-1]
        score, reasons = score_row(latest)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("最新收盤", f'{latest["Close"]:.2f}')
        c2.metric("趨勢分數", f"{score}/100")
        c3.metric("5MA", f'{latest["MA5"]:.2f}')
        c4.metric("10MA", f'{latest["MA10"]:.2f}')

        if score >= 80:
            st.success(f"🟢 強勢觀察｜{reasons}")
        elif score >= 60:
            st.warning(f"🟡 趨勢觀察｜{reasons}")
        else:
            st.error(f"🔴 暫不列入強勢候選｜{reasons}")

        chart = df.set_index("date")[["Close","MA5","MA10","MA20","MA60"]].dropna()
        st.subheader("價格與均線")
        st.line_chart(chart)

        trades = backtest(df, 5, 10)
        st.subheader("5MA進 / 10MA出 回測")
        if trades.empty:
            st.info("此期間沒有完整交易。")
        else:
            win = (trades["報酬率"] > 0).mean()
            avg = trades["報酬率"].mean()
            total = (1 + trades["報酬率"]).prod() - 1
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("交易次數", len(trades))
            m2.metric("勝率", f"{win:.1%}")
            m3.metric("平均單筆", f"{avg:.2%}")
            m4.metric("複利總報酬", f"{total:.2%}")
            show = trades.copy()
            show["報酬率"] = show["報酬率"].map(lambda x:f"{x:.2%}")
            st.dataframe(show.sort_values("進場日", ascending=False), use_container_width=True)

        st.caption("注意：此為研究/回測工具，不構成投資建議。V1 尚未計入手續費、交易稅、滑價、除權息調整與存活者偏誤。")
    except Exception as e:
        st.exception(e)
