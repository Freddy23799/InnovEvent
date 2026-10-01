import { defineStore } from "pinia";

// Confirmation visible et systématique après un enregistrement (« on doit
// sentir l'enregistrement ») — un seul composant global (ToastContainer,
// monté dans App.vue) plutôt qu'un indicateur bricolé par formulaire.
let nextId = 1;

export const useToastStore = defineStore("toast", {
  state: () => ({
    toasts: [],
  }),
  actions: {
    push(type, message, duration = 2600) {
      const id = nextId++;
      this.toasts.push({ id, type, message });
      setTimeout(() => this.dismiss(id), duration);
      return id;
    },
    success(message, duration) {
      return this.push("success", message, duration);
    },
    error(message, duration) {
      return this.push("error", message, duration ?? 4000);
    },
    dismiss(id) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
  },
});
