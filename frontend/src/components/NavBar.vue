<script setup>
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { to: '/attendance', label: '출퇴근', icon: '🐾' },
  { to: '/payroll', label: '급여', icon: '🦴' },
  { to: '/employees', label: '직원', icon: '🐶' },
]
</script>

<template>
  <header class="navbar">
    <div class="brand">
      <span class="brand-icon">🐾</span>
      <span class="brand-name">브라이튼독출근부</span>
    </div>
    <nav class="tabs">
      <RouterLink
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="tab"
        :class="{ active: route.path === tab.to }"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span>{{ tab.label }}</span>
      </RouterLink>
    </nav>
  </header>
</template>

<style scoped>
.navbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 14px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 18px;
}

.brand-icon {
  font-size: 22px;
}

.tabs {
  display: flex;
  gap: 4px;
  background: var(--bg);
  padding: 4px;
  border-radius: var(--radius);
}

.tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: calc(var(--radius) - 4px);
  color: var(--text-sub);
  font-weight: 600;
  font-size: 14px;
  transition: background 0.15s ease, color 0.15s ease;
}

.tab.active {
  background: var(--primary);
  color: #fff;
}

.tab-icon {
  font-size: 16px;
}

@media (max-width: 560px) {
  .navbar {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  .tabs {
    justify-content: space-between;
  }
  .tab {
    flex: 1;
    justify-content: center;
    padding: 10px 8px;
  }
}
</style>
