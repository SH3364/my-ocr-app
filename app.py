import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os

# הגדרות
REPORTS_DIR = 'reports'
DB_FILE = 'sim_database.csv'
SOAP_URL = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx'
TARGET_PLAN = 'Prepaid Refills - Talk Only - 4G HD'

if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR)
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=['תאריך הוספה', 'ICCID', 'שם חנות']).to_csv(DB_FILE, index=False, encoding='utf-8-sig')

st.set_page_config(page_title='בדיקת ICCID - מערכת סימים', layout='wide')

def call_soap_api(iccid, username, password):
    iccid = str(iccid).strip()
    payload = f'''<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <GetIVRLineInformation xmlns="urn:telispire:MdnServices">
          <username>{username.strip()}</username>
          <password>{password.strip()}</password>
          <mdn>{iccid}</mdn>
        </GetIVRLineInformation>
      </soap:Body>
    </soap:Envelope>'''
    
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'urn:telispire:MdnServices/GetIVRLineInformation'
    }
    
    try:
        response = requests.post(SOAP_URL, data=payload, headers=headers, timeout=20)
        raw_xml = response.text
        if response.status_code != 200:
            return "שגיאת שרת", "לא זמין", raw_xml

        root = ET.fromstring(response.content)
        res = {'Status': 'לא קיים ב-Wireless', 'RatePlan': 'אין תוכנית'}
        found_wireless = False

        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag == 'Status': 
                res['Status'] = elem.text
                found_wireless = True
            if tag == 'RatePlan': 
                res['RatePlan'] = elem.text
                found_wireless = True
        
        # אם הבלוק Wireless חסר, נבדוק אם יש אינדיקציה אחרת ב-XML
        if not found_wireless and '<GetIVRLineInformationResult>' in raw_xml:
            res['Status'] = 'מזוהה במערכת (ללא קו)'
            
        return res['Status'], res['RatePlan'], raw_xml
    except Exception as e:
        return "שגיאה", str(e), str(e)

# --- ממשק משתמש ---
with st.sidebar:
    st.header('🔐 התחברות')
    api_user = st.text_input('שם משתמש API')
    api_pass = st.text_input('סיסמה', type='password')
    show_debug = st.checkbox('הצג תשובת XML מלאה')

tab1, tab2, tab3, tab4 = st.tabs(['📋 ניהול ICCID', '🔍 בדיקה מיידית', '🚀 בדיקת כל הרשימה', '📂 היסטוריה'])

# טאב 1: ניהול
with tab1:
    with st.form('add_sim'):
        c1, c2 = st.columns(2)
        m = c1.text_input('מספר ICCID')
        s = c2.text_input('שם חנות')
        if st.form_submit_button('שמור סים במערכת'):
            df = pd.read_csv(DB_FILE)
            new_row = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d %H:%M'), 'ICCID': str(m), 'שם חנות': s}
            pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            st.success('נשמר')
    st.dataframe(pd.read_csv(DB_FILE), use_container_width=True)

# טאב 2: בדיקה מהירה
with tab2:
    q_iccid = st.text_input('הכנס ICCID לבדיקה')
    if st.button('בדוק עכשיו'):
        status, plan, raw = call_soap_api(q_iccid, api_user, api_pass)
        
        # הלוגיקה שלך: פנוי (Available) או תוכנית ספציפית
        is_ok = (status == 'Available' or plan == TARGET_PLAN)
        
        col1, col2 = st.columns(2)
        if is_ok:
            col1.success(f"**סטטוס:** {status}")
            col2.success(f"**תוכנית:** {plan}")
        else:
            col1.error(f"**סטטוס:** {status}")
            col2.error(f"**תוכנית:** {plan}")
            st.warning("שים לב: אם הסטטוס הוא 'לא קיים ב-Wireless', ה-API מזהה את הסים אך הוא טרם הופעל.")

        if show_debug:
            st.code(raw, language='xml')

# טאב 3: בדיקת רשימה
with tab3:
    if st.button('🚀 הרץ בדיקה על כל מספרי ה-ICCID'):
        df_sims = pd.read_csv(DB_FILE)
        results = []
        bar = st.progress(0)
        for i, row in df_sims.iterrows():
            status, plan, _ = call_soap_api(row['ICCID'], api_user, api_pass)
            final = "✅ תקין" if (status == 'Available' or plan == TARGET_PLAN) else "❌ דורש בדיקה"
            results.append({
                'תאריך': datetime.now().strftime('%d/%m/%Y'),
                'ICCID': row['ICCID'],
                'חנות': row['שם חנות'],
                'סטטוס': status,
                'תוכנית': plan,
                'תוצאה': final
            })
            bar.progress((i + 1) / len(df_sims))
        
        res_df = pd.DataFrame(results)
        res_df.to_csv(f'{REPORTS_DIR}/report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv', index=False, encoding='utf-8-sig')
        st.dataframe(res_df, use_container_width=True)

# טאב 4: היסטוריה
with tab4:
    files = sorted([f for f in os.listdir(REPORTS_DIR) if f.startswith('report_')], reverse=True)
    if files:
        selected = st.selectbox('בחר בדיקה מהעבר:', files)
        st.dataframe(pd.read_csv(os.path.join(REPORTS_DIR, selected)), use_container_width=True)
