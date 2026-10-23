import api from "./api";

// Chaque achat (« intention » : tel abonnement, telle réservation...) garde la
// même clé `Idempotency-Key` tant qu'il n'a pas abouti. Un double clic, un
// nouvel essai après une coupure réseau, une fenêtre fermée puis rouverte ou
// un rechargement de page renvoient donc la même clé : le serveur rejoue le
// premier résultat au lieu d'encaisser une seconde fois.
const STORAGE_KEY = "innovevent.payment-keys";
const inFlight = new Map();

function readKeys() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeKeys(keys) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
  } catch {
    // Stockage indisponible (navigation privée) : la clé reste en mémoire.
  }
}

const memoryKeys = readKeys();

function newKey() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}-${Math.random().toString(36).slice(2, 12)}`;
}

function keyFor(intent) {
  if (!memoryKeys[intent]) {
    memoryKeys[intent] = newKey();
    writeKeys(memoryKeys);
  }
  return memoryKeys[intent];
}

function releaseKey(intent) {
  delete memoryKeys[intent];
  writeKeys(memoryKeys);
}

export const NETWORK_PAYMENT_MESSAGE =
  "La connexion a été interrompue pendant le paiement. Réessayez : vous ne serez pas débité deux fois.";

/**
 * Envoie une demande de paiement protégée contre les doublons.
 * `intent` identifie l'achat (ex. `booking:12`). Tant qu'une demande pour cet
 * achat est en cours, un nouvel appel renvoie la même promesse.
 */
export function postPayment(intent, url, payload) {
  if (inFlight.has(intent)) return inFlight.get(intent);
  const request = api
    .post(url, payload, { headers: { "Idempotency-Key": keyFor(intent) } })
    .then((response) => {
      releaseKey(intent);
      return response;
    })
    .catch((error) => {
      const statusCode = error?.response?.status;
      // Réponse définitive du serveur (refus, paiement échoué) : la prochaine
      // tentative est un nouvel achat. Coupure réseau ou paiement « en cours »
      // (409) : on garde la clé pour que le nouvel essai soit reconnu.
      if (statusCode && statusCode !== 409) releaseKey(intent);
      if (!error?.response) error.paymentMessage = NETWORK_PAYMENT_MESSAGE;
      throw error;
    })
    .finally(() => inFlight.delete(intent));
  inFlight.set(intent, request);
  return request;
}

/** Message à afficher pour une erreur de paiement. */
export function paymentErrorMessage(error, fallback = "Le paiement a échoué. Réessayez ou choisissez un autre moyen de paiement.") {
  return error?.paymentMessage || error?.response?.data?.detail || error?.response?.data?.non_field_errors?.[0] || fallback;
}
