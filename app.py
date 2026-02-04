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
    return {"sims": [], "auth": {"user": "", "pass": ""}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def call_soap_api(method, user, password, body_content):
    """פונקציה מתוקנת למניעת TypeError - מקבלת בדיוק את כמות הארגומנטים הנדרשת"""
    soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <{method} xmlns="urn:telispire:MdnServices">
      <username>{user}</username>
      <password>{password}</password>
      {body_content}
    </{method}>
  </soap:Body>
</soap:Envelope>"""

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
    """תהליך אוטומטי: המרת ICCID ל-MDN ואז בדיקת חבילה לפי התיעוד"""
    
    # 1. ניסיון לקבל מידע על המנוי כדי לחלץ MDN
    # הערה: חלק מהשרתים משתמשים ב-GetIVRLineInformation או SearchSubscribers
    raw_mdn_res = call_soap_api("GetIVRLineInformation", user, password, f"<mdn>{iccid}</mdn>")
    
    mdn = None
    try:
        root_mdn = ET.fromstring(raw_mdn_res)
        # חיפוש תגית MDN בתוצאה
        for elem in root_mdn.iter():
            tag = elem.tag.split('}')[-1]
            if tag == "MDN" and elem.text:
                mdn = elem.text.strip()
                break
    except: pass

    # אם לא נמצא MDN, נשתמש ב-ICCID עצמו כברירת מחדל (חלק מהשרתים מאפשרים זאת)
    search_value = mdn if mdn else iccid
    
    # 2. בדיקת חבילות פעילות (לפי התיעוד שצירפת)
    raw_res = call_soap_api("GetActivePackages", user, password, f"<MDN>{search_value}</MDN>")
    
    if "User does not have access to MDN" in raw_res:
        # כאן אנחנו יודעים בוודאות שהשרת דחה את המספר, לא ננחש שהוא פנוי
        return "שגיאת גישה", "אין הרשאה למספר זה בחשבון (או שהמספר שגוי)", False, raw_res

    try:
        root = ET.fromstring(raw_res)
        found_plan = "לא מזוהה"
        found_active = False

        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            # חיפוש ב-MasterCategory לפי התיעוד שלך
            if tag in ["MasterCategory", "Description", "PlanName"]:
                if elem.text and len(elem.text) > 2:
                    found_plan = elem.text.strip()
                    found_active = True
                    break

        if not found_active:
             return "פנוי (Available)", "לא נמצאה חבילה פעילה - הסים פנוי להפעלה", True, raw_res

        # בדיקה מדויקת של שם התוכנית
        is_correct = (found_plan.lower() == TARGET_PLAN.lower())
        status = "תקין ✅" if is_correct else "תוכנית שונה ❌"
        return status, f"תוכנית: {found_plan} (טלפון: {mdn if mdn else 'N/A'})", is_correct, raw_res

    except Exception as e:
        return "שגיאת ניתוח", f"לא ניתן לקרוא את תשובת השרת: {str(e)}", False, raw_res

# --- ממשק המשתמש (Streamlit) ---
st.set_page_config(page_title="ניהול סימים מקצועי", layout="wide")
db = load_db()

with st.sidebar:
    st.header("⚙️ הגדרות API")
    u = st.text_input("שם משתמש", db['auth'].get('user', ''))
    p = st.text_input("סיסמה", db['auth'].get('pass', ''), type="password")
    if st.button("שמור הגדרות"):
        db['auth'] = {"user": u, "pass": p}; save_db(db)
        st.success("נשמר!")

st.title("📱 מערכת מעקב ובדיקת סימים אוטומטית")

tab1, tab2, tab3 = st.tabs(["🔍 בדיקה בזמן אמת", "📋 ניהול רשימה", "📊 דוחות"])

with tab1:
    val = st.text_input("הכנס ICCID לבדיקה:")
    if st.button("בדוק עכשיו 🚀"):
        with st.spinner("מבצע זיהוי ובדיקת חבילה..."):
            status, plan, ok, raw = check_sim_logic(val, db['auth']['user'], db['auth']['pass'])
            if ok: st.success(f"**סטטוס:** {status} | **מידע:** {plan}")
            else: st.error(f"**סטטוס:** {status} | **מידע:** {plan}")
            with st.expander("ראה נתונים גולמיים (Debug)"):
                st.code(raw, language="xml")

with tab2:
    st.subheader("הוספת סימים למעקב קבוע")
    c1, c2 = st.columns(2)
    with c1: nid = st.text_input("ICCID")
    with c2: nshop = st.text_input("חנות")
    if st.button("הוסף למאגר"):
        if nid:
            db['sims'].append({"iccid": nid, "shop": nshop, "added": datetime.now().strftime("%d/%m/%Y")})
            save_db(db); st.rerun()

    if db['sims']:
        st.dataframe(pd.DataFrame(db['sims']), use_container_width=True)
        if st.button("מחק הכל"):
            db['sims'] = []; save_db(db); st.rerun()

with tab3:
    if st.button("הפעל בדיקה לכל הרשימה"):
        if not db['sims']: st.warning("הרשימה ריקה")
        else:
            results = []
            bar = st.progress(0)
            for i, sim in enumerate(db['sims']):
                res, plan, ok, _ = check_sim_logic(sim['iccid'], db['auth']['user'], db['auth']['pass'])
                results.append({"תאריך": datetime.now().strftime("%d/%m/%Y"), "חנות": sim['shop'], "ICCID": sim['iccid'], "תוצאה": res, "תוכנית": plan})
                bar.progress((i + 1) / len(db['sims']))
                time.sleep(0.5) # מניעת עומס
            
            res_df = pd.DataFrame(results)
            st.dataframe(res_df)
            st.download_button("📥 הורד דוח ריכוז (CSV)", res_df.to_csv(index=False).encode('utf-8-sig'), "sim_report.csv")
