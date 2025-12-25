import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import firebase_admin
from firebase_admin import credentials, db

# ==================================================
# 1️⃣ إعدادات الاتصال (أسرار GitHub)
# ==================================================
# قراءة مفتاح فاير بيس
firebase_config_str = os.environ.get('FIREBASE_KEY')
if firebase_config_str:
    cred_dict = json.loads(firebase_config_str)
    cred = credentials.Certificate(cred_dict)
    # ⚠️⚠️ تأكد أن رابط الداتابيز هنا صحيح وينتهي بـ firebaseio.com
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://YOUR-DB-URL.firebaseio.com/'})
else:
    print("❌ خطأ: لم يتم العثور على مفاتيح فاير بيس!")

# قراءة بيانات دخول طرود
SITE_EMAIL = os.environ.get('TOROD_EMAIL')
SITE_PASS = os.environ.get('TOROD_PASSWORD')

# ==================================================
# 2️⃣ دالة تعبئة العنوان (المحرك الرئيسي)
# ==================================================
def add_address_to_torod(order_id, data):
    print(f"🚀 بدء معالجة الطلب: {order_id}")
    
    # إعدادات المتصفح
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # ⚠️ شغل هذا السطر لاحقاً في GitHub Actions
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--lang=ar")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        # --- (أ) تسجيل الدخول ---
        print("🔐 جاري تسجيل الدخول...")
        driver.get("https://torod.co/ar/login")
        
        wait.until(EC.visibility_of_element_located((By.NAME, "email"))).send_keys(SITE_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(SITE_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(5) # انتظار تحميل الداشبورد

        # --- (ب) الانتقال لصفحة العناوين ---
        print("📍 الانتقال لصفحة العناوين...")
        driver.get("https://torod.co/ar/settings/addresses")
        time.sleep(3)

        # ضغط زر "عنوان جديد"
        print("➕ ضغط زر إضافة عنوان جديد...")
        add_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="ga4-addressesDiv"]/div/div/div[2]/a')))
        add_btn.click()
        time.sleep(3)

        # --- (ج) 🛑 إيقاف الخريطة (Toggle Map) ---
        print("🗺️ إيقاف الخريطة (تفعيل الإدخال اليدوي)...")
        try:
            map_toggle = wait.until(EC.element_to_be_clickable((By.ID, "merchant_address_form_google_map_toggle")))
            map_toggle.click()
            time.sleep(2)
        except:
            print("⚠️ تنبيه: لم أستطع ضغط زر قفل الخريطة (قد تكون مقفلة أصلاً).")

        # --- (د) تعبئة البيانات النصية ---
        print("✍️ تعبئة البيانات الأساسية...")
        driver.find_element(By.ID, "merchant_address_form_name").send_keys(data.get('store_name', 'اسم المتجر'))
        driver.find_element(By.ID, "merchant_address_form_contact_name").send_keys(data.get('receiver_name', 'عميل'))
        driver.find_element(By.ID, "merchant_address_form_title").send_keys(order_id) # رقم الفرع = رقم الطلب
        driver.find_element(By.ID, "merchant_address_form_phone_number").send_keys(data.get('receiver_phone', '0500000000'))
        driver.find_element(By.ID, "merchant_address_form_email").send_keys("customer@example.com")

        # --- (هـ) معالجة المدينة والمنطقة (الذكية 🧠) ---
        print("🏙️ اختيار المدينة والمنطقة...")
        # 1. فتح القائمة
        driver.find_element(By.ID, "select2-merchant_address_form_city-container").click()
        time.sleep(1)
        
        # 2. تجهيز الأسماء
        city_name = data.get('city', '').strip()
        region_name = data.get('region', '').strip()
        
        # 3. الكتابة في البحث
        search_box = driver.find_element(By.CLASS_NAME, "select2-search__field")
        search_box.send_keys(city_name)
        time.sleep(3) # انتظار النتائج

        # 4. البحث عن التطابق (المدينة + المنطقة)
        results = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
        found = False
        
        for result in results:
            text = result.text
            # هل النص يحتوي على اسم المدينة واسم المنطقة معاً؟
            if city_name in text and region_name in text:
                print(f"   ✅ تم اختيار: {text}")
                result.click()
                found = True
                break
        
        # خطة بديلة: إذا لم يجد المنطقة، يختار أي شيء فيه اسم المدينة
        if not found:
            print("   ⚠️ لم أجد تطابقاً للمنطقة، سأختار بناءً على المدينة فقط.")
            for result in results:
                if city_name in result.text:
                    result.click()
                    found = True
                    break
        
        # خطة الطوارئ: اضغط انتر
        if not found:
            search_box.send_keys(Keys.ENTER)

        # --- (و) معالجة الحي ---
        print("🏘️ اختيار الحي...")
        try:
            driver.find_element(By.ID, "select2-merchant_address_form_district-container").click()
            time.sleep(1)
            search_box_dist = driver.find_element(By.CLASS_NAME, "select2-search__field")
            search_box_dist.send_keys(data.get('district', ''))
            time.sleep(2)
            search_box_dist.send_keys(Keys.ENTER)
        except:
            print("⚠️ مشكلة بسيطة في اختيار الحي، سأتجاوزها.")

        # --- (ز) العنوان التفصيلي ---
        driver.find_element(By.ID, "merchant_address_form_address_details").send_keys(data.get('street', '-'))

        # --- (ح) الضغط على زر الحفظ النهائي ✅ ---
        print("💾 جاري الحفظ...")
        save_btn = wait.until(EC.element_to_be_clickable((By.ID, "address_form_btn")))
        save_btn.click()
        
        print("✅✅ تمت العملية بنجاح! تم حفظ العنوان.")
        time.sleep(5)
        return True

    except Exception as e:
        print(f"❌ حدث خطأ أثناء المعالجة: {e}")
        # حفظ صورة للمشكلة
        driver.save_screenshot(f"error_{order_id}.png")
        return False
        
    finally:
        driver.quit()

# ==================================================
# 3️⃣ حلقة البحث عن طلبات جديدة
# ==================================================
print("🔄 جاري فحص قاعدة البيانات...")
ref = db.reference('orders')
orders = ref.get()

if orders:
    for key, val in orders.items():
        # نفحص إذا الحالة "pending" (معلق)
        if val.get('status') == 'pending':
            success = add_address_to_torod(key, val)
            if success:
                # تحديث الحالة إلى "done" عشان ما يكررها المرة الجاية
                ref.child(key).update({'status': 'done'})
else:
    print("💤 لا توجد طلبات جديدة.")
