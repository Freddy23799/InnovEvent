// Taxonomie des métiers de la Marketplace des acteurs événementiels — « INO
// Marketplace, nomenclature officielle des métiers » — groupée en 10
// catégories pour la navigation par blocs et pour la barre latérale (un
// groupe dépliable par catégorie). Les valeurs doivent rester en phase avec
// apps.providers.models.Provider.Category côté backend (une seule source de
// vérité pour les libellés : ce fichier ; les *valeurs* sont validées côté API).
export const ACTOR_CATEGORY_GROUPS = [
  {
    title: "Organisation & coordination",
    featureKey: "group_organisation",
    icon: "fa-solid fa-clipboard-list",
    items: [
      { value: "wedding_planner", label: "Wedding Planner / Event Planner" },
      { value: "mc", label: "Maître de Cérémonie (MC) - Bilingue" },
      { value: "protocol", label: "Protocole / Hôtesses d'accueil" },
      { value: "pco_agency", label: "Agence PCO - Organisateur de Conférences / Salons" },
      { value: "team_building_coach", label: "Coach / Formateur Team Building" },
    ],
  },
  {
    title: "Lieu & logistique de base",
    featureKey: "group_logistique",
    icon: "fa-solid fa-warehouse",
    items: [
      { value: "venue_rental", label: "Location de salle / Villa / Domaine / Hôtel / Jardin / Piscine" },
      { value: "tent_rental", label: "Location de chapiteaux / Tentes / Bâches / Structures" },
      { value: "furniture_rental", label: "Location de mobilier : Chaises, Tables, Nappes, Housses" },
      { value: "tableware_rental", label: "Location de vaisselle / Verrerie / Couverts / Chauffe-plats" },
      { value: "generator_electrician", label: "Groupe électrogène + Électricien / Technicien" },
      { value: "security", label: "Sécurité / Agent / Videur / Sécurité rapprochée" },
      { value: "cleaning_service", label: "Service de Nettoyage / Remise en état" },
    ],
  },
  {
    title: "Décoration & scénographie",
    featureKey: "group_decoration",
    icon: "fa-solid fa-palette",
    items: [
      { value: "decoration", label: "Décorateur / Designer Événementiel / Scénographe" },
      { value: "florist", label: "Fleuriste événementiel" },
      { value: "centerpiece_rental", label: "Décor : Centre de table, Arche, Backdrop, Moquette, Lustres" },
      { value: "balloon_artist", label: "Artiste Ballon / Décorateur Ballons organiques" },
      { value: "lighting", label: "Éclairagiste d'ambiance / Éclairage architectural" },
    ],
  },
  {
    title: "Restauration & boissons",
    featureKey: "group_restauration",
    icon: "fa-solid fa-utensils",
    items: [
      { value: "caterer", label: "Traiteur / Chef à domicile / Buffet / Rôtisseur" },
      { value: "pastry", label: "Pâtissier / Cake Designer / Glacier / Fontaine Chocolat" },
      { value: "bartender", label: "Barman / Mixologue / Service Bar Mobile" },
      { value: "waitstaff", label: "Serveur / Serveuse Professionnel(le)" },
    ],
  },
  {
    title: "Image & souvenirs",
    featureKey: "group_image",
    icon: "fa-solid fa-camera-retro",
    items: [
      { value: "photography", label: "Photographe (Mariage, Corporate, Anniversaire)" },
      { value: "video", label: "Vidéaste / Cameraman / Pilote Drone / Retransmission Live" },
      { value: "photobooth", label: "Photobooth / Miroir Photo / 360° Booth / Audioguestbook" },
    ],
  },
  {
    title: "Son, musique & lumière",
    featureKey: "group_musique",
    icon: "fa-solid fa-music",
    items: [
      { value: "dj", label: "DJ / Disc-Jockey" },
      { value: "sound", label: "Technicien Sonorisation / Sono complète / Traducteur simultané" },
      { value: "stage_lighting", label: "Technicien Lumière / Jeux de lumière / Fumigène / Écran LED" },
      { value: "live_band", label: "Groupe Live / Orchestre / Artiste / Chanteur / Saxophoniste" },
    ],
  },
  {
    title: "Animation & spectacle",
    featureKey: "group_animation",
    icon: "fa-solid fa-masks-theater",
    items: [
      { value: "animation", label: "Animateur / Danseurs / Troupe de danse" },
      { value: "entertainer", label: "Humoriste / Magicien / Cracheur de feu / Échassier" },
      { value: "mascot", label: "Mascottes / Personnages pour enfants / Clown" },
      { value: "games_rental", label: "Jeux : Château Gonflable, Trampoline, Jeux en bois, Baby-foot" },
    ],
  },
  {
    title: "Beauté, mode & tenue",
    featureKey: "group_beaute",
    icon: "fa-solid fa-spa",
    items: [
      { value: "makeup_artist", label: "Maquilleuse (MUA) / Coiffeuse / Prothésiste Ongulaire" },
      { value: "stylist", label: "Styliste / Créateur de Robes / Tailleur Costume sur-mesure" },
      { value: "costume_rental", label: "Location de Tenues Traditionnelles / Costumes / Voiles" },
      { value: "jeweler", label: "Bijoutier / Créateur d'Alliances / Loueur de Bijoux" },
    ],
  },
  {
    title: "Transport & hébergement",
    featureKey: "group_transport",
    icon: "fa-solid fa-car",
    items: [
      { value: "luxury_car_rental", label: "Location de Voitures de Luxe / Limousine / Voiture Mariés" },
      { value: "guest_transport", label: "Location de Bus / Navette / Transport Invités / Voiturier" },
      { value: "hotel_booking", label: "Réservation Hôtel / Hébergement Invités / Accueil Aéroport" },
    ],
  },
  {
    title: "Support & impression",
    featureKey: "group_support",
    icon: "fa-solid fa-file-signature",
    items: [
      { value: "printing", label: "Imprimeur : Faire-part, Invitations, Menus, Badges, Roll-up, Banderoles" },
      { value: "childcare_service", label: "Service Nounou / Gardiennage d'Enfants pour événement" },
      { value: "trophy_rental", label: "Loueur de Trophées / Awards pour Gala" },
    ],
  },
];

