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
MINIAPP_API_CONCURRENCY_LIMIT=50
```

عند تفعيل API يرفض التطبيق ربطها بعنوان شبكة عام، أو تشغيلها بلا `MINIAPP_ALLOWED_ORIGIN` من HTTPS، أو استخدام مسار بدل origin. أبقِ `MINIAPP_API_HOST=127.0.0.1` وشغّل reverse proxy HTTPS أمامه. في الواجهة انسخ `miniapp/client/.env.example` إلى `.env.production` واضبط `VITE_MINIAPP_API_URL=https://api.example.com` وقت البناء. لا تضع رمز البوت أو `initData` في ملفات الواجهة أو السجلات.

## reverse proxy مقترح

يبقى المنفذ `8080` محليًا فقط. يمرر Nginx طلبات API من نطاق HTTPS مخصص، ويقصر فحص الجاهزية على المضيف نفسه:

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    location /api/miniapp/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location = /healthz { proxy_pass http://127.0.0.1:8080; }
    location = /readyz {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8080;
    }
}
```

لا تستخدم نقطة API نفسها لتقديم ملفات Mini App static إذا لم تكن بحاجة إلى ذلك؛ افصل نطاق الواجهة عن نطاق API ثم ضع نطاق الواجهة، لا نطاق API، في `MINIAPP_ALLOWED_ORIGIN`.

## الضمانات

كل طلب لإعدادات المستخدم يتطلب الترويسة `X-Telegram-Init-Data`. يتحقق الخادم من توقيع HMAC ومدة الصلاحية قبل استخدام معرف Telegram. تُرفض بيانات المتصفح غير الموقعة، وتبقى CORS مقيدة بالنطاق المحدد. ترسل الاستجابات رؤوس منع التخزين و`nosniff` و`DENY` للإطارات، ولا تقبل إلا `GET` و`PUT` من الواجهة.

> لا يكفي `initDataUnsafe` لاتخاذ قرار صلاحيات، ولا يُستخدم في هذه الخدمة.

## فحص سريع

يتاح المسار `GET /healthz` للتحقق من حيوية العملية فقط. يتحقق `GET /readyz` أيضًا من قاعدة البيانات وعدادات outbox، ولذلك يجب أن يبقى داخليًا. لا يحتوي أي منهما على بيانات مستخدمين أو إعدادات حساسة.

## تحقق إطلاق مختصر

بعد إعادة تشغيل الخدمة، نفّذ على الخادم نفسه:

```bash
curl --fail http://127.0.0.1:8080/healthz
curl --fail http://127.0.0.1:8080/readyz
```

ثم اختبر من Telegram حقيقي: افتح Mini App، بدّل التنبيه، احفظ، أعد فتحها، وتحقق من ظهور الإعداد المحفوظ. لا تُعد هذه الخطوة مكتملة بمجرد نجاح CI، إذ تحتاج نطاق HTTPS مضبوطًا في BotFather وبيئة تشغيل حقيقية.
