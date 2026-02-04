import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os

# הגדרות שרת ו-API
SOAP_URL = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx'
TARGET_PLAN = 'Prepaid Refills - Talk Only - 4G HD'
REPORTS_DIR = 'reports'

# יצירת תיקיית דוחות אם אינה קיימת
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

st.set_page_config(page_title='מערכת ניהול סימים', layout='centered')
st.title('📊 מערכת ניהול ובדיקת סימים')

# פונקציית ה-API
def call_soap_api(mdn, username, password):
    payload = f'''<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetIVRLineInformation xmlns="urn:telispire:MdnServices">
          <username>{username}</username>
          <password>{password}</password>
          <mdn>{mdn}</mdn>
        </GetIVRLineInformation>
      </soap:Body>
    </soap:Envelope>'''
    
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'urn:telispire:MdnServices/GetIVRLineInformation'
    }
    
    try:
        response = requests.post(SOAP_URL, data=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            status, plan = 'Unknown', 'Unknown'
            for elem in root.iter():
                if 'Status' in elem.tag: status = elem.text
                if 'RatePlan' in elem.tag: plan = elem.text
            return status, plan
        return 'Error', f'Server returned {response.status_code}'
    except Exception as e:
        return 'Error', str(e)

# ממשק צד
with st.sidebar:
    st.header('הגדרות התחברות')
    api_user = st.text_input('שם משתמש API')
    api_pass = st.text_input('סיסמה', type='password')

# רשימת הסימים שלך
SIM_LIST = [
    {'mdn': '1234567890', 'store': 'חנות א'},
    {'mdn': '0987654321', 'store': 'חנות ב'}
]

if st.button('🚀 הרץ בדיקה לכל הרשימה'):
    if not api_user or not api_pass:
        st.error('חובה להזין שם משתמש וסיסמה בתפריט הצד!')
    else:
        results = []
        bar = st.progress(0)
        
        for i, sim in enumerate(SIM_LIST):
            status, plan = call_soap_api(sim['mdn'], api_user, api_pass)
            is_ok = (status == 'Available' or plan == TARGET_PLAN)
            results.append({
                'תאריך': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'MDN': sim['mdn'],
                'חנות': sim['store'],
                'סטטוס': status,
                'תוכנית': plan,
                'תוצאה': 'תקין' if is_ok else 'דורש טיפול'
            })
            bar.progress((i + 1) / len(SIM_LIST))
        
        df = pd.DataFrame(results)
        # תיקון השגיאה שהייתה כאן - שימוש בגרש בודד למניעת התנגשות עם הגרשיים של הדו"ח
        filename = f'{REPORTS_DIR}/report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        st.success('הבדיקה הושלמה! הדו"ח נשמר בהצלחה.')
        st.dataframe(df)

st.divider()
st.subheader('📁 הורדת דוחות קודמים מהאתר')

# הצגת כל הקבצים שנוצרו אי פעם בתיקיית reports
if os.path.exists(REPORTS_DIR):
    files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')], reverse=True)
    if files:
        for file in files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f'📄 {file}')
            with col2:
                with open(os.path.join(REPORTS_DIR, file), 'rb') as f:
                    st.download_button(label='הורד', data=f, file_name=file, mime='text/csv', key=file)
    else:
        st.info('טרם נוצרו דוחות. הרץ בדיקה כדי לראות קבצים כאן.')
