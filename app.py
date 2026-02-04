import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- הגדרות קבועות ---
DB_FILE = "sim_database.json"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
# הכתובת שהוכיחה את עצמה כעובדת אצלך (מונע 404)
SOAP_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"

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

def call_api_final(iccid, user, password):
    if not user or not password:
        return "שגיאה", "חסר שם משתמש/סיסמה בתפריט הצד", False, ""

    # שימוש ב-SearchSubscribers - הדרך הכי בטוחה לראות את שם התוכנית
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
        response = requests.post(SOAP_URL, data=soap_body, headers=headers, timeout=20)
        
        if response.status_code == 404:
            return "שגיאה 404", "השרת לא מצא את הכתובת. נסה להשתמש בכתובת ה-API החלופית.", False, response.text
        
        root = ET.fromstring(response.text)
        
        # חיפוש אגרסיבי של שם התוכנית
        found_plan = "לא זוהה"
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1]
            if tag_name in ["PlanName", "RatePlanName", "RatePlan"]:
                if elem.text and len(elem.text) > 2:
                    found_plan = elem.text.strip()
                    break
        
        # בדיקה אם נמצאו תוצאות בכלל
        total_count = "0"
        for elem in root.iter():
            if "TotalCount" in elem.tag:
                total_count = elem.text
                break

        if total_count == "0" and found_plan == "לא זוהה":
            return "פנוי (Available)", "הסים פנוי או שלא נמצא מנוי תואם", True, response.text

        is_correct = (found_plan == TARGET_PLAN)
        status = "תקין ✅" if is_correct else "תוכנית לא תואמת ❌"
        return status, found_plan, is_correct, response.text

    except Exception as e:
        return "שגיאת חיבור", str(e), False, ""

# --- ממשק האתר ---
st.set_page_config(page_title="ניהול סימים", layout="wide")
data = load_db()

with st.sidebar:
    st.header("🔑 הגדרות API")
    st.warning("שים לב: שם המשתמש הוא המייל שלך למערכת!")
    u = st.text_input("שם משתמש API", data['auth'].get('user', ''))
    p = st.text_input("סיסמה API", data['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        data['auth'] = {"user": u, "pass": p}
        save_db(data)
        st.success("נשמר!")

st.title("📱 מערכת בדיקת סימים - גרסה סופית")

tab1, tab2 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 רשימת מעקב"])

with tab1:
    input_sim = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מתחבר לשרת..."):
            status, plan, ok, raw = call_api_final(input_sim, data['auth']['user'], data['auth']['pass'])
            if ok: st.success(f"**תוצאה:** {status} | **תוכנית:** {plan}")
            else: st.error(f"**תוצאה:** {status} | **תוכנית:** {plan}")
            
            with st.expander("ראה תשובה טכנית (למקרה של ספק)"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("ניהול רשימת סימים")
    # כאן נשארת הלוגיקה של הוספת סימים וטבלה...
    c1, c2 = st.columns(2)
    with c1: new_id = st.text_input("מספר סים")
    with c2: new_sh = st.text_input("שם חנות")
    if st.button("הוסף"):
        if new_id:
            data['sims'].append({"iccid": new_id, "shop": new_sh, "date": datetime.now().strftime("%d/%m/%Y")})
            save_db(data)
            st.rerun()
    if data['sims']:
        st.table(pd.DataFrame(data['sims']))
