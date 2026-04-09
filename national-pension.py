import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import requests

st.set_page_config(page_title="National Pension Dashboard", page_icon="🏢", layout="wide")
st.title("🏢 National Pension Workplace Dashboard")

# ── Google Drive CSV ──────────────────────────────────────────────────────────
FILE_ID = "1lbks2ZHhqs1sx6XZONsOtFB5kIeT9SVD"
GDRIVE_URL = f"https://drive.google.com/uc?export=download&id={FILE_ID}"

@st.cache_data(show_spinner="Loading data from Google Drive...")
def load_data():
    try:
        response = requests.get(GDRIVE_URL)
        response.raise_for_status()
        df = pd.read_csv(io.BytesIO(response.content), encoding="cp949", low_memory=False)
        return df, True
    except Exception as e:
        st.warning(f"Could not load real data: {e}. Using sample data instead.")
        return load_sample(), False

def load_sample():
    import numpy as np
    rng = np.random.default_rng(42)
    n = 2000
    regions    = ["Seoul","Busan","Incheon","Daegu","Gwangju",
                  "Daejeon","Ulsan","Gyeonggi","Gangwon","Jeju"]
    industries = ["Manufacturing","Retail","IT/Software","Construction",
                  "Healthcare","Finance","Education","Food Service",
                  "Logistics","Real Estate"]
    return pd.DataFrame({
        "year_month":      rng.choice(["202312","202401","202402","202403","202404","202405"], n),
        "workplace_name":  [f"Company_{i}" for i in range(n)],
        "status":          rng.choice(["Active","Inactive"], n, p=[0.9,0.1]),
        "region":          rng.choice(regions, n),
        "industry":        rng.choice(industries, n),
        "subscribers":     rng.integers(3, 500, n),
        "monthly_billing": rng.integers(500_000, 50_000_000, n),
        "new_enrollees":   rng.integers(0, 20, n),
        "lost_enrollees":  rng.integers(0, 15, n),
    })

df_raw, is_real = load_data()

# ── Column rename (real data) ─────────────────────────────────────────────────
if is_real:
    df_raw.rename(columns={
        "자료생성년월":"year_month","사업장명":"workplace_name",
        "가입상태":"status","광역시코드":"region","업종코드명":"industry",
        "가입자수":"subscribers","고지금액":"monthly_billing",
        "신규":"new_enrollees","상실":"lost_enrollees",
    }, inplace=True)
    st.success("✅ Real data loaded from Google Drive!")
else:
    st.info("⚠️ Demo mode – using sample data.")

df = df_raw.copy()

for col in ["subscribers","monthly_billing","new_enrollees","lost_enrollees"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df["est_monthly_salary"] = (df["monthly_billing"] / df["subscribers"].replace(0, pd.NA)) / 0.09
df["est_annual_salary"]  = df["est_monthly_salary"] * 12

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 Filters")
    regions_list = sorted(df["region"].dropna().unique())
    sel_region = st.multiselect("Region", regions_list, default=regions_list[:5])
    if sel_region:
        df = df[df["region"].isin(sel_region)]
    industries_list = sorted(df["industry"].dropna().unique())
    sel_industry = st.multiselect("Industry", industries_list, default=industries_list[:5])
    if sel_industry:
        df = df[df["industry"].isin(sel_industry)]

# ── KPI ───────────────────────────────────────────────────────────────────────
st.subheader("📊 Key Metrics")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Workplaces",       f"{len(df):,}")
k2.metric("Total Subscribers",      f"{int(df['subscribers'].sum()):,}")
k3.metric("Total Billing (KRW)",    f"₩{int(df['monthly_billing'].sum()):,}")
k4.metric("Avg Est. Annual Salary", f"₩{int(df['est_annual_salary'].median()):,}")
st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Subscribers by Region")
    reg = df.groupby("region")["subscribers"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots()
    reg.plot(kind="bar", ax=ax, color="steelblue")
    ax.set_xlabel("Region"); ax.set_ylabel("Subscribers")
    plt.xticks(rotation=30, ha="right"); plt.tight_layout()
    st.pyplot(fig); plt.close()

with col_b:
    st.subheader("Subscribers by Industry")
    ind = df.groupby("industry")["subscribers"].sum().sort_values().tail(10)
    fig, ax = plt.subplots()
    ind.plot(kind="barh", ax=ax, color="coral")
    ax.set_xlabel("Subscribers"); plt.tight_layout()
    st.pyplot(fig); plt.close()

col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Est. Annual Salary Distribution")
    sal = df["est_annual_salary"].dropna()
    sal = sal[sal < sal.quantile(0.99)]
    fig, ax = plt.subplots()
    ax.hist(sal, bins=40, color="#636EFA", edgecolor="white")
    ax.set_xlabel("Est. Annual Salary (KRW)"); ax.set_ylabel("Count")
    plt.tight_layout(); st.pyplot(fig); plt.close()

with col_d:
    st.subheader("New vs Lost Enrollees by Region")
    nl = df.groupby("region")[["new_enrollees","lost_enrollees"]].sum()
    fig, ax = plt.subplots()
    nl.plot(kind="bar", ax=ax, color=["#2ECC71","#E74C3C"])
    plt.xticks(rotation=30, ha="right"); plt.tight_layout()
    st.pyplot(fig); plt.close()

# ── Top 20 ────────────────────────────────────────────────────────────────────
st.subheader("🏆 Top 20 Workplaces by Subscribers")
top20 = df.nlargest(20,"subscribers")[["workplace_name","subscribers","region","industry"]].reset_index(drop=True)
top20.index += 1
st.dataframe(top20, use_container_width=True)

with st.expander("🔎 Raw Data"):
    st.dataframe(df.head(500), use_container_width=True)

st.caption("Built with Streamlit · Data: Korea Public Data Portal · Pension rate: 9%")
