import requests
import pandas as pd
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import pyotp
import json
from supabase import create_client, Client

# ==============================
# 🔐 CONFIG
# ==============================
API_KEY = os.getenv("ANGEL_API_KEY", "9MHdQQky")
API_SECRET = os.getenv("ANGEL_API_SECRET", "ac1e4dd3-22fe-4e88-84dd-a9b8a3ee7dc5")

CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE", "AAAD530239")
PASSWORD = os.getenv("ANGEL_PASSWORD", "0498")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "7A7UIPYX3PZ6JJZLNJZ6AQKMMA")

SUPABASE_URL = os.getenv("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SUPABASE_KEY")

ACCESS_TOKEN = None

HEADERS = {
    "X-PrivateKey": API_KEY,
    "Content-Type": "application/json"
}

if SUPABASE_URL != "YOUR_SUPABASE_URL" and SUPABASE_KEY != "YOUR_SUPABASE_KEY":
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# ==============================
# 🔑 LOGIN TO API
# ==============================
def login_and_get_token():
    global ACCESS_TOKEN
    try:
        url = "https://apiconnect.angelone.in/rest/auth/angelbroking/user/v1/loginByPassword"
        totp = pyotp.TOTP(TOTP_SECRET).now() if TOTP_SECRET and TOTP_SECRET != "YOUR_TOTP_SECRET" else ""
        payload = {
            "clientcode": CLIENT_CODE,
            "password": PASSWORD,
            "totp": totp
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00-00-00-00-00-00",
            "X-PrivateKey": API_KEY
        }
        
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        data = res.json()
        
        if data and data.get("status"):
            ACCESS_TOKEN = data["data"]["jwtToken"]
            HEADERS["Authorization"] = f"Bearer {ACCESS_TOKEN}"
        else:
            print("❌ Login failed:", data.get("message", data) if data else res.text)
    except Exception as e:
        print("❌ Login error:", e)

# ==============================
# 🔌 FETCH OPTION CHAIN
# ==============================
def fetch_option_chain():
    if not ACCESS_TOKEN:
        login_and_get_token()
    try:
        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/marketData/v1/optionChain"
        payload = {
            "exchange": "NSE",
            "symbol": "NIFTY"
        }
        res = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        return res.json()
    except Exception as e:
        print("API Error:", e)
        return None

# ==============================
# 🧠 PROCESS DATA
# ==============================
def process_data(raw):
    records = []
    if not raw or "data" not in raw:
        return pd.DataFrame()

    for item in raw["data"]:
        records.append({
            "strike": item["strikePrice"],
            "ce_oi": item["CE"]["openInterest"],
            "pe_oi": item["PE"]["openInterest"],
            "ce_change": item["CE"]["changeinOpenInterest"],
            "pe_change": item["PE"]["changeinOpenInterest"]
        })
    return pd.DataFrame(records)

# ==============================
# 📊 ANALYSIS
# ==============================
def calculate_levels(df):
    resistance = df.loc[df["ce_oi"].idxmax()]
    support = df.loc[df["pe_oi"].idxmax()]
    return resistance, support

def calculate_pcr(df):
    total_pe = df["pe_oi"].sum()
    total_ce = df["ce_oi"].sum()
    if total_ce == 0: return 0.0
    return round(total_pe / total_ce, 2)

def generate_signal(pcr, res, sup):
    if pcr > 1 and sup["pe_change"] > 0:
        return "Bullish"
    elif pcr < 1 and res["ce_change"] > 0:
        return "Bearish"
    return "Sideways"

# ==============================
# 🕒 TIME CHECK (IST)
# ==============================
def is_market_open():
    ist_time = datetime.now(ZoneInfo("Asia/Kolkata")).time()
    if ist_time.hour < 9 or (ist_time.hour == 15 and ist_time.minute > 30) or ist_time.hour > 15:
        return False
    return True

