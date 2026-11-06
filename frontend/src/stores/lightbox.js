import { defineStore } from "pinia";

// `open` affiche une image seule ; `openGallery` ouvre une série (portfolio,
// réalisations…) que l'on parcourt avec les flèches, le clavier ou un glissé.
export const useLightboxStore = defineStore("lightbox", {
  state: () => ({
    items: [],
    index: 0,
  }),
  getters: {
    current: (state) => state.items[state.index] || null,
    imageUrl() {
      return this.current?.url || null;
    },
    caption() {
      return this.current?.caption || "";
    },
    hasMany: (state) => state.items.length > 1,
  },
  actions: {
    open(imageUrl, caption = "") {
      this.items = imageUrl ? [{ url: imageUrl, caption }] : [];
      this.index = 0;
    },
    openGallery(items, startIndex = 0) {
      this.items = items.filter((item) => item.url);
      this.index = Math.min(Math.max(startIndex, 0), Math.max(this.items.length - 1, 0));
    },
    next() {
      if (this.hasMany) this.index = (this.index + 1) % this.items.length;
    },
    prev() {
      if (this.hasMany) this.index = (this.index - 1 + this.items.length) % this.items.length;
    },
    close() {
      this.items = [];
      this.index = 0;
    },
  },
});
