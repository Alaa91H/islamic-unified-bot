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

type TodayPayload = {
  configured: boolean;
  profile: { username: string | null };
  local_now: string;
  city: { name: string; country: string; method: string; method_name: string; asr_method: string; timezone: string };
  preferences: { language: "ar" | "en"; notifications_on: boolean };
  prayers: { key: string; name: string; time: string }[];
  next_prayer: { key: string; name: string; time: string; minutes_until: number; is_tomorrow: boolean };
};

const PRAYER_ICONS: Record<string, string> = {
  fajr: "◔", sunrise: "◒", dhuhr: "●", asr: "◐", maghrib: "◓", isha: "☾",
};
const PRAYER_NAMES_EN: Record<string, string> = {
  fajr: "Fajr", sunrise: "Sunrise", dhuhr: "Dhuhr", asr: "Asr", maghrib: "Maghrib", isha: "Isha",
};

const API_BASE = import.meta.env.VITE_MINIAPP_API_URL?.replace(/\/$/, "");
const DEFAULT_CITY = "مكة المكرمة";

function formatLocalDate(value: string | undefined, language: "ar" | "en") {
  if (!value) return language === "ar" ? "جارٍ تحميل تاريخ اليوم…" : "Loading today…";
  return new Intl.DateTimeFormat(language === "ar" ? "ar-SA-u-ca-islamic" : "en-US-u-ca-islamic", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).format(new Date(value));
}

export default function Home() {
  const [notifications, setNotifications] = useState(true);
  const [language, setLanguage] = useState<"ar" | "en">("ar");
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [today, setToday] = useState<TodayPayload | null>(null);
  const [isLoadingToday, setIsLoadingToday] = useState(Boolean(API_BASE));
  const [todayError, setTodayError] = useState(false);
  const isArabic = language === "ar";
  const copy = useMemo(
    () =>
      isArabic
        ? {
            greeting: "مرحبًا",
            next: "الصلاة القادمة",
            unavailable: "تعذر تحميل بيانات اليوم",
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
            greeting: "Welcome",
            next: "NEXT PRAYER",
            unavailable: "Today’s data is unavailable",
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
    const city = today?.city.name ?? DEFAULT_CITY;
    const apiPayload = { language, notifications_on: notifications, city };
    const fallbackPayload = { language, notifications, city, source: "miniapp" };
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
  }, [language, notifications, today?.city.name]);

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
      setIsLoadingToday(false);
      return;
    }
    const controller = new AbortController();
    const loadToday = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/miniapp/today`, {
          headers: { "X-Telegram-Init-Data": initData },
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Could not load today data");
        const data: TodayPayload = await response.json();
        setToday(data);
        setLanguage(data.preferences.language);
        setNotifications(data.preferences.notifications_on);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) setTodayError(true);
      } finally {
        if (!controller.signal.aborted) setIsLoadingToday(false);
      }
    };
    void loadToday();
    return () => controller.abort();
  }, []);

  const cityLabel = today ? [today.city.name, today.city.country].filter(Boolean).join("، ") : "—";
  const profileName = today?.profile.username ? `@${today.profile.username}` : "";
  const nextPrayer = today?.next_prayer;
  const remainingLabel = nextPrayer
    ? isArabic
      ? `بقي ${nextPrayer.minutes_until} دقيقة${nextPrayer.is_tomorrow ? " حتى الغد" : ""}`
      : `${nextPrayer.minutes_until} minutes remaining${nextPrayer.is_tomorrow ? " until tomorrow" : ""}`
    : isLoadingToday ? copy.loading : copy.unavailable;

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
          <p className="eyebrow">{formatLocalDate(today?.local_now, language)}</p>
          <h1 id="greeting">{copy.greeting}{profileName ? `، ${profileName}` : ""}</h1>
        </div>
        <div className="status-chip"><Sparkles size={14} /> <span>{today ? (isArabic ? "متزامن" : "In sync") : (isArabic ? "قيد المزامنة" : "Syncing")}</span></div>
      </section>

      <section className="hero-card" aria-label={copy.next}>
        <img className="hero-art" src="/assets/mihrab-hero.webp" alt="" />
        <div className="hero-shade" />
        <div className="hero-content">
          <div className="hero-label"><MoonStar size={15} /> {copy.next}</div>
          <div className="prayer-name">{nextPrayer ? (isArabic ? nextPrayer.name : PRAYER_NAMES_EN[nextPrayer.key]) : "—"}</div>
          <div className="hero-time">{nextPrayer?.time ?? "--:--"}</div>
          <div className="remaining"><Clock3 size={15} /> {remainingLabel}</div>
        </div>
        <div className="hero-location"><MapPin size={14} /> {cityLabel}</div>
      </section>

      <section className="section-head">
        <h2>{copy.timings}</h2>
        <span className="quiet-link">{today?.city.timezone ?? ""} <ChevronLeft size={16} /></span>
      </section>

      <section className="prayer-rail" aria-label={copy.timings}>
        {(today?.prayers ?? []).map((prayer) => {
          const active = prayer.key === nextPrayer?.key;
          return (
            <article className={`prayer-item ${active ? "active" : ""}`} key={prayer.name}>
              <span className="prayer-icon">{PRAYER_ICONS[prayer.key]}</span>
              <strong>{isArabic ? prayer.name : PRAYER_NAMES_EN[prayer.key]}</strong>
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
        <div className="setting-row">
          <span className="setting-icon"><MapPin size={19} /></span>
          <span className="setting-copy"><strong>{copy.city}</strong><small>{cityLabel} · {today?.city.method_name ?? "—"}</small></span>
        </div>
      </section>

      <button className="save-button" type="button" onClick={handleSave} disabled={isSaving} aria-busy={isSaving}>
        {saved ? <Check size={19} /> : <span className="save-arch" />}
        {saved ? copy.saved : isSaving ? copy.saving : copy.save}
      </button>
      <p className="footnote">{saveError ? (isArabic ? "تعذر حفظ الإعدادات. حاول مرة أخرى." : "Could not save settings. Try again.") : todayError ? (isArabic ? "تعذر تحميل بيانات اليوم. تحقق من الاتصال ثم أعد الفتح." : "Could not load today’s data. Check your connection and reopen the app.") : isLoadingToday ? copy.loading : copy.settingsNote}</p>
    </main>
  );
}
