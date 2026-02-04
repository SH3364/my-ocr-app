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
    """תיקון ה-TypeError: פונקציה עם 4 ארגומנטים בדיוק"""
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
    """לוגיקה דו-שלבית למניעת שגיאת 'User does not have access'"""
    # שלב 1: ניסיון חילוץ MDN מה-ICCID
    # אנחנו שולחים את ה-ICCID בשדה mdn כי השרת בודק את שניהם בשיטה זו
    res_info = call_soap_api("GetIVRLineInformation", user, password, f"<mdn>{iccid}</mdn>")
    
    # בדיקה אם השרת חסם את הגישה כבר בשלב הראשון
    if "User does not have access to MDN" in res_info:
        return "שגיאת הרשאה ❌", "החשבון שלך אינו בעל ההרשאות לסים זה", False, res_info

    mdn = None
    try:
        root = ET.fromstring(res_info)
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN" and elem.text and len(elem.text) >= 10:
                mdn = elem.text.strip()
                break
    except: pass

    # שלב 2: בדיקת חבילות (באמצעות MDN שנמצא)
    target_value = mdn if mdn else iccid
    pkg_res = call_soap_api("GetActivePackages", user, password, f"<MDN>{target_value}</MDN>")
    
    if "User does not have access to MDN" in pkg_res:
        # אם יש לנו IVR אבל אין גישה לחבילות, זה סים פעיל שמוגן על ידי השרת
        if "<GetIVRLineInformationResult>" in res_info:
            return "סים פעיל (מוגן) ⚠️", "הסים פעיל אך השרת חוסם גישה לפרטי חבילה", False, pkg_res
        return "פנוי (Available)", "הסים לא נמצא במערכת", True, pkg_res

    # ניתוח שם התוכנית
    found_plan = "לא מזוהה"
    try:
        root_pkg = ET.fromstring(pkg_res)
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "Description", "PlanName"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break
    except: pass

    is_correct = (found_plan.lower() == TARGET_PLAN.lower())
    status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
    info = f"טלפון: {mdn if mdn else 'N/A'} | תוכנית: {found_plan}"
    return status, info, is_correct, pkg_res

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש", db['auth'].get('user', ''))
    p = st.text_input("סיסמה", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db); st.success("נשמר!")

st.title("📱 מערכת ניהול ובדיקת סימים אוטומטית")

# טאבים לפי העיצוב שלך
tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בודדת", "📋 ניהול רשימה וייבוא", "📊 בדיקה המונית"])

with tab1:
    val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        if not db['auth']['user'] or not db['auth']['pass']:
            st.warning("נא להגדיר שם משתמש וסיסמה ב-Sidebar")
        else:
            with st.spinner("מבצע זיהוי..."):
                status, info, ok, raw = check_sim_logic(val, db['auth']['user'], db['auth']['pass'])
                if ok: st.success(status)
                else: st.error(status)
                st.info(info)
                with st.expander("נתוני API גולמיים (Debug)"):
                    st.code(raw, language="xml")

# (שאר הטאבים נשארים עם הלוגיקה של ייבוא אקסל ובדיקה המונית)
