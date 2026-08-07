<script setup>
import NavBar from './components/NavBar.vue'
</script>

<template>
  <NavBar />
  <main class="main">
    <RouterView />
  </main>
</template>

<style scoped>
.main {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px 60px;
}

@media (max-width: 560px) {
  .main {
    padding: 16px 12px 60px;
  }
}
</style>
