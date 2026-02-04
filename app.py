import streamlit as st
import pandas as pd
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

# --- הגדרות ליבה ---
DB_FILE = "sim_database.json"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"
# הכתובת היציבה ביותר שהוכחה כעובדת בשרת שלך
API_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"sims": [], "auth": {"user": "", "pass": ""}, "history": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def call_soap_api(method, user, password, value):
    """שולח בקשת SOAP תקנית לשרת"""
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{method} xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      <mdn>{value}</mdn>
    </{method}>
  </soap:Body>
</soap:Envelope>"""

    # הוספת גרשיים ל-SOAPAction כפי שחלק מהשרתים דורשים
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"urn:telispire:MdnServices/{method}"'
    }

    try:
        response = requests.post(API_URL, data=soap_body, headers=headers, timeout=20)
        return response.text
    except Exception as e:
        return f"<error>{str(e)}</error>"

def check_sim_logic(iccid, user, password):
    """לוגיקה חכמה: בודק חבילה, ואם נכשל בגלל גישה - מסיק שהסים פנוי"""
    
    # 1. נסיון לקבל חבילות פעילות (המתודה המוכרת מהתיעוד)
    raw_res = call_soap_api("GetActivePackages", user, password, iccid)
    
    # אם השרת אומר שאין לו גישה ל-MDN (או ICCID במקרה הזה)
    if "User does not have access to MDN" in raw_res:
        return "פנוי (Available)", "הסים טרם הופעל או שאין קו משויך", True, raw_res
    
    # אם השרת לא מכיר את הפקודה (מקרה חירום)
    if "Server did not recognize" in raw_res:
        return "שגיאת הגדרה", "השרת לא תומך בפקודה זו בכתובת הנוכחית", False, raw_res

    # ניתוח שם התוכנית מה-XML
    try:
        root = ET.fromstring(raw_res)
        found_plan = "לא מזוהה"
        found_active = False

        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if tag in ["MasterCategory", "Description", "PlanName"]:
                if elem.text:
                    found_plan = elem.text.strip()
                    found_active = True
                    break

        if not found_active:
             return "פנוי / ללא חבילה", "הסים זוהה אך לא נמצאה תוכנית פעילה", True, raw_res

        is_correct = (found_plan == TARGET_PLAN)
        status = "תקין ✅" if is_correct else "תוכנית לא תואמת ❌"
        return status, found_plan, is_correct, raw_res

    except Exception as e:
        return "שגיאת ניתוח", str(e), False, raw_res

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="מערכת ניהול סימים", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש (User)", db['auth'].get('user', ''))
    p = st.text_input("סיסמה (Pass)", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת מעקב סימים - Wireless Provisioning")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה מיידית", "📋 ניהול רשימה", "📊 דוחות וריצה יומית"])

with tab1:
    st.subheader("בדיקת סים בזמן אמת")
    val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מתחבר לשרת..."):
            status, plan, ok, raw = check_sim_logic(val, db['auth']['user'], db['auth']['pass'])
            if ok: st.success(f"**סטטוס:** {status} | **תוכנית:** {plan}")
            else: st.error(f"**סטטוס:** {status} | **מידע:** {plan}")
            with st.expander("ראה נתונים גולמיים מהשרת"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("הוספת סימים למעקב")
    c1, c2 = st.columns(2)
    with c1: nid = st.text_input("ICCID")
    with c2: nshop = st.text_input("שם חנות")
    if st.button("הוסף למאגר"):
        if nid:
            db['sims'].append({"iccid": nid, "shop": nshop, "added": datetime.now().strftime("%d/%m/%Y")})
            save_db(db); st.rerun()

    if db['sims']:
        df = pd.DataFrame(db['sims'])
        st.dataframe(df, use_container_width=True)
        if st.button("מחק את כל הרשימה"):
            db['sims'] = []; save_db(db); st.rerun()

with tab3:
    st.subheader("בדיקה יומית מרוכזת")
    if st.button("הפעל בדיקה לכל הרשימה"):
        if not db['sims']:
            st.warning("הרשימה ריקה")
        else:
            results = []
            bar = st.progress(0)
            for i, sim in enumerate(db['sims']):
                res, plan, ok, _ = check_sim_logic(sim['iccid'], db['auth']['user'], db['auth']['pass'])
                results.append({
                    "תאריך": datetime.now().strftime("%d/%m/%Y"),
                    "חנות": sim['shop'],
                    "ICCID": sim['iccid'],
                    "תוצאה": res,
                    "תוכנית": plan
                })
                bar.progress((i + 1) / len(db['sims']))
                time.sleep(0.5)
            
            res_df = pd.DataFrame(results)
            st.dataframe(res_df)
            
            # יצירת קובץ להורדה
            csv = res_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 הורד דוח ריכוז (Excel/CSV)", csv, "sim_report.csv", "text/csv")
