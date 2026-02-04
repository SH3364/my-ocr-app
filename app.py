import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os

# הגדרות מערכת
REPORTS_DIR = 'reports'
DB_FILE = 'sim_database.csv'
SOAP_URL = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx'
TARGET_PLAN = 'Prepaid Refills - Talk Only - 4G HD'

# יצירת תיקיות וקבצים
if not os.path.exists(REPORTS_DIR): os.makedirs(REPORTS_DIR)
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=['תאריך הוספה', 'MDN', 'שם חנות']).to_csv(DB_FILE, index=False, encoding='utf-8-sig')

st.set_page_config(page_title='מערכת בדיקת סימים', layout='wide')

def call_soap_api(mdn, username, password):
    username = username.strip()
    password = password.strip()
    mdn = mdn.strip()
    
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
        response = requests.post(SOAP_URL, data=payload, headers=headers, timeout=20)
        raw_xml = response.text
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # חיפוש תגיות בצורה בטוחה
            res = {'Status': 'לא נמצאו נתונים', 'RatePlan': 'לא נמצאה תוכנית'}
            
            found_data = False
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1]
                if tag_name == 'Status': 
                    res['Status'] = elem.text
                    found_data = True
                if tag_name == 'RatePlan': 
                    res['RatePlan'] = elem.text
                    found_data = True
            
            # אם לא נמצאו סטטוס או תוכנית, נדווח שהמספר כנראה לא קיים במערכת
            if not found_data:
                return "חסר ב-API", "אין מידע", raw_xml
                
            return res['Status'], res['RatePlan'], raw_xml
        else:
            return "שגיאת שרת", f"קוד {response.status_code}", raw_xml
    except Exception as e:
        return "שגיאה טכנית", str(e), str(e)

# --- ממשק האתר ---
with st.sidebar:
    st.header('🔐 התחברות')
    api_user = st.text_input('שם משתמש API')
    api_pass = st.text_input('סיסמה', type='password')
    st.divider()
    show_debug = st.checkbox('הצג XML גולמי (למפתחים)')

tab1, tab2, tab3, tab4 = st.tabs(['📋 רשימת מספרים', '🔍 בדיקה מהירה', '🚀 בדיקת רשימה', '📂 היסטוריה'])

# טאב 1: ניהול רשימה
with tab1:
    st.subheader('הוספת מספרים למעקב')
    with st.form('add_form', clear_on_submit=True):
        col1, col2 = st.columns(2)
        m = col1.text_input('מספר (MDN)')
        s = col2.text_input('שם החנות')
        if st.form_submit_button('שמור במערכת'):
            if m and s:
                df = pd.read_csv(DB_FILE)
                new_row = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d %H:%M'), 'MDN': str(m), 'שם חנות': s}
                pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
                st.success(f'המספר {m} נשמר')
            else:
                st.warning('נא למלא את שני השדות')
    
    st.divider()
    st.subheader('כל המספרים במערכת')
    st.dataframe(pd.read_csv(DB_FILE), use_container_width=True)

# טאב 2: בדיקה מהירה
with tab2:
    st.subheader('בדיקת מספר ללא שמירה')
    q_mdn = st.text_input('הכנס מספר לבדיקה')
    if st.button('בדוק עכשיו'):
        if not api_user or not api_pass:
            st.error('נא להזין פרטי API בתפריט הצד')
        else:
            status, plan, raw = call_soap_api(q_mdn, api_user, api_pass)
            
            c1, c2 = st.columns(2)
            # לוגיקת הצלחה: פנוי או תוכנית נכונה
            if status == 'Available' or plan == TARGET_PLAN:
                c1.success(f"**סטטוס:** {status}")
                c2.success(f"**תוכנית:** {plan}")
                st.balloons()
            else:
                c1.error(f"**סטטוס:** {status}")
                c2.error(f"**תוכנית:** {plan}")
            
            if show_debug:
                with st.expander("נתונים טכניים מהשרת"):
                    st.code(raw, language='xml')

# טאב 3: בדיקת רשימה
with tab3:
    st.subheader('הרצת בדיקה על כל הטבלה')
    if st.button('🚀 התחל בדיקה'):
        df_sims = pd.read_csv(DB_FILE)
        if df_sims.empty:
            st.warning('הרשימה ריקה')
        else:
            results = []
            bar = st.progress(0)
            for i, row in df_sims.iterrows():
                status, plan, _ = call_soap_api(row['MDN'], api_user, api_pass)
                
                # לוגיקה סופית
                is_ok = "❌ נכשל"
                if status == 'Available': is_ok = "✅ פנוי"
                elif plan == TARGET_PLAN: is_ok = "✅ תוכנית תקינה"
                elif status == "חסר ב-API": is_ok = "❓ אין נתונים"
                
                results.append({
                    'תאריך בדיקה': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'MDN': row['MDN'],
                    'חנות': row['שם חנות'],
                    'סטטוס': status,
                    'תוכנית': plan,
                    'תוצאה סופית': is_ok
                })
                bar.progress((i + 1) / len(df_sims))
            
            res_df = pd.DataFrame(results)
            res_df.to_csv(f'{REPORTS_DIR}/last_check.csv', index=False, encoding='utf-8-sig')
            # שמירה גם להיסטוריה
            res_df.to_csv(f'{REPORTS_DIR}/report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv', index=False, encoding='utf-8-sig')
            st.dataframe(res_df, use_container_width=True)

# טאב 4: היסטוריה
with tab4:
    st.subheader('דוחות קודמים')
    files = sorted([f for f in os.listdir(REPORTS_DIR) if f.startswith('report_')], reverse=True)
    if files:
        selected = st.selectbox('בחר דוח לצפייה:', files)
        df_view = pd.read_csv(os.path.join(REPORTS_DIR, selected))
        st.dataframe(df_view, use_container_width=True)
        with open(os.path.join(REPORTS_DIR, selected), 'rb') as f:
            st.download_button('הורד דוח זה', f, file_name=selected)
    else:
        st.info('טרם בוצעו בדיקות')
