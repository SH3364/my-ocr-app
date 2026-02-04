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
    pd.DataFrame(columns=['תאריך הוספה', 'MDN', 'שם חנות']).to_csv(DB_FILE, index=False, encoding='utf-8-sig')

st.set_page_config(page_title='בדיקת סימים - Wireless Provisioning', layout='wide')

def call_soap_api(mdn, username, password):
    # ניקוי רווחים משם המשתמש והסיסמה
    username = username.strip()
    password = password.strip()
    
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
            # פענוח XML בצורה חזקה יותר
            root = ET.fromstring(response.content)
            res = {'Status': 'Not Found', 'RatePlan': 'Not Found'}
            
            # חיפוש התגים בתוך ה-XML ללא קשר ל-Namespace
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] # מסיר את ה-Namespace אם קיים
                if tag_name == 'Status': res['Status'] = elem.text
                if tag_name == 'RatePlan': res['RatePlan'] = elem.text
            
            return res['Status'], res['RatePlan'], raw_xml
        else:
            return 'Error', f'Server Error {response.status_code}', raw_xml
    except Exception as e:
        return 'Error', str(e), str(e)

# --- ממשק משתמש ---
with st.sidebar:
    st.header('🔑 פרטי התחברות')
    api_user = st.text_input('שם משתמש API')
    api_pass = st.text_input('סיסמה', type='password')
    show_debug = st.checkbox('הצג לוג טכני (במקרה של שגיאה)')

tab1, tab2, tab3, tab4 = st.tabs(['📝 ניהול רשימה', '⚡ בדיקה מהירה', '🚀 בדיקה כללית', '📜 היסטוריה'])

# טאב 1: ניהול רשימה
with tab1:
    with st.form('add_sim'):
        c1, c2 = st.columns(2)
        m = c1.text_input('מספר MDN')
        s = c2.text_input('שם חנות')
        if st.form_submit_button('הוסף לרשימה'):
            df = pd.read_csv(DB_FILE)
            new_row = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d %H:%M'), 'MDN': str(m), 'שם חנות': s}
            pd.concat([df, pd.DataFrame([new_row])], ignore_index=True).to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            st.success('נוסף בהצלחה')
    st.dataframe(pd.read_csv(DB_FILE), use_container_width=True)

# טאב 2: בדיקה מהירה
with tab2:
    q_mdn = st.text_input('מספר לבדיקה מיידית')
    if st.button('בדוק עכשיו'):
        st.write('---')
        status, plan, raw = call_soap_api(q_mdn, api_user, api_pass)
        
        # לוגיקת הבדיקה שביקשת
        is_free = (status == 'Available')
        is_correct_plan = (plan == TARGET_PLAN)
        
        if is_free:
            st.success(f'✅ המספר פנוי! (סטטוס: {status})')
        elif is_correct_plan:
            st.success(f'✅ המספר תקין עם התוכנית הדרושה. (תוכנית: {plan})')
        else:
            st.error(f'❌ הבדיקה נכשלה. סטטוס: {status} | תוכנית: {plan}')
            
        if show_debug:
            with st.expander("ראה תשובה גולמית מהשרת"):
                st.code(raw, language='xml')

# טאב 3: בדיקה כללית
with tab3:
    if st.button('🚀 הרץ בדיקה על כל הרשימה'):
        df_sims = pd.read_csv(DB_FILE)
        results = []
        bar = st.progress(0)
        
        for i, row in df_sims.iterrows():
            status, plan, _ = call_soap_api(row['MDN'], api_user, api_pass)
            
            # קביעת תוצאה לפי הלוגיקה שלך
            final_res = '❌ נכשל'
            if status == 'Available': final_res = '✅ פנוי'
            elif plan == TARGET_PLAN: final_res = '✅ תוכנית תקינה'
            
            results.append({
                'זמן': datetime.now().strftime('%H:%M'),
                'MDN': row['MDN'],
                'חנות': row['שם חנות'],
                'סטטוס מהשרת': status,
                'תוכנית מהשרת': plan,
                'תוצאה סופית': final_res
            })
            bar.progress((i + 1) / len(df_sims))
            
        res_df = pd.DataFrame(results)
        fname = f'{REPORTS_DIR}/report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        res_df.to_csv(fname, index=False, encoding='utf-8-sig')
        st.dataframe(res_df, use_container_width=True)

# טאב 4: היסטוריה
with tab4:
    files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')], reverse=True)
    if files:
        selected = st.selectbox('בחר דוח:', files)
        df_view = pd.read_csv(os.path.join(REPORTS_DIR, selected))
        st.dataframe(df_view, use_container_width=True)
        with open(os.path.join(REPORTS_DIR, selected), 'rb') as f:
            st.download_button('הורד דוח זה', f, file_name=selected)
