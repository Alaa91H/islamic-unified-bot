import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const TODAY = {
  configured: true,
  profile: { username: "tester" },
  local_now: "2026-08-22T12:00:00+03:00",
  city: {
    name: "مكة المكرمة",
    country: "السعودية",
    method: "makkah",
    method_name: "أم القرى",
    asr_method: "standard",
    timezone: "Asia/Riyadh",
  },
  preferences: { language: "ar" as const, notifications_on: true },
  prayers: [
    { key: "fajr", name: "الفجر", time: "04:46" },
    { key: "dhuhr", name: "الظهر", time: "12:22" },
  ],
  next_prayer: {
    key: "dhuhr",
    name: "الظهر",
    time: "12:22",
    minutes_until: 22,
    is_tomorrow: false,
  },
};

const CITIES = {
  cities: [
    { name: "مكة المكرمة", country: "السعودية", method: "makkah", method_name: "أم القرى" },
    { name: "الرياض", country: "السعودية", method: "mwl", method_name: "رابطة العالم الإسلامي" },
  ],
};

function response(body: unknown, ok = true) {
  return { ok, json: async () => body } as Response;
}

function installTelegram(initData = "signed-init-data") {
  Object.assign(window, {
    Telegram: {
      WebApp: {
        ready: vi.fn(),
        expand: vi.fn(),
        initData,
        MainButton: {
          setText: vi.fn(),
          show: vi.fn(),
          onClick: vi.fn(),
          offClick: vi.fn(),
        },
      },
    },
  });
}

async function renderHome() {
  const { default: Home } = await import("./Home");
  return render(<Home />);
}

describe("Home Mini App API contract", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv("VITE_MINIAPP_API_URL", "https://miniapp.example");
    installTelegram();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.resetModules();
    delete window.Telegram;
  });

  it("loads today and cities through authenticated API requests", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(TODAY)).mockResolvedValueOnce(response(CITIES));
    vi.stubGlobal("fetch", fetchMock);

    await renderHome();

    expect(await screen.findByRole("heading", { name: "مرحبًا، @tester" })).toBeTruthy();
    expect(screen.getAllByText("الظهر")).toHaveLength(2);
    expect(screen.getByRole("option", { name: /الرياض/ })).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "https://miniapp.example/api/miniapp/today",
      expect.objectContaining({ headers: { "X-Telegram-Init-Data": "signed-init-data" } }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "https://miniapp.example/api/miniapp/cities",
      expect.objectContaining({ headers: { "X-Telegram-Init-Data": "signed-init-data" } }),
    );
  });

  it("saves the chosen city and refreshes data after a successful authenticated update", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(TODAY))
      .mockResolvedValueOnce(response(CITIES))
      .mockResolvedValueOnce(response({}))
      .mockResolvedValueOnce(response({ ...TODAY, city: { ...TODAY.city, name: "الرياض" } }))
      .mockResolvedValueOnce(response(CITIES));
    vi.stubGlobal("fetch", fetchMock);

    await renderHome();
    await screen.findByRole("option", { name: /الرياض/ });
    await user.selectOptions(screen.getByLabelText("المدينة وطريقة الحساب"), "الرياض");
    await user.click(screen.getByRole("button", { name: "حفظ الإعدادات في البوت" }));

    expect(await screen.findByText("حُفظت الإعدادات")).toBeTruthy();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "https://miniapp.example/api/miniapp/preferences",
        expect.objectContaining({
          method: "PUT",
          headers: expect.objectContaining({ "X-Telegram-Init-Data": "signed-init-data" }),
          body: JSON.stringify({ language: "ar", notifications_on: true, city: "الرياض" }),
        }),
      );
    });
  });

  it("surfaces a localized error when the today or cities contract fails", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response({}, false)).mockResolvedValueOnce(response({}, false));
    vi.stubGlobal("fetch", fetchMock);

    await renderHome();

    expect(await screen.findByText("تعذر تحميل بيانات اليوم. تحقق من الاتصال ثم أعد الفتح.")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
