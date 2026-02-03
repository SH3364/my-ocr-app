
import requests
import xml.etree.ElementTree as ET
import os
import csv
from datetime import datetime

# הגדרות
SOAP_URL = "https://wirelessprovisioning.com/desktopmodules/telispire.webservices/mdnservices.asmx"
TARGET_PLAN = "Prepaid Refills - Talk Only - 4G HD"

# רשימת סימים (ניתן להוציא לקובץ נפרד בעתיד)
SIM_DATABASE = [
    {"mdn": "1234567890", "store": "חנות א"},
    {"mdn": "0987654321", "store": "חנות ב"},
]

def check_sim(username, password, mdn):
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

    try:
        response = requests.post(SOAP_URL, data=payload, headers=headers)
        response.raise_for_status()
        
        # פענוח ה-XML (בהתאם לתיעוד ששלחת)
        root = ET.fromstring(response.content)
        # חיפוש גנרי של התגים בתוך ה-Namespace
        namespaces = {'ns': 'urn:telispire:MdnServices'}
        
        status = "N/A"
        rate_plan = "N/A"
        
        for elem in root.iter():
            if 'Status' in elem.tag: status = elem.text
            if 'RatePlan' in elem.tag: rate_plan = elem.text
            
        return status, rate_plan
    except Exception as e:
        return "Error", str(e)

def main():
    # קריאת נתונים מ-GitHub Secrets (אבטחה)
    user = os.getenv("API_USER")
    pw = os.getenv("API_PASS")
    
    report_file = f"reports/report_{datetime.now().strftime('%Y-%m-%d')}.csv"
    os.makedirs("reports", exist_ok=True)
    
    results = []
    failed_sims = []

    for item in SIM_DATABASE:
        status, plan = check_sim(user, pw, item['mdn'])
        is_ok = (status == "Available" or plan == TARGET_PLAN)
        
        results.append([datetime.now(), item['mdn'], item['store'], status, plan, "OK" if is_ok else "FAIL"])
        if not is_ok:
            failed_sims.append(f"חנות: {item['store']}, סים: {item['mdn']}, תוכנית: {plan}")

    # כתיבה לקובץ CSV
    with open(report_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["תאריך", "MDN", "חנות", "סטטוס", "תוכנית", "תוצאה"])
        writer.writerows(results)

    # כאן ניתן להוסיף לוגיקה לשליחת מייל (דרך SMTP) אם יש כישלונות

if __name__ == "__main__":
    main()
