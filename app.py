import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- הגדרות ---
DB_FILE = "sim_database.json"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
API_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def check_sim_full_search(iccid, user, password):
    if not user or not password:
        return "שגיאה", "חסר שם משתמש/סיסמה", False, ""

    # שימוש ב-SearchSubscribers - הפקודה הכי רחבה שיש
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Header>
    <AuthenticationHeader xmlns="urn:telispire:MdnServices">
      <Username>{user}</Username>
      <Password>{password}</Password>
    </AuthenticationHeader>
  </soap:Header>
  <soap:Body>
    <SearchSubscribers xmlns="urn:telispire:MdnServices">
      <SearchValue>{iccid}</SearchValue>
      <SearchType>ICCID</SearchType>
    </SearchSubscribers>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/SearchSubscribers"
    }

    try:
        response = requests.post(API_URL, data=soap_body, headers=headers, timeout=20)
        raw_res = response.text

        if response.status_code != 200:
            return f"שגיאה {response.status_code}", "השרת לא הגיב כראוי", False, raw_res

        root = ET.fromstring(raw_res)
        
        # חילוץ נתונים חכם
        mdn = "לא נמצא"
        plan = "לא נמצאה תוכנית"
        found_active = False

        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN":
                mdn = elem.text
                found_active = True
            if tag in ["PlanName", "RatePlanName", "RatePlan"]:
                if elem.text:
                    plan = elem.text.strip()

        if not found_active or mdn == "לא נמצא":
            return "סים לא פעיל", "ה-API לא מצא מנוי פעיל עם ה-ICCID הזה", False, raw_res

        is_correct = (TARGET_PLAN.lower() in plan.lower())
        status = "תקין ✅" if is_correct else "תוכנית לא תואמת ❌"
        
        detail = f"טלפון משויך: {mdn} | תוכנית במערכת: {plan}"
        return status, detail, is_correct, raw_res

    except Exception as e:
        return "שגיאה טכנית", str(e), False, ""

# --- ממשק ---
st.set_page_config(page_title="בדיקה לפי ICCID", layout="wide")
db = load_db()

with st.sidebar:
    st.header("🔑 פרטי התחברות")
    u = st.text_input("User", db['auth'].get('user', ''))
    p = st.text_input("Pass", db['auth'].get('pass', ''), type="password")
    if st.button("שמור"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 זיהוי אוטומטי של סים (ICCID)")

iccid_input = st.text_input("הכנס ICCID לבדיקה:")

if st.button("בדוק סים 🚀"):
    if iccid_input:
        with st.spinner("מבצע חיפוש מנוי..."):
            status, detail, ok, raw = check_sim_full_search(iccid_input, db['auth']['user'], db['auth']['pass'])
            
            if ok: st.success(status)
            else: st.error(status)
            
            st.info(detail)
            
            with st.expander("ראה נתונים גולמיים"):
                st.code(raw, language="xml")
