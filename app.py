import streamlit as st
import pandas as pd
import yfinance as yf

# 設定網頁標題
st.set_page_config(page_title="自定義 ETF 質押試算工具", layout="wide")

st.title("🚀 全彈性 ETF 質押與 0050 槓桿試算")
st.markdown("輸入任何台股代碼，即時計算市值、維持率與利差效益。")

# --- 1. 動態資產輸入區 ---
st.sidebar.header("📋 1. 設定持股組合")
st.sidebar.info("請輸入台股代碼 (例如: 0050, 00878) 與持有張數")

# 初始化 Session State 來儲存輸入框數量
if 'input_rows' not in st.session_state:
    st.session_state.input_rows = 3  # 預設三個輸入框

def add_row():
    st.session_state.input_rows += 1

# 輸入區域
user_assets = []
for i in range(st.session_state.input_rows):
    c1, c2 = st.sidebar.columns([2, 1])
    ticker = c1.text_input(f"代碼 {i+1}", key=f"tick_{i}", value="0050" if i==0 else ("00878" if i==1 else ""))
    amount = c2.number_input(f"張數", key=f"amt_{i}", min_value=0.0, step=1.0, value=0.0)
    if ticker:
        # 修正為 yfinance 格式：台股需加 .TW
        yf_ticker = ticker if ".TW" in ticker.upper() else f"{ticker}.TW"
        user_assets.append({"ticker": yf_ticker, "display_name": ticker, "amount": amount})

st.sidebar.button("➕ 增加標的", on_click=add_row)

# --- 2. 質押與市場設定 ---
st.sidebar.divider()
st.sidebar.header("💰 2. 質押設定")
loan_rate = st.sidebar.number_input("元大質押年利率 (%)", value=2.58) / 100
loan_ratio = st.sidebar.slider("預計貸出成數 (%)", 10, 60, 50) / 100
div_yield_input = st.sidebar.slider("組合平均預期年化殖利率 (%)", 0.0, 10.0, 6.0) / 100
growth_target = st.sidebar.slider("0050 (再投資標的) 預期年成長 (%)", -20, 30, 12) / 100

# --- 3. 抓取即時數據 ---
@st.cache_data(ttl=600)  # 10分鐘更新一次股價
def fetch_stock_data(assets):
    if not assets: return pd.DataFrame()
    tickers = [a["ticker"] for a in assets]
    try:
        data = yf.download(tickers, period="1d")['Close'].iloc[-1]
        if len(tickers) == 1: # 單一標的處理
            return {tickers[0]: data}
        return data.to_dict()
    except:
        return {}

stock_prices = fetch_stock_data(user_assets)

# --- 4. 計算與顯示 ---
if user_assets and stock_prices:
    rows = []
    total_market_val = 0
    
    for asset in user_assets:
        price = stock_prices.get(asset["ticker"], 0)
        market_val = asset["amount"] * 1000 * price
        total_market_val += market_val
        rows.append({
            "標的": asset["display_name"],
            "現價": f"{price:.2f}",
            "張數": asset["amount"],
            "市值": int(market_val)
        })
    
    df_assets = pd.DataFrame(rows)
    
    # 計算核心數值
    total_loan = total_market_val * loan_ratio
    annual_interest = total_loan * loan_rate
    annual_dividend = total_market_val * div_yield_input
    net_cashflow = annual_dividend - annual_interest
    
    # 頂部指標
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("總市值", f"${total_market_val:,.0f}")
    m2.metric("可貸金額", f"${total_loan:,.0f}")
    m3.metric("維持率", f"{(1/loan_ratio)*100:.0f}%")
    m4.metric("淨年現金流", f"${net_cashflow:,.0f}")

    st.subheader("📋 資產細節")
    st.table(df_assets)

    # --- 5. 效益與風險 ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 再投資 0050 效益預估")
        # 獲取 0050 即時價來計算可買股數
        p_0050 = stock_prices.get("0050.TW", 200.0) # 預設一個大約值若沒在清單內
        new_shares = total_loan / p_0050
        profit_0050 = total_loan * growth_target
        st.info(f"借出資金可增購 **0050 約 {new_shares:.1f} 股**")
        st.success(f"0050 預期回報 (含配息): **${profit_0050:,.0f}**")
        st.metric("總策略預期淨損益", f"${profit_0050 + net_cashflow:,.0f}")

    with c2:
        st.subheader("🚨 斷頭壓力測試")
        drops = [0, -0.1, -0.2, -0.3, -0.4, -0.5]
        risk_data = []
        for d in drops:
            m_ratio = ((total_market_val * (1 + d)) / total_loan) * 100
            risk_data.append({"跌幅 (%)": f"{int(d*100)}%", "維持率": f"{m_ratio:.1f}%", "狀態": "✅ 安全" if m_ratio > 140 else "🚨 危險"})
        st.dataframe(pd.DataFrame(risk_data), use_container_width=True)

else:
    st.warning("請在左側輸入正確的台股代碼並設定張數。")
