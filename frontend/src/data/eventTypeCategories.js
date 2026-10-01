// « Un seul parcours intelligent » : plutôt que d'afficher les 42 métiers de
// la Marketplace des acteurs d'un coup, le client choisit d'abord le type
// d'événement qu'il organise, et ne voit ensuite que les métiers réellement
// utiles pour CET événement — liste courte et pertinente, sans doublon.
// Les valeurs de catégories doivent rester en phase avec celles de
// actorCategories.js / apps.providers.models.Provider.Category.
export const EVENT_TYPES = [
  { value: "anniv_enfant", label: "Anniversaire Enfant", icon: "fa-solid fa-cake-candles" },
  { value: "anniv_adulte", label: "Anniversaire Adulte", icon: "fa-solid fa-champagne-glasses" },
  { value: "mariage", label: "Mariage / Dot", icon: "fa-solid fa-ring" },
  { value: "gala", label: "Soirée Gala / VIP", icon: "fa-solid fa-star" },
  { value: "conference", label: "Conférence / Séminaire / Salon", icon: "fa-solid fa-chalkboard-user" },
  { value: "team_building", label: "Team Building / Entreprise", icon: "fa-solid fa-people-group" },
];

export const EVENT_TYPE_CATEGORY_MAP = {
  anniv_enfant: [
    "venue_rental", "furniture_rental", "decoration", "balloon_artist", "caterer", "pastry",
    "waitstaff", "photography", "photobooth", "dj", "sound", "mascot", "games_rental", "childcare_service",
  ],
  anniv_adulte: [
    "venue_rental", "furniture_rental", "decoration", "balloon_artist", "caterer", "pastry", "bartender",
    "waitstaff", "photography", "photobooth", "dj", "sound", "stage_lighting", "live_band", "security",
  ],
  mariage: [
    "wedding_planner", "mc", "protocol", "venue_rental", "tent_rental", "furniture_rental", "tableware_rental",
    "generator_electrician", "security", "decoration", "florist", "centerpiece_rental", "caterer", "pastry",
    "bartender", "waitstaff", "photography", "video", "photobooth", "dj", "sound", "stage_lighting", "live_band",
    "makeup_artist", "stylist", "costume_rental", "jeweler", "luxury_car_rental", "guest_transport",
    "hotel_booking", "printing", "childcare_service",
  ],
  gala: [
    "wedding_planner", "mc", "protocol", "venue_rental", "furniture_rental", "generator_electrician", "security",
    "decoration", "lighting", "caterer", "bartender", "waitstaff", "photography", "video", "sound",
    "stage_lighting", "live_band", "luxury_car_rental", "guest_transport", "trophy_rental",
  ],
  conference: [
    "pco_agency", "protocol", "venue_rental", "furniture_rental", "generator_electrician", "security", "caterer",
    "waitstaff", "photography", "video", "sound", "stage_lighting", "guest_transport", "hotel_booking", "printing",
  ],
  team_building: [
    "team_building_coach", "venue_rental", "furniture_rental", "caterer", "waitstaff", "sound", "animation",
    "games_rental", "guest_transport",
  ],
};
