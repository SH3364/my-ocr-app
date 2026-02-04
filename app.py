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

# רשימת כתובות API אפשריות (כי לכל מפיץ יש כתובת אחרת)
API_URLS = {
    "אפשרות 1 (הכי נפוץ)": "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx",
    "אפשרות 2 (חדש)": "https://api.wirelessprovisioning.com/publish/MdnServices.asmx",
    "אפשרות 3 (חלופי)": "https://api.wirelessprovisioning.com/MdnServices.asmx"
}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"sims": [], "auth": {"user": "", "pass": "", "url": list(API_URLS.values())[0]}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def call_api(iccid, user, password, url):
    # ננסה קודם את SearchSubscribers שהיא הכי מפורטת
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
        response = requests.post(url, data=soap_body, headers=headers, timeout=15)
        
        if response.status_code == 404:
            return "שגיאה 404", "הכתובת לא נכונה. נסה להחליף 'שרת API' בתפריט הצד.", False, response.text
        
        if response.status_code != 200:
            return f"שגיאה {response.status_code}", "תקשורת נכשלה", False, response.text

        raw_res = response.text
        root = ET.fromstring(raw_res)
        
        # חיפוש שם התוכנית בכל התגיות האפשריות
        found_plan = "לא נמצא"
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["PlanName", "RatePlanName", "RatePlan"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    break

        if found_plan == "לא נמצא":
            # אם לא מצאנו שם תוכנית, נבדוק אם ה-API לפחות החזיר תשובה חיובית
            if "SearchSubscribersResult" in raw_res:
                return "פנוי / לא הופעל", "הסים נמצא אך אין עליו תוכנית פעילה", True, raw_res
            return "מידע חסר", "השרת ענה אך לא שלח פרטי תוכנית", False, raw_res

        is_correct = (found_plan == TARGET_PLAN)
        status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
        return status, found_plan, is_correct, raw_res

    except Exception as e:
        return "שגיאה טכנית", str(e), False, ""

# --- ממשק ---
st.set_page_config(page_title="בדיקת סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות חיבור")
    # בחירת שרת - הפתרון ל-404
    selected_url_name = st.selectbox("בחר שרת API:", list(API_URLS.keys()))
    current_url = API_URLS[selected_url_name]
    
    u = st.text_input("שם משתמש (User/Email)", db['auth'].get('user', ''))
    p = st.text_input("סיסמה (Password)", db['auth'].get('pass', ''), type="password")
    
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p, "url": current_url}
        save_db(db)
        st.success("הגדרות נשמרו!")

st.title("📱 מערכת בדיקת סימים WP")

# בדיקה בזמן אמת
st.subheader("🔍 בדיקה מיידית")
test_iccid = st.text_input("הכנס ICCID לבדיקה:")
if st.button("בדוק עכשיו"):
    with st.spinner("מבצע שאילתה..."):
        status, plan, ok, raw = call_api(test_iccid, db['auth']['user'], db['auth']['pass'], current_url)
        
        if ok: st.success(f"**סטטוס:** {status} | **תוכנית:** {plan}")
        else: st.error(f"**סטטוס:** {status} | **מידע:** {plan}")
        
        with st.expander("ראה תשובה גולמית מהשרת (לפתרון תקלות)"):
            st.code(raw, language="xml")

st.divider()

# ניהול רשימה
st.subheader("📋 רשימת מעקב וחנות")
c1, c2 = st.columns(2)
with c1: nid = st.text_input("הוסף ICCID")
with c2: nshop = st.text_input("שם חנות")
if st.button("הוסף לרשימה"):
    if nid:
        db['sims'].append({"iccid": nid, "shop": nshop, "date": datetime.now().strftime("%d/%m")})
        save_db(db)
        st.rerun()

if db['sims']:
    st.table(pd.DataFrame(db['sims']))
