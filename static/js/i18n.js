// static/js/i18n.js
// Minimal i18n utility for Odysseus Chat
// Exports: t(key) — look up a translation key, falling back to the key itself
//          initI18n(locale) — load the locale JSON, returns a Promise

let _translations = {};

/**
 * Look up a translation key.
 * Returns the translated string, or the key itself if not found.
 */
export function t(key, fallback) {
  if (_translations[key] !== undefined) return _translations[key];
  return fallback !== undefined ? fallback : key;
}

/**
 * Load translations for the given locale.
 * @param {string} locale — e.g. 'ru'
 * @returns {Promise<void>}
 */
export function initI18n(locale) {
  return fetch(`/static/locales/${locale}.json`)
    .then(r => {
      if (!r.ok) throw new Error(`Failed to load locale ${locale}: ${r.status}`);
      return r.json();
    })
    .then(data => {
      _translations = data || {};
    })
    .catch(err => {
      console.warn('[i18n] Could not load locale', locale, err);
      _translations = {};
    });
}
