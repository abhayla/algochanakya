<template>
  <div class="ai-subnav" data-testid="ai-subnav">
    <router-link
      v-for="item in navItems"
      :key="item.path"
      :to="item.path"
      :class="['subnav-item', { active: isActive(item.path) }]"
      :data-testid="`ai-subnav-${item.id}`"
    >
      <i :class="item.icon"></i>
      {{ item.label }}
    </router-link>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/ai/settings', label: 'Settings', id: 'settings', icon: 'fas fa-cog' },
  { path: '/ai/paper-trading', label: 'Paper Trading', id: 'paper-trading', icon: 'fas fa-chart-line' },
  { path: '/ai/analytics', label: 'Analytics', id: 'analytics', icon: 'fas fa-chart-bar' }
]

const isActive = (path) => route.path === path
</script>

<style scoped>
.ai-subnav {
  display: flex;
  gap: 4px;
  padding: 12px 24px;
  background: white;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
}

.subnav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 14px;
  color: var(--kite-text-secondary, #6c757d);
  text-decoration: none;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.subnav-item:hover {
  color: var(--kite-text-primary, #394046);
  background: var(--kite-bg-light, #f8f9fa);
}

.subnav-item.active {
  color: var(--kite-primary, #387ed1);
  background: var(--kite-primary-light, #e8f1fb);
  font-weight: 500;
}

.subnav-item i {
  font-size: 14px;
}
</style>
