import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import translationsEn from "./locales/en/translations";
import translationsDe from "./locales/de/translations";
import LanguageDetector from "i18next-browser-languagedetector";

export const defaultNS = "translations";

export const resources = {
  en: { translations: translationsEn },
  de: { translations: translationsDe },
} as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    lng: "en-US",
    fallbackLng: "en",
    debug: true,
    defaultNS: defaultNS,
    resources: resources,
    interpolation: { escapeValue: false },
  });

export default i18n;
