import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# --- הגדרות בסיסיות ---
DB_FILE = "database.json"
SOAP_URL = "https://api.wirelessprovisioning.com/publish/MdnServices.asmx"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"

# --- פונקציות עזר ---
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def call_sim_api(iccid, user, password):
    if not user or not password:
        return "Error", "נא להגדיר משתמש וסיסמה בתפריט הצד", False
    
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

    headers = {{
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/SearchSubscribers"
    }}

    try:
        response = requests.post(SOAP_URL, data=soap_body, headers=headers, timeout=20)
        root = ET.fromstring(response.text)
        ns = {{'ns': 'urn:telispire:MdnServices'}}
        
        count_elem = root.find(".//ns:TotalCount", ns)
        if count_elem is not None and count_elem.text == "0":
            return "פנוי", "אין קו פעיל", True

        plan_elem = root.find(".//ns:PlanName", ns)
        current_plan = plan_elem.text if plan_elem is not None else "לא ידוע"
        
        is_ok = (current_plan == TARGET_PLAN)
        return "פעיל" if is_ok else "תוכנית שגויה", current_plan, is_ok
    except Exception as e:
        return "שגיאה", str(e), False

# --- ממשק האתר ---
st.set_page_config(page_title="מערכת ניהול סימים", layout="wide")
data = load_data()

# איפה מגדירים API? בסרגל הצד (Sidebar)
with st.sidebar:
    st.header("🔑 הגדרות API")
    st.write("כאן מגדירים את החיבור ל-Wireless Provisioning")
    user_input = st.text_input("שם משתמש", data['auth'].get('user', ''))
    pass_input = st.text_input("סיסמה", data['auth'].get('pass', ''), type="password")
    
    if st.button("שמור הגדרות"):
        data['auth'] = {"user": user_input, "pass": pass_input}
        save_data(data)
        st.success("ההגדרות נשמרו בהצלחה!")

st.title("📱 ניהול ובדיקת סימים")

# הוספת סים
with st.container():
    st.subheader("➕ הוספת סים חדש")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        new_iccid = st.text_input("מספר ICCID", key="iccid_input")
    with col2:
        new_shop = st.text_input("שם חנות", key="shop_input")
    with col3:
        st.write(" ") # יישור
        if st.button("הוסף לרשימה"):
            if new_iccid and new_shop:
                data['sims'].append({
                    "iccid": new_iccid, 
                    "shop": new_shop, 
                    "date": datetime.now().strftime("%d/%m/%Y")
                })
                save_data(data)
                st.success("נוסף!")
                st.rerun()

# הצגת נתונים ובדיקה מיידית
st.divider()
if data['sims']:
    df = pd.DataFrame(data['sims'])
    st.subheader("📋 רשימת הסימים שלך")
    st.dataframe(df, use_container_width=True)

    st.subheader("🔍 בדיקה מיידית")
    selected_iccid = st.selectbox("בחר סים לבדיקה", [s['iccid'] for s in data['sims']])
    if st.button("בדוק סים זה עכשיו"):
        with st.spinner("מתחבר ל-API..."):
            status, plan, ok = call_sim_api(selected_iccid, data['auth']['user'], data['auth']['pass'])
            if ok:
                st.success(f"תוצאה: {status} | תוכנית: {plan}")
            else:
                st.error(f"תוצאה: {status} | תוכנית: {plan}")
else:
    st.info("הרשימה ריקה. הוסף סים למעלה.")

# דוחות
st.divider()
st.subheader("📂 דוחות")
reports = [f for f in os.listdir(".") if f.startswith("report_")]
if reports:
    selected_report = st.selectbox("בחר דוח להורדה", sorted(reports, reverse=True))
    with open(selected_report, "rb") as f:
        st.download_button("📥 הורד קובץ CSV", f, file_name=selected_report)
