import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os

# הגדרות בסיסיות מהתיעוד
SOAP_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
REPORTS_DIR = "reports"

# וודא שתיקיית הדוחות קיימת
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

st.set_page_config(page_title="מערכת ניהול סימים", layout="centered")
st.title("📊 מערכת ניהול ובדיקת סימים")

# פונקציית ה-API לפי התיעוד שסיפקת
def call_soap_api(mdn, username, password):
    payload = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetIVRLineInformation xmlns="urn:telispire:MdnServices">
          <username>{username}</username>
          <password>{password}</password>
          <mdn>{mdn}</mdn>
        </GetIVRLineInformation>
      </soap:Body>
    </soap:Envelope>"""
    
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "urn:telispire:MdnServices/GetIVRLineInformation"
    }
    
    response = requests.post(SOAP_URL, data=payload, headers=headers)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        # חילוץ נתונים (שימוש בחיפוש גנרי למניעת בעיות Namespace)
        status = "Unknown"
        plan = "Unknown"
        for elem in root.iter():
            if 'Status' in elem.tag: status = elem.text
            if 'RatePlan' in elem.tag: plan = elem.text
        return status, plan
    return "Error", "Connection Failed"

# ממשק משתמש להגדרות
with st.sidebar:
    st.header("הגדרות API")
    api_user = st.text_input("שם משתמש", type="default")
    api_pass = st.text_input("סיסמה", type="password")

# רשימת סימים (ניתן לעדכן כאן)
SIM_LIST = [
    {"mdn": "1234567890", "store": "חנות א"},
    {"mdn": "0987654321", "store": "חנות ב"}
]

if st.button("🚀 הרץ בדיקה עכשיו"):
    if not api_user or not api_pass:
        st.error("נא להזין שם משתמש וסיסמה בתפריט הצד")
    else:
        results = []
        progress_bar = st.progress(0)
        
        for i, sim in enumerate(SIM_LIST):
            status, plan = call_soap_api(sim['mdn'], api_user, api_pass)
            is_ok = (status == "Available" or plan == TARGET_PLAN)
            results.append({
                "תאריך": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "MDN": sim['mdn'],
                "חנות": sim['store'],
                "סטטוס": status,
                "תוכנית": plan,
                "תוצאה": "תקין" if is_ok else "שגיאה"
            })
            progress_bar.progress((i + 1) / len(SIM_LIST))
        
        # שמירת הדו"ח
        df = pd.DataFrame(results)
        filename = f"{REPORTS_DIR}/report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        st.success(f"הבדיקה הושלמה! הדו"ח נשמר.")
        st.dataframe(df)

st.divider()
st.subheader("📁 דוחות קודמים להורדה")

# הצגת קבצים להורדה
files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')], reverse=True)
if files:
    for file in files:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"📄 {file}")
        with col2:
            with open(f"{REPORTS_DIR}/{file}", "rb") as f:
                st.download_button(
                    label="הורד",
                    data=f,
                    file_name=file,
                    mime="text/csv",
                    key=file
                )
else:
    st.info("אין עדיין דוחות זמינים. הרץ בדיקה כדי ליצור דוח ראשון.")
