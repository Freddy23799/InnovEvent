<script setup>
import ImageLightbox from "./components/ImageLightbox.vue";
import OfflineBanner from "./components/OfflineBanner.vue";
import ToastContainer from "./components/ToastContainer.vue";
import TopProgressBar from "./components/TopProgressBar.vue";
</script>

<template>
  <TopProgressBar />
  <router-view />
  <ImageLightbox />
  <ToastContainer />
  <OfflineBanner />
</template>
