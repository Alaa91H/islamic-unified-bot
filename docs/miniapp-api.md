# تشغيل API لواجهة Telegram Mini App

تعمل الواجهة افتراضيًا بتدفق Telegram `sendData` المتوافق مع البوت. فعّل الخدمة الاختيارية فقط عندما تحتاج إلى حفظ الإعدادات دون إغلاق Mini App أو تحتاج إلى قراءة حالة حية.

## الإعداد

اضبط القيم التالية في ملف البيئة، ثم أعد تشغيل خدمة البوت:

```dotenv
MINIAPP_API_ENABLED=true
MINIAPP_API_HOST=127.0.0.1
MINIAPP_API_PORT=8080
MINIAPP_INIT_DATA_MAX_AGE=3600
MINIAPP_ALLOWED_ORIGIN=https://miniapp.example.com
```

شغّل reverse proxy HTTPS أمام المنفذ المحلي، واجعل `MINIAPP_ALLOWED_ORIGIN` مطابقًا تمامًا لنطاق واجهة Mini App. في الواجهة عيّن `VITE_MINIAPP_API_URL=https://api.example.com` وقت البناء. لا تضع رمز البوت أو `initData` في ملفات الواجهة أو السجلات.

## الضمانات

كل طلب لإعدادات المستخدم يتطلب الترويسة `X-Telegram-Init-Data`. يتحقق الخادم من توقيع HMAC ومدة الصلاحية قبل استخدام معرف Telegram. تُرفض بيانات المتصفح غير الموقعة، وتبقى CORS مقيدة بالنطاق المحدد عندما تضبطه.

> لا يكفي `initDataUnsafe` لاتخاذ قرار صلاحيات، ولا يُستخدم في هذه الخدمة.

## فحص سريع

يتاح المسار `GET /healthz` للتحقق التشغيلي فقط. لا يحتوي على بيانات مستخدمين أو إعدادات حساسة.

