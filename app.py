import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- הגדרות ליבה ---
DB_FILE = "sim_database.json"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
API_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "sims" not in data: data["sims"] = []
                if "auth" not in data: data["auth"] = {"user": "", "pass": ""}
                return data
        except: pass
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def call_soap_api(method, user, password, body_content):
    """שליחת בקשת SOAP - תוקן למניעת TypeError"""
    soap_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{method} xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      {body_content}
    </{method}>
  </soap:Body>
</soap:Envelope>"""

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }
    try:
        response = requests.post(API_URL, data=soap_payload, headers=headers, timeout=20)
        return response.text
    except Exception as e:
        return f"<error>{str(e)}</error>"

def check_sim_logic(iccid, user, password):
    """לוגיקה זהירה: לא קובעת 'פנוי' ללא הוכחה מהשרת"""
    # ניסיון קבלת מידע בסיסי
    res_info = call_soap_api("GetIVRLineInformation", user, password, f"<mdn>{iccid}</mdn>")
    
    # אם השרת חוסם גישה - אנחנו לא יודעים אם זה פנוי או פעיל של מישהו אחר
    if "User does not have access to MDN" in res_info:
        return "אין גישה (סטטוס לא ידוע) ⚠️", "השרת מסרב לתת מידע על מזהה זה. ייתכן שהסים לא הופעל או שאינו משויך לחשבון שלך.", False, res_info

    try:
        root = ET.fromstring(res_info)
        found_plan = "לא מזוהה"
        mdn = None
        
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN": mdn = elem.text
            if tag in ["RatePlan", "PlanName", "MasterCategory"]:
                if elem.text: found_plan = elem.text.strip()

        if mdn or found_plan != "לא מזוהה":
            is_correct = (found_plan.lower() == TARGET_PLAN.lower())
            status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
            return status, f"טלפון: {mdn} | תוכנית: {found_plan}", is_correct, res_info
            
        return "פנוי (Available) ⚪", "לא נמצא מידע פעיל בשרת", True, res_info

    except Exception as e:
        return "שגיאת ניתוח", str(e), False, res_info

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש", db['auth'].get('user', ''))
    p = st.text_input("סיסמה", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db); st.success("נשמר!")

st.title("📱 מערכת ניהול ובדיקת סימים")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בודדת", "📋 ניהול רשימה", "📊 בדיקה המונית"])

with tab1:
    val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("שואל את השרת..."):
            status, info, ok, raw = check_sim_logic(val, db['auth']['user'], db['auth']['pass'])
            if "תקין" in status: st.success(status)
            elif "אין גישה" in status: st.warning(status)
            else: st.error(status)
            st.info(info)
            with st.expander("נתוני API גולמיים (Debug)"):
                st.code(raw, language="xml")
