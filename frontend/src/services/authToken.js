// Le jeton d'accès vit uniquement en mémoire. Le jeton de renouvellement est
// conservé dans un cookie HttpOnly géré par le backend.
let accessToken = null;

export function getAccessToken() {
  return accessToken;
}

export function setAccessToken(token) {
  accessToken = token || null;
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("ie-access-token-changed", { detail: accessToken }));
  }
}
