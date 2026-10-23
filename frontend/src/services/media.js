// URLs des versions allégées (WebP redimensionné) servies par le backend via
// `?w=` — voir backend/apps/documents/image_variants.py.

export const VARIANT_WIDTHS = [160, 320, 480, 640, 960, 1280, 1920];
export const PLACEHOLDER_WIDTH = 32;
const VARIANT_PATHS = /^\/media\/(venues|equipment|providers|trainings|avatars|talents\/photos|talents\/portfolio|marketplace|landing|events)\//;

/** URL analysée si l'image a des versions allégées, sinon null. */
export function mediaUrl(src) {
  if (!src || typeof src !== "string" || /^(data|blob):/.test(src)) return null;
  let url;
  try {
    url = new URL(src, window.location.origin);
  } catch {
    return null;
  }
  if (!VARIANT_PATHS.test(url.pathname) || /\.svg$/i.test(url.pathname)) return null;
  return url;
}

export function withWidth(url, width) {
  const copy = new URL(url.href);
  copy.searchParams.set("w", String(width));
  return copy.href;
}

/** Plus petite version couvrant `cssWidth` px sur cet écran (densité ≤ 2). */
export function bestWidth(cssWidth) {
  const needed = (cssWidth || 480) * Math.min(window.devicePixelRatio || 1, 2);
  return VARIANT_WIDTHS.find((w) => w >= needed) || VARIANT_WIDTHS[VARIANT_WIDTHS.length - 1];
}

/** Version adaptée d'une image affichée sur `cssWidth` px (fond, carrousel…). */
export function imageVariant(src, cssWidth = window.innerWidth) {
  const url = mediaUrl(src);
  return url ? withWidth(url, bestWidth(cssWidth)) : src;
}

/** Télécharge et décode une image hors de la page ; résout avec son URL. */
export function preloadImage(src) {
  const loader = new Image();
  loader.decoding = "async";
  loader.src = src;
  return (loader.decode
    ? loader.decode()
    : new Promise((resolve, reject) => {
        loader.onload = resolve;
        loader.onerror = reject;
      })
  ).then(() => src);
}
