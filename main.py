import json
import os
import pandas as pd
from datetime import datetime
from logic import call_sim_api

def run_automated_check():
    if not os.path.exists("database.json"):
        print("No database found.")
        return

    with open("database.json", "r") as f:
        data = json.load(f)

    results = []
    failed = []
    
    for sim in data['sims']:
        status, plan, ok = call_sim_api(sim['iccid'], data['auth']['user'], data['auth']['pass'])
        res = {
            "תאריך": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ICCID": sim['iccid'],
            "חנות": sim['shop'],
            "סטטוס": status,
            "תוכנית": plan
        }
        results.append(res)
        if not ok:
            failed.append(res)

    # שמירת דוח CSV
    df = pd.DataFrame(results)
    filename = f"report_{datetime.now().strftime('%Y-%m-%d')}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    
    # כאן אפשר להוסיף לוגיקת שליחת מייל (דורש SMTP)
    if failed:
        print(f"ALERT: {len(failed)} SIMs failed the check!")

if __name__ == "__main__":
    run_automated_check()
