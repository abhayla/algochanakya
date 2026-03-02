<template>
  <div class="strategy-multiselect" data-testid="ofo-strategy-select">
    <!-- Trigger Button -->
    <button
      class="select-trigger"
      :class="{ 'is-open': isOpen }"
      @click="toggleDropdown"
      data-testid="ofo-strategy-trigger"
    >
      <span class="trigger-text">
        {{ selectedCount === 0 ? 'Select Strategies' : `${selectedCount} selected` }}
      </span>
      <svg
        class="chevron-icon"
        :class="{ 'rotate-180': isOpen }"
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </button>

    <!-- Dropdown Menu -->
    <div v-if="isOpen" class="dropdown-menu" data-testid="ofo-strategy-dropdown">
      <!-- Header Actions -->
      <div class="dropdown-header">
        <button
          class="header-btn"
          @click="selectAll"
          data-testid="ofo-strategy-select-all"
        >
          Select All
        </button>
        <button
          class="header-btn"
          @click="clearAll"
          data-testid="ofo-strategy-clear-all"
        >
          Clear All
        </button>
      </div>

      <!-- Strategy Options -->
      <div class="options-list">
        <label
          v-for="strategy in strategies"
          :key="strategy.key"
          class="strategy-option"
          :class="getCategoryClass(strategy.category)"
          :data-testid="`ofo-strategy-option-${strategy.key}`"
        >
          <input
            type="checkbox"
            :checked="isSelected(strategy.key)"
            @change="toggleStrategy(strategy.key)"
          />
          <span class="option-name">{{ strategy.name }}</span>
          <span class="option-legs">{{ strategy.legs_count }} legs</span>
        </label>
      </div>
    </div>

    <!-- Backdrop to close dropdown -->
    <div
      v-if="isOpen"
      class="dropdown-backdrop"
      data-testid="ofo-dropdown-backdrop"
      @click="closeDropdown"
    ></div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useOFOStore } from '@/stores/ofo'

const ofoStore = useOFOStore()

const isOpen = ref(false)

const strategies = computed(() => ofoStore.availableStrategies)
const selectedCount = computed(() => ofoStore.selectedCount)

function toggleDropdown() {
  isOpen.value = !isOpen.value
}

function closeDropdown() {
  isOpen.value = false
}

function isSelected(strategyKey) {
  return ofoStore.isStrategySelected(strategyKey)
}

function toggleStrategy(strategyKey) {
  ofoStore.toggleStrategy(strategyKey)
}

function selectAll() {
  ofoStore.selectAllStrategies()
}

function clearAll() {
  ofoStore.clearStrategies()
}

function getCategoryClass(category) {
  return `category-${category}`
}
</script>

<style scoped>
.strategy-multiselect {
  position: relative;
}

.select-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--kite-card-bg, #ffffff);
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 3px;
  color: var(--kite-text-primary, #394046);
  font-size: 14px;
  cursor: pointer;
  min-width: 160px;
  transition: all 0.15s ease;
}

.select-trigger:hover {
  border-color: var(--kite-primary, #2d68b0);
}

.select-trigger.is-open {
  border-color: var(--kite-primary, #2d68b0);
  box-shadow: 0 0 0 2px rgba(45, 104, 176, 0.15);
}

.trigger-text {
  flex: 1;
  text-align: left;
}

.chevron-icon {
  transition: transform 0.15s ease;
  color: var(--kite-text-secondary, #6c757d);
}

.chevron-icon.rotate-180 {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 100;
  min-width: 220px;
  background: var(--kite-card-bg, #ffffff);
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 4px;
  box-shadow: var(--kite-shadow-lg, 0 4px 16px rgba(0,0,0,0.08));
  overflow: hidden;
}

.dropdown-header {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--kite-border, #e8e8e8);
  background: var(--kite-table-header-bg, #fafbfc);
}

.header-btn {
  flex: 1;
  padding: 6px 10px;
  font-size: 12px;
  background: var(--kite-card-bg, #ffffff);
  border: 1px solid var(--kite-border, #e8e8e8);
  border-radius: 3px;
  color: var(--kite-text-secondary, #6c757d);
  cursor: pointer;
  transition: all 0.15s ease;
}

.header-btn:hover {
  background: var(--kite-primary, #2d68b0);
  color: white;
  border-color: var(--kite-primary, #2d68b0);
}

.options-list {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px 0;
}

.strategy-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.strategy-option:hover {
  background: var(--kite-table-hover, #f5f8fa);
}

.strategy-option input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--kite-primary, #2d68b0);
  cursor: pointer;
}

.option-name {
  flex: 1;
  font-size: 14px;
  color: var(--kite-text-primary, #394046);
}

.option-legs {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--kite-table-header-bg, #fafbfc);
  border: 1px solid var(--kite-border-light, #f5f5f5);
  border-radius: 3px;
  color: var(--kite-text-secondary, #6c757d);
}

/* Category colors */
.category-neutral .option-name::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #6c757d;
  margin-right: 8px;
}

.category-bullish .option-name::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--kite-green, #00b386);
  margin-right: 8px;
}

.category-bearish .option-name::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--kite-red, #e53935);
  margin-right: 8px;
}

.category-volatile .option-name::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9b59b6;
  margin-right: 8px;
}

.dropdown-backdrop {
  position: fixed;
  inset: 0;
  z-index: 99;
}
</style>
