import os
import json
import firebase_admin
from firebase_admin import credentials, db
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time

# --- إعداد الاتصال بفاير بيس ---
# هنا يقرأ المفتاح من الخزنة السرية اللي سويتها
key_content = os.environ.get('FIREBASE_CREDENTIALS')
cred_dict = json.loads(key_content)
cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred, {
    # 🔴🔴 استبدل الرابط أدناه برابط قاعدة بياناتك اللي نسخته 🔴🔴
    'databaseURL': 'https://my-dashboard-d7e5f-default-rtdb.firebaseio.com/'
})

# --- دالة تعبئة البيانات ---
def fill_form(order_id, data):
    print(f"Start processing order: {order_id}")
    
    # إعدادات المتصفح المخفي
    chrome_options = Options()
    chrome_options.add_argument("--headless") # تشغيل بدون شاشة
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # تشغيل المتصفح
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        # 1. الذهاب للموقع
        driver.get("https://google.com") # 🔴 استبدله برابط الموقع اللي تبي تعبي فيه
        
        # مثال: طباعة العنوان للتأكد من الوصول
        print("Page Title is:", driver.title)
        
        # 2. هنا تكتب كود التعبئة (ابحث عن الحقول وعبيها)
        # مثال توضيحي فقط:
        # driver.find_element(By.ID, "username").send_keys(data.get('name'))
        # driver.find_element(By.ID, "submit_btn").click()
        
        # ننتظر قليلاً للتأكد
        time.sleep(2)
        
        return True # إذا تمت العملية بنجاح

    except Exception as e:
        print(f"Error: {e}")
        return False
        
    finally:
        driver.quit()

# --- البحث عن طلبات جديدة ---
ref = db.reference('orders') # تأكد ان بياناتك في فاير بيس تحت مسمى orders
orders = ref.get()

if orders:
    for key, val in orders.items():
        # نفترض أن حالة الطلب الجديد هي 'pending'
        if val.get('status') == 'pending':
            success = fill_form(key, val)
            
            if success:
                print("Done!")
                # تحديث الحالة إلى done عشان ما يكرره المرة الجاية
                ref.child(key).update({'status': 'done'})
else:
    print("No new orders.")
