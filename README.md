# API-Based Dataset Generator Tool

Ushbu tool API orqali so‘rov yuborib, natija asosida avtomatik **dataset generate** qiladi.

Bunda foydalanuvchi API konfiguratsiyasini belgilaydi (endpoint, model name, auth token va h.k.), tool esa kerakli miqdorda ma’lumot yig‘ib, kerakli formatda saqlab beradi.

⚙️ Tipik jarayon:

1. API endpoint → so‘rov yuboriladi  
2. Javoblardan dataset elementlari shakllantiriladi  
3. Yakuniy dataset `.json` yoki `.csv` ko‘rinishida saqlanadi

> 🔧 Ushbu tool alohida branchda (`tool-api-dataset-generator`) joylashadi.



🚀 Branch bilan ishlash qo‘llanmasi (tool-generator-api)
🔹 1. Lokal kodingizni tool-generator-api branch sifatida push qilish
git push -u origin HEAD:tool-generator-api


Hozirgi branch (HEAD) remote’da tool-generator-api nomi bilan yaratiladi va upstream sifatida o‘rnatiladi.

🔹 2. Faqat tool-generator-api branchni klon qilish
git clone --branch tool-generator-api --single-branch https://github.com/SaidAbbos96/dataset-tools.git


Boshqa branchlar yuklanmaydi — faqat shu branch keladi.

🔹 3. Klon qilingan loyihada ushbu branch uchun so‘nggi yangilanishlarni yuklab olish
git checkout tool-generator-api
git pull origin tool-generator-api


Branchga o‘tasiz va remote’dagi oxirgi versiyani yuklab olasiz.


Script fileni bajarish uchun chmod +x push.sh
