import streamlit as st
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import os

# הגדרות נתיבים
REPORTS_DIR = 'reports'
DB_FILE = 'sim_database.csv'
SOAP_URL = 'https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx'
TARGET_PLAN = 'Prepaid Refills - Talk Only - 4G HD'

# יצירת תשתיות אם אינן קיימות
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)
if not os.path.exists(DB_FILE):
    df_empty = pd.DataFrame(columns=['תאריך הוספה', 'MDN', 'שם חנות'])
    df_empty.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

st.set_page_config(page_title='ניהול מערך סימים', layout='wide')

# פונקציית ה-API המקורית מהתיעוד
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
    headers = {'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': 'urn:telispire:MdnServices/GetIVRLineInformation'}
    try:
        response = requests.post(SOAP_URL, data=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            status, plan = 'Unknown', 'Unknown'
            for elem in root.iter():
                if 'Status' in elem.tag: status = elem.text
                if 'RatePlan' in elem.tag: plan = elem.text
            return status, plan
        return 'Error', f'שרת החזיר קוד {response.status_code}'
    except Exception as e:
        return 'Error', str(e)

# תפריט צד להגדרות
with st.sidebar:
    st.header('🔑 הגדרות התחברות')
    api_user = st.text_input('שם משתמש API')
    api_pass = st.text_input('סיסמה', type='password')
    st.info('הנתונים אינם נשמרים בדפדפן מטעמי אבטחה.')

# יצירת טאבים לניווט נוח
tab1, tab2, tab3, tab4 = st.tabs(['📝 ניהול רשימה', '⚡ בדיקה מהירה', '🚀 הרצת בדיקה כללית', '📜 היסטוריית דוחות'])

# --- טאב 1: ניהול רשימת המספרים ---
with tab1:
    st.subheader('הוספת מספר חדש למערכת')
    with st.form('add_sim_form', clear_on_submit=True):
        col1, col2 = st.columns(2)
        new_mdn = col1.text_input('מספר MDN')
        new_store = col2.text_input('שם החנות')
        submit = st.form_submit_button('הוסף לרשימה')
        
        if submit and new_mdn and new_store:
            df = pd.read_csv(DB_FILE)
            new_row = {'תאריך הוספה': datetime.now().strftime('%Y-%m-%d %H:%M'), 'MDN': str(new_mdn), 'שם חנות': new_store}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
            st.success(f'המספר {new_mdn} נוסף בהצלחה!')

    st.divider()
    st.subheader('רשימת המספרים הקיימת')
    df_list = pd.read_csv(DB_FILE)
    st.dataframe(df_list, use_container_width=True)

# --- טאב 2: בדיקה מיידית ---
with tab2:
    st.subheader('בדיקה מהירה למספר בודד (ללא שמירה)')
    quick_mdn = st.text_input('הכנס מספר לבדיקה מיידית')
    if st.button('בדוק עכשיו'):
        if not api_user or not api_pass:
            st.error('נא להזין פרטי API בתפריט הצד')
        else:
            with st.spinner('בודק...'):
                status, plan = call_soap_api(quick_mdn, api_user, api_pass)
                col1, col2 = st.columns(2)
                col1.metric('סטטוס', status)
                col2.metric('תוכנית', plan)

# --- טאב 3: הרצת בדיקה כללית ---
with tab3:
    st.subheader('הרצת בדיקה על כל הרשימה השמורה')
    if st.button('🚀 התחל בדיקה מקיפה'):
        df_sims = pd.read_csv(DB_FILE)
        if df_sims.empty:
            st.warning('הרשימה ריקה. הוסף מספרים בטאב "ניהול רשימה".')
        elif not api_user or not api_pass:
            st.error('נא להזין פרטי API בתפריט הצד')
        else:
            results = []
            progress = st.progress(0)
            for i, row in df_sims.iterrows():
                status, plan = call_soap_api(row['MDN'], api_user, api_pass)
                is_ok = (status == 'Available' or plan == TARGET_PLAN)
                results.append({
                    'זמן בדיקה': datetime.now().strftime('%H:%M:%S'),
                    'MDN': row['MDN'],
                    'חנות': row['שם חנות'],
                    'סטטוס': status,
                    'תוכנית': plan,
                    'תוצאה': '✅ תקין' if is_ok else '❌ שגיאה'
                })
                progress.progress((i + 1) / len(df_sims))
            
            res_df = pd.DataFrame(results)
            fname = f'{REPORTS_DIR}/report_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
            res_df.to_csv(fname, index=False, encoding='utf-8-sig')
            st.success('הבדיקה הסתיימה והדוח נשמר!')
            st.dataframe(res_df, use_container_width=True)

# --- טאב 4: היסטוריית דוחות ---
with tab4:
    st.subheader('צפייה בדוחות קודמים')
    report_files = sorted([f for f in os.listdir(REPORTS_DIR) if f.endswith('.csv')], reverse=True)
    
    if report_files:
        selected_file = st.selectbox('בחר דוח לצפייה:', report_files)
        if selected_file:
            report_path = os.path.join(REPORTS_DIR, selected_file)
            view_df = pd.read_csv(report_path)
            
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.write(f'מציג נתונים מתוך: {selected_file}')
            with col_b:
                with open(report_path, 'rb') as f:
                    st.download_button('📥 הורד כ-CSV', f, file_name=selected_file)
            
            st.dataframe(view_df, use_container_width=True)
    else:
        st.info('עדיין לא בוצעו בדיקות כלליות.')
