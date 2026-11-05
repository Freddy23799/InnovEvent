// Rayons de la boutique (Marketplace vente) et leurs sous-catégories. Les
// valeurs des rayons correspondent à `SaleCategory` côté backend ; les
// sous-catégories sont stockées telles quelles dans `subcategory`.
export const SALE_CATEGORIES = [
  {
    value: "furniture", label: "Mobilier", icon: "fa-solid fa-chair", tagline: "Chaises, tables et salons",
    subcategories: [
      { value: "chairs", label: "Chaises" },
      { value: "tables", label: "Tables" },
      { value: "high_tables", label: "Mange-debout" },
      { value: "lounge", label: "Salons & canapés" },
      { value: "chair_covers", label: "Housses de chaises" },
      { value: "bars", label: "Bars & comptoirs" },
    ],
  },
  {
    value: "tableware", label: "Art de la table", icon: "fa-solid fa-wine-glass", tagline: "Verres, vaisselle et couverts",
    subcategories: [
      { value: "glasses", label: "Verres" },
      { value: "plates", label: "Assiettes" },
      { value: "cutlery", label: "Couverts" },
      { value: "charger_plates", label: "Assiettes de présentation" },
      { value: "jugs", label: "Carafes & pichets" },
      { value: "trays", label: "Plateaux & présentoirs" },
    ],
  },
  {
    value: "textile", label: "Linge & textile", icon: "fa-solid fa-rug", tagline: "Nappes, serviettes et tentures",
    subcategories: [
      { value: "tablecloths", label: "Nappes" },
      { value: "napkins", label: "Serviettes" },
      { value: "runners", label: "Chemins de table" },
      { value: "drapes", label: "Tentures & voilages" },
      { value: "carpets", label: "Tapis" },
    ],
  },
  {
    value: "decoration", label: "Décoration", icon: "fa-solid fa-wand-magic-sparkles", tagline: "Centres de table, fleurs et arches",
    subcategories: [
      { value: "centerpieces", label: "Centres de table" },
      { value: "flowers", label: "Fleurs artificielles" },
      { value: "arches", label: "Arches & backdrops" },
      { value: "candles", label: "Bougies & photophores" },
      { value: "balloons", label: "Ballons" },
      { value: "signage", label: "Panneaux & signalétique" },
    ],
  },
  {
    value: "lighting", label: "Éclairage", icon: "fa-solid fa-lightbulb", tagline: "Projecteurs, guirlandes et lustres",
    subcategories: [
      { value: "spotlights", label: "Projecteurs" },
      { value: "string_lights", label: "Guirlandes lumineuses" },
      { value: "chandeliers", label: "Lustres" },
      { value: "led", label: "Éclairage LED" },
      { value: "effects", label: "Effets lumineux" },
    ],
  },
  {
    value: "sound", label: "Son & vidéo", icon: "fa-solid fa-volume-high", tagline: "Enceintes, micros et écrans",
    subcategories: [
      { value: "speakers", label: "Enceintes" },
      { value: "microphones", label: "Micros" },
      { value: "mixers", label: "Tables de mixage" },
      { value: "screens", label: "Écrans & vidéoprojecteurs" },
      { value: "cables", label: "Câbles & accessoires" },
    ],
  },
  {
    value: "structure", label: "Structures & scènes", icon: "fa-solid fa-tents", tagline: "Tentes, podiums et pistes",
    subcategories: [
      { value: "tents", label: "Tentes & chapiteaux" },
      { value: "stages", label: "Podiums & scènes" },
      { value: "dance_floors", label: "Pistes de danse" },
      { value: "barriers", label: "Barrières & potelets" },
      { value: "red_carpet", label: "Tapis rouges" },
    ],
  },
  {
    value: "catering", label: "Traiteur & service", icon: "fa-solid fa-utensils", tagline: "Chafing dishes, fontaines et buffets",
    subcategories: [
      { value: "chafing_dishes", label: "Chafing dishes" },
      { value: "fountains", label: "Fontaines" },
      { value: "coolers", label: "Glacières & seaux" },
      { value: "buffet", label: "Matériel de buffet" },
      { value: "cooking", label: "Cuisson" },
    ],
  },
  {
    value: "other", label: "Autre", icon: "fa-solid fa-box-open", tagline: "Tout le reste", subcategories: [],
  },
];

export function findCategory(value) {
  return SALE_CATEGORIES.find((c) => c.value === value) || null;
}

export function subcategoryLabel(categoryValue, subValue) {
  return findCategory(categoryValue)?.subcategories.find((s) => s.value === subValue)?.label || "";
}

export function formatMoney(amount, currency = "XAF") {
  return `${Number(amount || 0).toLocaleString("fr-FR")} ${currency === "XAF" ? "FCFA" : currency}`;
}

// Photo principale puis photos supplémentaires, dans l'ordre d'affichage.
export function productImages(listing) {
  return [listing.photo, ...(listing.photos || []).map((p) => p.image)].filter(Boolean);
}

// Pièces disponibles aujourd'hui (calculé par le serveur : stock possédé
// moins locations en cours ou à venir). `null` = stock non suivi (illimité).
export function availableOf(listing) {
  return listing.available_stock !== undefined ? listing.available_stock : listing.stock ?? null;
}

export function stockLabel(listing) {
  const stock = availableOf(listing);
  if (stock === null) return { text: "En stock", tone: "ok" };
  if (stock <= 0) return { text: "Rupture de stock", tone: "out" };
  if (stock <= 5) return { text: `Plus que ${stock} pièce${stock > 1 ? "s" : ""}`, tone: "low" };
  return { text: `${stock} pièces disponibles`, tone: "ok" };
}

// Modes proposés par un produit, pour les badges « Achat » / « Location ».
export function offerModes(listing) {
  return {
    sale: listing.is_for_sale !== false,
    rent: Boolean(listing.is_for_rent && listing.rental_price),
  };
}

// Nombre de jours d'une location, dates incluses (du 10 au 11 = 2 jours).
export function rentalDays(start, end) {
  if (!start || !end) return 0;
  const days = Math.round((new Date(`${end}T00:00:00`) - new Date(`${start}T00:00:00`)) / 86400000) + 1;
  return days > 0 ? days : 0;
}

export function formatDay(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" }) : "";
}