// Catégories historiques conservées (anciens profils déjà publiés, ou utilisées
// par d'autres marketplaces comme la décoration & design intérieur) — non
// affichées dans l'index par blocs ni dans la sidebar, mais toujours proposées
// au choix lorsqu'un prestataire crée ou modifie son profil.
export const OTHER_CATEGORY_GROUP = {
  title: "Autres catégories",
  icon: "fa-solid fa-ellipsis",
  items: [
    { value: "interior_architect", label: "Architecte / designer d'intérieur" },
    { value: "agency", label: "Agence événementielle" },
    { value: "graphic_design", label: "Graphisme & infographie" },
    { value: "equipment_rental", label: "Location de matériel" },
    { value: "venue_manager", label: "Responsable de salle" },
    { value: "impresario", label: "Impresario" },
    { value: "ice_cream_fountain", label: "Glacier / Fontaine à chocolat" },
    { value: "guestbook", label: "Livre d'or / Audioguest" },
    { value: "hairdresser", label: "Coiffeuse" },
    { value: "manicure", label: "Manucure / Onglerie" },
    { value: "website_creator", label: "Créateur de site web pour l'événement" },
    { value: "other", label: "Autre" },
  ],
};

export const ACTOR_CATEGORY_LOOKUP = Object.fromEntries(
  [...ACTOR_CATEGORY_GROUPS.flatMap((g) => g.items), ...OTHER_CATEGORY_GROUP.items].map((i) => [i.value, i.label])
);
