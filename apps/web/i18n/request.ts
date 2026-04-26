import { getRequestConfig } from "next-intl/server";
import { cookies, headers } from "next/headers";

const locales = ["en", "zh-CN"] as const;
type AppLocale = (typeof locales)[number];
const defaultLocale: AppLocale = "en";

function isAppLocale(value: string | undefined | null): value is AppLocale {
  return Boolean(value && locales.includes(value as AppLocale));
}

function localeFromHeader(value: string | null): AppLocale {
  if (!value) {
    return defaultLocale;
  }

  const normalized = value.toLowerCase();
  if (normalized.includes("zh-cn") || normalized.includes("zh")) {
    return "zh-CN";
  }
  return "en";
}

export default getRequestConfig(async ({ locale, requestLocale }) => {
  const segmentLocale = locale ?? (await requestLocale);
  if (isAppLocale(segmentLocale)) {
    return {
      locale: segmentLocale,
      messages: (await import(`../messages/${segmentLocale}.json`)).default,
    };
  }

  const cookieStore = await cookies();
  const headerStore = await headers();
  const cookieLocale = cookieStore.get("ai-desk.locale")?.value;
  const resolvedLocale = isAppLocale(cookieLocale)
    ? cookieLocale
    : localeFromHeader(headerStore.get("accept-language"));

  return {
    locale: resolvedLocale,
    messages: (await import(`../messages/${resolvedLocale}.json`)).default,
  };
});
