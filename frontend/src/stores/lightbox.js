import { defineStore } from "pinia";

export const useLightboxStore = defineStore("lightbox", {
  state: () => ({
    imageUrl: null,
    caption: "",
  }),
  actions: {
    open(imageUrl, caption = "") {
      this.imageUrl = imageUrl;
      this.caption = caption;
    },
    close() {
      this.imageUrl = null;
      this.caption = "";
    },
  },
});
