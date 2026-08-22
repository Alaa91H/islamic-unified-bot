/**
 * تصميم «محراب اليوم»: طبقات هادئة، قوس للمعلومة الأهم، ونحاس المحراب للإجراء.
 * الواجهة RTL أولًا؛ تحفظ عبر API موثقة عند تهيئتها وتبقى متوافقة مع sendData.
 */
import {
  BellRing,
  Check,
  ChevronLeft,
  Clock3,
  Globe2,
  MapPin,
  MoonStar,
  Settings2,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

type TelegramWebApp = {
  ready: () => void;
  expand: () => void;
  MainButton?: {
    setText: (text: string) => void;
    show: () => void;
    onClick: (listener: () => void) => void;
    offClick?: (listener: () => void) => void;
  };
  sendData?: (payload: string) => void;
  initData?: string;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

const prayers = [
  { name: "الفجر", time: "04:38", icon: "◔" },
  { name: "الشروق", time: "06:01", icon: "◒" },
  { name: "الظهر", time: "12:19", icon: "●" },
  { name: "العصر", time: "15:42", icon: "◐" },
  { name: "المغرب", time: "18:37", icon: "◓" },
  { name: "العشاء", time: "20:00", icon: "☾" },
];

const API_BASE = import.meta.env.VITE_MINIAPP_API_URL?.replace(/\/$/, "");
const DEFAULT_CITY = "الرياض";

export default function Home() {
  const [notifications, setNotifications] = useState(true);
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingPreferences, setIsLoadingPreferences] = useState(Boolean(API_BASE));
  const isArabic = language === "ar";
  const copy = useMemo(
    () =>
      isArabic
        ? {
            greeting: "مرحبًا، عبد الله",
            date: "الخميس، 14 صفر 1448 هـ",
            next: "الصلاة القادمة",
            remaining: "بقي 37 دقيقة",
            asr: "العصر",
            location: "الرياض، المملكة العربية السعودية",
            timings: "أوقات اليوم",
            settings: "إعداداتك",
            alert: "تنبيهات الأذان",
            alertHint: "إشعار قبل الأذان بخمس دقائق",
            city: "المدينة وطريقة الحساب",
            save: "حفظ الإعدادات في البوت",
            saved: "حُفظت الإعدادات",
            saving: "جارٍ الحفظ…",
            loading: "جارٍ مزامنة إعداداتك…",
            settingsNote: "يمكنك تعديل التفاصيل الكاملة من محادثة البوت.",
          }
        : {
            greeting: "Welcome, Abdullah",
            date: "Thursday, 14 Safar 1448 AH",
            next: "NEXT PRAYER",
            remaining: "37 minutes remaining",
            asr: "Asr",
            location: "Riyadh, Saudi Arabia",
            timings: "TODAY'S TIMES",
            settings: "YOUR SETTINGS",
            alert: "Adhan alerts",
            alertHint: "Notify me five minutes before adhan",
            city: "City & calculation method",
            save: "Save settings in the bot",
            saved: "Settings saved",
            saving: "Saving…",
            loading: "Syncing your settings…",
            settingsNote: "Edit detailed preferences in the bot chat.",
          },
    [isArabic],
  );

  const handleSave = useCallback(async () => {
    const apiPayload = { language, notifications_on: notifications, city: DEFAULT_CITY };
    const fallbackPayload = { language, notifications, city: DEFAULT_CITY, source: "miniapp" };
    const telegram = window.Telegram?.WebApp;
    setSaveError(false);
    setIsSaving(true);
    try {
      if (API_BASE) {
        if (!telegram?.initData) throw new Error("Telegram initData is required for the API");
        const response = await fetch(`${API_BASE}/api/miniapp/preferences`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-Telegram-Init-Data": telegram.initData,
          },
          body: JSON.stringify(apiPayload),
        });
        if (!response.ok) throw new Error("Could not save preferences");
      } else if (telegram?.sendData) {
        telegram.sendData(JSON.stringify(fallbackPayload));
      } else {
        throw new Error("Telegram WebApp is unavailable");
      }
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2800);
    } catch {
      setSaveError(true);
    } finally {
      setIsSaving(false);
    }
  }, [language, notifications]);

  useEffect(() => {
    const app = window.Telegram?.WebApp;
    if (!app) return;
    const onMainButtonClick = () => void handleSave();
    app.ready();
    app.expand();
    app.MainButton?.setText(copy.save);
    app.MainButton?.show();
    app.MainButton?.onClick(onMainButtonClick);
    return () => app.MainButton?.offClick?.(onMainButtonClick);
  }, [copy.save, handleSave]);

  useEffect(() => {
    const telegram = window.Telegram?.WebApp;
    const initData = telegram?.initData;
    if (!API_BASE || !initData) {
      setIsLoadingPreferences(false);
      return;
    }
    const controller = new AbortController();
    const loadPreferences = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/miniapp/preferences`, {
          headers: { "X-Telegram-Init-Data": initData },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Could not load preferences");
        const data: { configured: boolean; language?: "ar" | "en"; notifications_on?: boolean } = await response.json();
        if (data.configured) {
          if (data.language) setLanguage(data.language);
          if (typeof data.notifications_on === "boolean") setNotifications(data.notifications_on);
        }
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) setSaveError(true);
      } finally {
        if (!controller.signal.aborted) setIsLoadingPreferences(false);
      }
    };
    void loadPreferences();
    return () => controller.abort();
  }, []);

  return (
    <main className="mihrab-app" dir={isArabic ? "rtl" : "ltr"}>
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <header className="topbar" aria-label="التنقل الرئيسي">
        <div className="brand-lockup">
          <img className="brand-mark" src="/assets/mihrab-mark.webp" alt="" />
          <span>محراب اليوم</span>
        </div>
        <button
          className="icon-button"
          onClick={() => setLanguage(isArabic ? "en" : "ar")}
          aria-label="تبديل اللغة"
        >
          <Globe2 size={18} />
          <span>{isArabic ? "EN" : "ع"}</span>
        </button>
      </header>

      <section className="welcome-row" aria-labelledby="greeting">
        <div>
          <p className="eyebrow">{copy.date}</p>
          <h1 id="greeting">{copy.greeting}</h1>
        </div>
        <div className="status-chip"><Sparkles size={14} /> <span>{isArabic ? "منظّم" : "In sync"}</span></div>
      </section>

      <section className="hero-card" aria-label={copy.next}>
        <img className="hero-art" src="/assets/mihrab-hero.webp" alt="" />
        <div className="hero-shade" />
        <div className="hero-content">
          <div className="hero-label"><MoonStar size={15} /> {copy.next}</div>
          <div className="prayer-name">{copy.asr}</div>
          <div className="hero-time">15:42</div>
          <div className="remaining"><Clock3 size={15} /> {copy.remaining}</div>
        </div>
        <div className="hero-location"><MapPin size={14} /> {copy.location}</div>
      </section>

      <section className="section-head">
        <h2>{copy.timings}</h2>
        <button className="quiet-link" type="button">{isArabic ? "التقويم" : "Calendar"} <ChevronLeft size={16} /></button>
      </section>

      <section className="prayer-rail" aria-label={copy.timings}>
        {prayers.map((prayer) => {
          const active = prayer.name === "العصر";
          return (
            <article className={`prayer-item ${active ? "active" : ""}`} key={prayer.name}>
              <span className="prayer-icon">{prayer.icon}</span>
              <strong>{isArabic ? prayer.name : prayer.name === "العصر" ? "Asr" : prayer.name}</strong>
              <time>{prayer.time}</time>
              {active && <span className="now-dot" aria-label="الوقت الحالي" />}
            </article>
          );
        })}
      </section>

      <section className="section-head settings-head">
        <h2>{copy.settings}</h2>
        <Settings2 size={19} aria-hidden="true" />
      </section>

      <section className="setting-stack" aria-label={copy.settings}>
        <button className="setting-row" type="button" onClick={() => setNotifications(!notifications)}>
          <span className="setting-icon"><BellRing size={19} /></span>
          <span className="setting-copy"><strong>{copy.alert}</strong><small>{copy.alertHint}</small></span>
          <span className={`toggle ${notifications ? "on" : ""}`} aria-checked={notifications} role="switch"><span /></span>
        </button>
        <button className="setting-row" type="button">
          <span className="setting-icon"><MapPin size={19} /></span>
          <span className="setting-copy"><strong>{copy.city}</strong><small>{copy.location} · أم القرى</small></span>
          <ChevronLeft className="row-chevron" size={19} />
        </button>
      </section>

      <button className="save-button" type="button" onClick={handleSave} disabled={isSaving} aria-busy={isSaving}>
        {saved ? <Check size={19} /> : <span className="save-arch" />}
        {saved ? copy.saved : isSaving ? copy.saving : copy.save}
      </button>
      <p className="footnote">{saveError ? (isArabic ? "تعذر الحفظ أو مزامنة الإعدادات. حاول مرة أخرى." : "Could not save or sync settings. Try again.") : isLoadingPreferences ? copy.loading : copy.settingsNote}</p>
    </main>
  );
}
