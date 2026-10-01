<script setup>
import { computed } from "vue";
import { useAuthStore } from "../../stores/auth";
import AdminDashboardView from "./AdminDashboardView.vue";
import ClientDashboardView from "./ClientDashboardView.vue";
import OrganizerDashboardView from "./OrganizerDashboardView.vue";
import ParticipantDashboardView from "./ParticipantDashboardView.vue";
import PartnerDashboardView from "./PartnerDashboardView.vue";

const auth = useAuthStore();

const component = computed(() => {
  if (auth.role === "admin") return AdminDashboardView;
  if (auth.role === "client") return ClientDashboardView;
  if (auth.role === "organizer") return OrganizerDashboardView;
  if (auth.role === "partner") return PartnerDashboardView;
  return ParticipantDashboardView;
});
</script>

<template>
  <component :is="component" />
</template>
