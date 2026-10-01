// Taxonomie des métiers de la Marketplace « Décoration & design intérieur »
// — organisée en 5 grandes familles pour la navigation par blocs (même
// principe que ACTOR_CATEGORY_GROUPS pour la Marketplace des acteurs) et pour
// le sélecteur « Type d'activité » du profil professionnel. Les valeurs
// doivent rester en phase avec apps.providers.models.Provider.Category côté
// backend (une seule source de vérité pour les libellés : ce fichier ; les
// *valeurs* sont validées côté API).
export const INTERIOR_DESIGN_CATEGORY_GROUPS = [
  {
    title: "Conception & études",
    icon: "fa-solid fa-compass-drafting",
    hint: "Le cerveau du projet",
    items: [
      { value: "interior_architect", label: "Architecte d'intérieur" },
      { value: "landscape_architect", label: "Architecte d'extérieur / Paysagiste" },
      { value: "interior_decorator", label: "Décorateur d'intérieur" },
      { value: "home_stager", label: "Home Stager" },
      { value: "design_3d_visualizer", label: "Dessinateur 3D / Visualiseur" },
      { value: "technical_design_office", label: "Bureau d'études (plans techniques)" },
    ],
  },
  {
    title: "Aménagement intérieur — Second œuvre",
    icon: "fa-solid fa-trowel-bricks",
    hint: "Ceux qui font les murs, sols, plafonds",
    items: [
      { value: "carpentry_joinery", label: "Menuiserie / Ébénisterie (cuisine, dressing sur-mesure)" },
      { value: "painting_wall_coverings", label: "Peinture & Revêtements muraux" },
      { value: "tiling_flooring", label: "Carrelage & Revêtements de sol" },
      { value: "ceiling_staff_work", label: "Plafonds & Staff" },
      { value: "home_electrician_lighting", label: "Électricité & Éclairage" },
      { value: "plumbing_sanitary", label: "Plomberie & Sanitaire" },
    ],
  },
  {
    title: "Aménagement extérieur",
    icon: "fa-solid fa-tree",
    items: [
      { value: "garden_landscaping", label: "Aménagement de jardin & espaces verts" },
      { value: "terrace_pergola_poolhouse", label: "Terrasse, pergola, pool house" },
      { value: "pool_builder", label: "Pisciniste" },
      { value: "facade_fencing_gates", label: "Façade, clôture & portails" },
      { value: "outdoor_lighting", label: "Éclairage extérieur" },
    ],
  },
  {
    title: "Mobilier, matériaux & décoration",
    icon: "fa-solid fa-couch",
    hint: "Ceux qui vendent le produit fini",
    items: [
      { value: "custom_standard_furniture", label: "Mobilier sur-mesure & standard" },
      { value: "lighting_fixtures", label: "Luminaires" },
      { value: "fabrics_curtains_linens", label: "Tissus, rideaux, linge de maison" },
      { value: "decor_art_objects", label: "Objets déco & art" },
      { value: "material_suppliers", label: "Fournisseurs de matériaux (bois, pierre, carrelage, peinture)" },
    ],
  },
  {
    title: "Exécution & services complémentaires",
    icon: "fa-solid fa-helmet-safety",
    items: [
      { value: "general_contractor", label: "Entreprise générale / Maître d'œuvre" },
      { value: "moving_installation", label: "Déménagement & Installation" },
      { value: "post_construction_cleaning", label: "Nettoyage fin de chantier" },
      { value: "interior_photographer", label: "Photographe d'intérieur" },
    ],
  },
];

export const INTERIOR_DESIGN_OTHER_CATEGORY_GROUP = {
  title: "Autres catégories",
  icon: "fa-solid fa-ellipsis",
  items: [{ value: "other", label: "Autre" }],
};

export const INTERIOR_DESIGN_CATEGORY_LOOKUP = Object.fromEntries(
  [...INTERIOR_DESIGN_CATEGORY_GROUPS.flatMap((g) => g.items), ...INTERIOR_DESIGN_OTHER_CATEGORY_GROUP.items].map((i) => [i.value, i.label])
);

export const CLIENT_TYPES = [
  { value: "individual", label: "Particulier" },
  { value: "professional", label: "Professionnel" },
  { value: "hotel_restaurant", label: "Hôtel / Restaurant" },
];

export const PRICE_RANGES = [
  { value: "€", label: "€ — Accessible" },
  { value: "€€", label: "€€ — Intermédiaire" },
  { value: "€€€", label: "€€€ — Haut de gamme" },
];
