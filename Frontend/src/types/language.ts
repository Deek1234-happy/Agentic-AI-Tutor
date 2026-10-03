export const SUPPORTED_LANGUAGES = [
  { code: "en", name: "English", locale: "en-IN" },
  { code: "kn", name: "Kannada", locale: "kn-IN" },
  { code: "hi", name: "Hindi", locale: "hi-IN" },
  { code: "ml", name: "Malayalam", locale: "ml-IN" },
  { code: "ta", name: "Tamil", locale: "ta-IN" },
  { code: "te", name: "Telugu", locale: "te-IN" },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

export function getLanguageLocale(language: LanguageCode): string {
  return SUPPORTED_LANGUAGES.find((item) => item.code === language)?.locale ?? "en-IN";
}

export function getLanguageName(language: LanguageCode): string {
  return SUPPORTED_LANGUAGES.find((item) => item.code === language)?.name ?? "English";
}