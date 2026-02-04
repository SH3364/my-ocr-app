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
# הכתובת הרשמית והנכונה ל-API
API_URL = "https://api.wirelessprovisioning.com/publish/MdnServices.asmx"

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

def call_api_fixed(iccid, user, password):
    if not user or not password:
        return "חסר מידע", "נא להזין משתמש וסיסמה", False, ""

    # בניית ה-XML עם ה-Namespace המדויק
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

        # בדיקה אם יש שגיאת SOAP (כמו ששלחת)
        if "<soap:Fault>" in raw_res:
            return "שגיאת שרת (Fault)", "ה-API דחה את הבקשה. בדוק שם משתמש וסיסמה.", False, raw_res

        if response.status_code != 200:
            return f"שגיאה {response.status_code}", "תקשורת נכשלה", False, raw_res

        root = ET.fromstring(raw_res)
        
        # חיפוש TotalCount - רק אם הוא "0" באמת נגיד שפנוי
        total_count = None
        for elem in root.iter():
            if "TotalCount" in elem.tag:
                total_count = elem.text
                break
        
        if total_count == "0":
            return "פנוי (Available)", "הסים טרם הופעל", True, raw_res

        # חיפוש שם התוכנית
        found_plan = "לא זוהה"
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["PlanName", "RatePlanName", "RatePlan"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break

        if found_plan == "לא זוהה":
            return "פעיל - תוכנית לא ידועה", "הסים פעיל אך שם התוכנית לא חזר", False, raw_res

        is_correct = (found_plan == TARGET_PLAN)
        status = "תקין ✅" if is_correct else "תוכנית שגויה ❌"
        return status, found_plan, is_correct, raw_res

    except Exception as e:
        return "שגיאה טכנית", str(e), False, ""

# --- ממשק ---
st.set_page_config(page_title="מערכת סימים מושלמת", layout="wide")
db = load_db()

with st.sidebar:
    st.header("🔑 הגדרות התחברות")
    u = st.text_input("Username", db['auth'].get('user', ''))
    p = st.text_input("Password", db['auth'].get('pass', ''), type="password")
    if st.button("שמור"):
        db['auth'] = {"user": u, "pass": p}
        save_db(db)
        st.success("נשמר!")

st.title("📱 בדיקת סימים בזמן אמת")

iccid_input = st.text_input("הכנס ICCID לבדיקה:")
if st.button("בדוק עכשיו"):
    if iccid_input:
        with st.spinner("מתחבר..."):
            status, plan, ok, raw = call_api_fixed(iccid_input, db['auth']['user'], db['auth']['pass'])
            
            if "תקין" in status: st.success(f"**סטטוס:** {status} | **תוכנית:** {plan}")
            elif "פנוי" in status: st.info(f"**סטטוס:** {status}")
            else: st.error(f"**סטטוס:** {status} | **מידע:** {plan}")
            
            with st.expander("פרטים טכניים (במקרה של תקלה)"):
                st.code(raw, language="xml")
    else:
        st.warning("נא להזין מספר סים")

# ניהול רשימה פשוט למטה
st.divider()
st.subheader("📋 רשימת מעקב")
c1, c2 = st.columns(2)
with c1: nid = st.text_input("הוסף ICCID לרשימה")
with c2: nshop = st.text_input("שם חנות")
if st.button("הוסף לרשימה"):
    if nid:
        db['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m")})
        save_db(db)
        st.rerun()

if db['sims']:
    st.table(pd.DataFrame(db['sims']))
