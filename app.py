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
                return json.load(f)
        except: pass
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def call_soap(method, user, password, body_content):
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
    # שלב 1: האם הסים בכלל קיים? (בדיקת IVR שהוכחה כעובדת אצלך)
    res_ivr = call_soap("GetIVRLineInformation", user, password, f"<mdn>{iccid}</mdn>")
    
    is_active_in_system = "<GetIVRLineInformationResult>" in res_ivr
    
    # שלב 2: ניסיון חילוץ MDN כדי שנוכל לבדוק חבילות
    mdn = None
    # ננסה לחלץ MDN מכל תגית אפשרית ב-XML
    try:
        root_ivr = ET.fromstring(res_ivr)
        for elem in root_ivr.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN" and elem.text and len(elem.text) >= 10:
                mdn = elem.text.strip()
    except: pass

    # שלב 3: בדיקת חבילות (רק אם יש MDN או אם הסים מזוהה)
    search_value = mdn if mdn else iccid
    res_pkg = call_soap("GetActivePackages", user, password, f"<MDN>{search_value}</MDN>")
    
    # ניתוח תוצאות
    found_plan = "לא זוהתה חבילה"
    try:
        root_pkg = ET.fromstring(res_pkg)
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "Description", "PlanName"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break
    except: pass

    # לוגיקת ההחלטה הסופית
    if is_active_in_system:
        is_correct = (found_plan.lower() == TARGET_PLAN.lower())
        if is_correct:
            return "תקין ✅", f"תוכנית: {found_plan}", True, res_pkg
        elif found_plan != "לא זוהתה חבילה":
            return "תוכנית שונה ❌", f"נמצאה תוכנית: {found_plan}", False, res_pkg
        else:
            return "פעיל - חסר מידע חבילה ⚠️", "הסים מזוהה במערכת אך ה-API לא מחזיר את שם התוכנית", False, res_pkg

    if "User does not have access" in res_pkg and not is_active_in_system:
        return "פנוי (Available)", "הסים לא נמצא במערכת המנויים", True, res_pkg

    return "שגיאה", "תגובה לא מזוהה מהשרת", False, res_pkg

# --- ממשק האתר ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת בדיקת סימים אוטומטית")

iccid_input = st.text_input("הכנס ICCID לבדיקה:")
if st.button("בדוק עכשיו 🚀"):
    with st.spinner("מבצע זיהוי..."):
        status, info, ok, raw = check_sim_logic(iccid_input, db['auth']['user'], db['auth']['pass'])
        if "תקין" in status: st.success(status)
        elif "פנוי" in status: st.info(status)
        else: st.error(status)
        st.info(info)
        with st.expander("ראה נתונים גולמיים"):
            st.code(raw, language="xml")

# ניהול רשימה
st.divider()
st.subheader("📋 רשימת מעקב")
c1, c2 = st.columns(2)
with c1: nid = st.text_input("הוסף ICCID")
with c2: nshop = st.text_input("חנות")
if st.button("הוסף"):
    if nid:
        db['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m")})
        save_db(db); st.rerun()

if db['sims']:
    st.dataframe(pd.DataFrame(db['sims']), use_container_width=True)
