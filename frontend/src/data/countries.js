// Structure prête pour une évolution multi-pays : chaque pays porte son code
// ISO 3166-1 alpha-2 (celui stocké côté backend sur ProfessionalProfile.country)
// et ses villes avec coordonnées approximatives (utilisées pour la recherche
// « près de moi » sans dépendre d'un service de géocodage externe). Pour
// l'instant seul le Cameroun est renseigné — activité réelle de la
// plateforme — mais ajouter un pays plus tard ne demande qu'une nouvelle
// entrée ici, sans changement d'architecture (modèle, filtre, sérialiseur).
export const COUNTRIES = [
  {
    code: "CM",
    name: "Cameroun",
    cities: [
      { name: "Yaoundé", lat: 3.848, lng: 11.5021 },
      { name: "Douala", lat: 4.0511, lng: 9.7679 },
      { name: "Bafoussam", lat: 5.4737, lng: 10.4176 },
      { name: "Bamenda", lat: 5.9631, lng: 10.1591 },
      { name: "Garoua", lat: 9.3265, lng: 13.3958 },
      { name: "Maroua", lat: 10.591, lng: 14.3159 },
      { name: "Ngaoundéré", lat: 7.3167, lng: 13.5833 },
      { name: "Bertoua", lat: 4.5833, lng: 13.6833 },
      { name: "Ebolowa", lat: 2.9, lng: 11.15 },
      { name: "Kribi", lat: 2.9333, lng: 9.9167 },
      { name: "Limbe", lat: 4.0227, lng: 9.2016 },
      { name: "Buea", lat: 4.1559, lng: 9.2415 },
      { name: "Dschang", lat: 5.4453, lng: 10.0534 },
      { name: "Kumba", lat: 4.6363, lng: 9.4469 },
      { name: "Edéa", lat: 3.8, lng: 10.1333 },
    ],
  },
];

export function citiesForCountry(countryCode) {
  return COUNTRIES.find((c) => c.code === countryCode)?.cities || [];
}

export function findCityCoords(countryCode, name) {
  const match = citiesForCountry(countryCode).find(
    (c) => c.name.toLowerCase() === (name || "").trim().toLowerCase()
  );
  return match ? { lat: match.lat, lng: match.lng } : null;
}
