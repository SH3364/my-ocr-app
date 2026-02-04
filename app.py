import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

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

# --- פונקציית העל: בדיקה אוטומטית דו-שלבית ---
def auto_check_sim(iccid, user, password):
    if not user or not password:
        return "שגיאה", "חסר שם משתמש/סיסמה", False, ""

    # --- שלב 1: קבלת MDN לפי ICCID ---
    get_mdn_soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetMDNByICCID xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      <ICCID>{iccid}</ICCID>
    </GetMDNByICCID>
  </soap:Body>
</soap:Envelope>"""

    headers_mdn = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/GetMDNByICCID"
    }

    try:
        res_mdn = requests.post(API_URL, data=get_mdn_soap, headers=headers_mdn, timeout=15)
        root_mdn = ET.fromstring(res_mdn.text)
        
        found_mdn = None
        for elem in root_mdn.iter():
            if "GetMDNByICCIDResult" in elem.tag or "MDN" in elem.tag:
                if elem.text and len(elem.text) >= 10:
                    found_mdn = elem.text.strip()
                    break

        if not found_mdn:
            return "סים לא מזוהה", "השרת לא מצא מספר טלפון משויך לסים זה (ייתכן שאינו פעיל)", False, res_mdn.text

        # --- שלב 2: בדיקת חבילות לפי ה-MDN שנמצא ---
        get_pkg_soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetActivePackages xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      <MDN>{found_mdn}</MDN>
    </GetActivePackages>
  </soap:Body>
</soap:Envelope>"""

        headers_pkg = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "urn:telispire:MdnServices/GetActivePackages"
        }

        res_pkg = requests.post(API_URL, data=get_pkg_soap, headers=headers_pkg, timeout=15)
        root_pkg = ET.fromstring(res_pkg.text)
        
        found_plan = "ללא חבילה"
        for elem in root_pkg.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "PlanName"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break

        is_correct = (TARGET_PLAN.lower() in found_plan.lower())
        status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
        
        detail = f"טלפון: {found_mdn} | תוכנית: {found_plan}"
        return status, detail, is_correct, res_pkg.text

    except Exception as e:
        return "שגיאה טכנית", str(e), False, ""

# --- ממשק Streamlit ---
st.set_page_config(page_title="בדיקת סימים אוטומטית", layout="wide")
db = load_db()

with st.sidebar:
    st.header("🔑 הגדרות API")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור"):
        db['auth'] = {"user": u, "pass": p}
        save_db(db)
        st.success("נשמר!")

st.title("📱 בדיקת סים אוטומטית (ICCID ➔ MDN ➔ Plan)")

iccid_input = st.text_input("הכנס מספר סים (ICCID):")

if st.button("הפעל בדיקה אוטומטית 🚀"):
    if iccid_input:
        with st.spinner("מחלץ מספר טלפון ובודק חבילה..."):
            status, detail, ok, raw = auto_check_sim(iccid_input, db['auth']['user'], db['auth']['pass'])
            
            if ok:
                st.success(f"**{status}**")
                st.info(detail)
            else:
                st.error(f"**{status}**")
                st.warning(detail)
            
            with st.expander("נתוני API גולמיים (שלב ב')"):
                st.code(raw, language="xml")