# ==============================
# 🚀 FASTAPI APP
# ==============================
app = FastAPI(title="Nifty Auto Bot API Vercel", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since it's on Vercel, permit all for testing.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Vercel serverless API running", "time": datetime.now().isoformat()}

# ------------------------------
# ⏲️ CRON ENDPOINTS
# ------------------------------
@app.get("/api/cron/heatmap")
def cron_heatmap():
    """Triggered every 3 mins by Vercel Cron"""
    if not is_market_open():
        return {"status": "skipped", "reason": "outside market hours"}
        
    if not supabase:
        return {"error": "Supabase credentials missing"}

    raw = fetch_option_chain()
    df = process_data(raw)
    if df.empty:
        return {"error": "empty data or fetch failed"}

    # Convert to JSON for Supabase
    records = df.rename(columns={
        "ce_oi": "ce",
        "pe_oi": "pe",
        "ce_change": "ceChange",
        "pe_change": "peChange"
    }).to_dict(orient="records")
    
    # Save to Supabase
    data_payload = {
        "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "data": records
    }
    supabase.table('heatmap_snapshots').insert(data_payload).execute()
    
    return {"status": "success", "records": len(records)}

@app.get("/api/cron/summary")
def cron_summary():
    """Triggered every 15 mins by Vercel Cron"""
    if not is_market_open():
        return {"status": "skipped"}
        
    if not supabase:
        return {"error": "Supabase credentials missing"}

    # Fetch latest snapshot
    res = supabase.table('heatmap_snapshots').select("data").order('id', desc=True).limit(2).execute()
    
    if not res.data or len(res.data) == 0:
        return {"error": "No heatmap data found"}
        
    current_payload = res.data[0]["data"]
    
    df = pd.DataFrame(current_payload).rename(columns={
        "ce": "ce_oi",
        "pe": "pe_oi",
        "ceChange": "ce_change",
        "peChange": "pe_change"
    })
    
    res_level, sup_level = calculate_levels(df)
    pcr = calculate_pcr(df)
    signal = generate_signal(pcr, res_level, sup_level)

    summary_data = {
        "spot": 0,
        "pcr": pcr,
        "signal": signal,
        "resistance": {
            "strike": int(res_level["strike"]),
            "change": str(res_level["ce_change"]),
            "strength": min(int(res_level["ce_oi"] / 10000), 100)
        },
        "support": {
            "strike": int(sup_level["strike"]),
            "change": str(sup_level["pe_change"]),
            "strength": min(int(sup_level["pe_oi"] / 10000), 100)
        }
    }
    
    alerts = []
    if len(res.data) > 1:
        prev_df = pd.DataFrame(res.data[1]["data"]).rename(columns={
            "ce": "ce_oi",
            "pe": "pe_oi",
            "ceChange": "ce_change",
            "peChange": "pe_change"
        })
        prev_res = prev_df.loc[prev_df["ce_oi"].idxmax()]
        curr_res = df.loc[df["ce_oi"].idxmax()]
        if curr_res["ce_oi"] < prev_res["ce_oi"]:
            alerts.append("⚠️ Resistance weakening")

        prev_sup = prev_df.loc[prev_df["pe_oi"].idxmax()]
        curr_sup = df.loc[df["pe_oi"].idxmax()]
        if curr_sup["pe_oi"] < prev_sup["pe_oi"]:
            alerts.append("⚠️ Support weakening")

    supabase.table('summary_snapshots').insert({
        "timestamp": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "data": summary_data,
        "alerts": alerts
    }).execute()
    
    return {"status": "success", "summary": summary_data}

# ------------------------------
# 🌐 PUBLIC API (Used by frontend)
# ------------------------------
@app.get("/api/heatmap")
def get_heatmap():
    if not supabase: return []
    res = supabase.table('heatmap_snapshots').select("data").order('id', desc=True).limit(1).execute()
    if res.data:
        return res.data[0]["data"]
    return []

@app.get("/api/summary")
def get_summary():
    if not supabase: return {}
    res = supabase.table('summary_snapshots').select("data").order('id', desc=True).limit(1).execute()
    if res.data:
        return res.data[0]["data"]
    return {}

@app.get("/api/alerts")
def get_alerts():
    if not supabase: return []
    res = supabase.table('summary_snapshots').select("alerts").order('id', desc=True).limit(1).execute()
    if res.data:
        return res.data[0]["alerts"]
    return []
