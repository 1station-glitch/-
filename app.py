from flask import Flask, render_template, request, jsonify
import requests
import json
import os

app = Flask(__name__, static_folder='.', static_url_path='')

# ==========================================
# 🔑 إعدادات طرود (Torod API)
# ==========================================
# رابط إنشاء عنوان (مستودع) في بيئة التجربة
TOROD_API_URL = "https://demo.stage.torod.co/ar/api/create/address"

# ⚠️ هام جداً: ضع التوكن الخاص بك هنا
TOROD_TOKEN = "CfbR6T8gU6usVFtiCvo4iwK09p0GZkDSWy7Vn8luEpa72j5Ywj3hz5a8re0mMy4Kcxg5EkcBjvaA3O26thqRgM5PNQOh0sP3GINDAmQJkU3s21mJ7C7xHbZ7l496r38WM2e173LY3v6dq02qz4S4HXyTVIPE5plJoQ98x49LtR6Kib59fD2XO1wdGBF5H9A1U1I19F01" 

# دالة مساعدة لجلب المدن
def get_cities():
    cities_list = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'cities.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        cities_list = [item.get('name_ar') or item.get('name') for item in data if item.get('name_ar') or item.get('name')]
                    else:
                        cities_list = data
        except: pass
    return cities_list

@app.route('/')
def home():
    return render_template('index.html', cities_data=get_cities())

@app.route('/store')
def store_page():
    return render_template('store.html', cities_data=get_cities())

# ==========================================
# 🚀 المسار الجديد: استقبال بيانات المتجر وإرسالها لطرود
# ==========================================
@app.route('/create-torod-address', methods=['POST'])
def create_torod_address():
    try:
        # 1. استلام البيانات من صفحة المتجر
        data = request.json
        print(f"📥 جاري إرسال بيانات المتجر: {data.get('store_name')} إلى طرود...")

        # 2. تجهيز البيانات حسب متطلبات طرود
        # ندمج المدينة والحي في حقل العنوان
        full_address = f"{data['city']} - {data['district']}"

        torod_payload = {
            "warehouse_name": data['store_name'],     # اسم المتجر كمستودع
            "contact_name": data['sender_name'],      # اسم الشخص المسؤول
            "phone_number": data['phone'],            # رقم الجوال
            "email": data['email'],                   # البريد الالكتروني
            "type": "address",                        # نوع العنوان
            "locate_address": full_address,           # العنوان مجمع
            "address": full_address,                  # تكرار العنوان للتأكيد
            # يمكنك استخدام رمز المتجر كمرجع
            "warehouse": f"{data['store_code']}" 
        }

        # 3. إرسال الطلب إلى طرود
        headers = {
            "Authorization": f"Bearer {TOROD_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        response = requests.post(TOROD_API_URL, json=torod_payload, headers=headers)
        
        # 4. الرد على الموقع
        if response.status_code in [200, 201]:
            print("✅ تم الإنشاء بنجاح في طرود!")
            return jsonify({"status": "success", "message": "تم إنشاء عنوان المتجر في طرود بنجاح!", "data": response.json()})
        else:
            print(f"❌ خطأ من طرود: {response.text}")
            return jsonify({"status": "error", "message": "رفضت طرود الطلب", "details": response.text}), 400

    except Exception as e:
        print(f"❌ خطأ فني: {e}")
        return jsonify({"status": "error", "message": f"حدث خطأ فني: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)