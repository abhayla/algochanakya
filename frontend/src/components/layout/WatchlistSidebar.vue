<template>
  <div class="watchlist-sidebar">
    <!-- Header -->
    <div class="sidebar-header">
      <div class="header-left">
        <span class="title">Watchlist</span>
        <span class="count">({{ totalCount }} / 250)</span>
      </div>
      <button class="new-group-btn" @click="$emit('create-watchlist')">
        <span>+</span> New
      </button>
    </div>

    <!-- Group Tabs -->
    <div class="group-tabs" v-if="watchlists.length > 0">
      <button
        v-for="wl in watchlists"
        :key="wl.id"
        :class="['group-tab', { active: activeWatchlistId === wl.id }]"
        @click="$emit('select-watchlist', wl.id)"
      >
        {{ wl.name }} ({{ wl.instruments?.length || 0 }})
      </button>
    </div>

    <!-- Search -->
    <div class="search-bar">
      <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/>
        <path d="M21 21l-4.35-4.35"/>
      </svg>
      <input
        type="text"
        v-model="searchQuery"
        placeholder="Search eg: infy bse, nifty fut"
        class="search-input"
        @input="onSearchInput"
      />
    </div>

    <!-- Search Results -->
    <div v-if="searchQuery && searchResults.length > 0" class="search-results">
      <div
        v-for="result in searchResults"
        :key="result.token"
        class="search-result-item"
        @click="addInstrument(result)"
      >
        <div class="result-info">
          <span class="result-symbol">{{ result.tradingsymbol }}</span>
          <span class="result-exchange">{{ result.exchange }}</span>
        </div>
        <button class="add-btn">+</button>
      </div>
    </div>

    <!-- Stock List -->
    <div class="stock-list" v-else>
      <div
        v-for="stock in stocks"
        :key="stock.token"
        class="stock-row"
        @click="$emit('select', stock)"
      >
        <div class="stock-info">
          <span class="stock-symbol">{{ stock.tradingsymbol || stock.symbol }}</span>
          <span v-if="stock.exchange" class="stock-exchange">{{ stock.exchange }}</span>
        </div>
        <div class="stock-price-info">
          <span :class="['stock-change', (stock.tick?.change || 0) >= 0 ? 'up' : 'down']">
            {{ formatChange(stock.tick?.change) }}
          </span>
          <span :class="['stock-pct', (stock.tick?.change || 0) >= 0 ? 'up' : 'down']">
            {{ formatPct(stock.tick?.change_percent) }}
            <span class="arrow">{{ (stock.tick?.change || 0) >= 0 ? '▲' : '▼' }}</span>
          </span>
          <span class="stock-ltp">{{ formatPrice(stock.tick?.ltp) }}</span>
        </div>
        <button class="remove-btn" @click.stop="$emit('remove', stock.token)" title="Remove">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <div v-if="stocks.length === 0" class="empty-state">
        <p>No instruments in watchlist</p>
        <p class="hint">Search above to add instruments</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  stocks: {
    type: Array,
    default: () => []
  },
  watchlists: {
    type: Array,
    default: () => []
  },
  activeWatchlistId: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(['select', 'remove', 'search', 'add-instrument', 'select-watchlist', 'create-watchlist']);

const searchQuery = ref('');
const searchResults = ref([]);
let searchTimeout = null;

const totalCount = computed(() => {
  return props.watchlists.reduce((sum, wl) => sum + (wl.instruments?.length || 0), 0);
});

const formatPrice = (price) => {
  if (!price) return '--';
  return new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(price);
};

const formatChange = (change) => {
  if (change === null || change === undefined) return '--';
  return (change >= 0 ? '+' : '') + change.toFixed(2);
};

const formatPct = (pct) => {
  if (pct === null || pct === undefined) return '--%';
  return (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
};

const onSearchInput = () => {
  clearTimeout(searchTimeout);
  if (searchQuery.value.length < 2) {
    searchResults.value = [];
    return;
  }

  searchTimeout = setTimeout(() => {
    emit('search', searchQuery.value, (results) => {
      searchResults.value = results || [];
    });
  }, 300);
};

const addInstrument = (instrument) => {
  emit('add-instrument', instrument);
  searchQuery.value = '';
  searchResults.value = [];
};
</script>

<style scoped>
.watchlist-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e0e0e0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title {
  font-size: 14px;
  font-weight: 600;
  color: #212529;
}

.count {
  font-size: 12px;
  color: #6c757d;
}

.new-group-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: transparent;
  border: none;
  color: #2196f3;
  font-size: 12px;
  cursor: pointer;
}

.new-group-btn:hover {
  text-decoration: underline;
}

.group-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 16px;
  border-bottom: 1px solid #e0e0e0;
  overflow-x: auto;
}

.group-tab {
  padding: 4px 10px;
  background: transparent;
  border: none;
  font-size: 12px;
  color: #6c757d;
  cursor: pointer;
  border-radius: 3px;
  white-space: nowrap;
}

.group-tab.active {
  background: #f0f0f0;
  color: #212529;
  font-weight: 500;
}

.search-bar {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #e0e0e0;
  gap: 8px;
}

.search-icon {
  width: 16px;
  height: 16px;
  color: #adb5bd;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  padding: 8px 0;
  border: none;
  font-size: 12px;
  outline: none;
  background: transparent;
}

.search-input::placeholder {
  color: #adb5bd;
}

.search-results {
  max-height: 300px;
  overflow-y: auto;
  border-bottom: 1px solid #e0e0e0;
}

.search-result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.1s ease;
}

.search-result-item:hover {
  background: #f8f9fa;
}

.result-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-symbol {
  font-size: 13px;
  font-weight: 500;
  color: #212529;
}

.result-exchange {
  font-size: 9px;
  color: #adb5bd;
  padding: 1px 4px;
  background: #f5f5f5;
  border-radius: 2px;
  text-transform: uppercase;
}

.add-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  background: #e3f2fd;
  color: #2196f3;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-btn:hover {
  background: #2196f3;
  color: white;
}

.stock-list {
  flex: 1;
  overflow-y: auto;
}

.stock-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.1s ease;
  position: relative;
}

.stock-row:hover {
  background: #f8f9fa;
}

.stock-row:hover .remove-btn {
  opacity: 1;
}

.stock-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stock-symbol {
  font-size: 13px;
  font-weight: 500;
  color: #2196f3;
}

.stock-exchange {
  font-size: 9px;
  color: #adb5bd;
  padding: 1px 4px;
  background: #f5f5f5;
  border-radius: 2px;
  text-transform: uppercase;
}

.stock-price-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stock-change {
  font-size: 12px;
}

.stock-pct {
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 2px;
}

.stock-pct .arrow {
  font-size: 8px;
}

.stock-ltp {
  font-size: 13px;
  font-weight: 600;
  color: #212529;
  min-width: 70px;
  text-align: right;
}

.up { color: #00b386; }
.down { color: #e74c3c; }

.remove-btn {
  position: absolute;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 3px;
  border: none;
  background: transparent;
  color: #adb5bd;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.15s ease;
}

.remove-btn:hover {
  background: #ffebee;
  color: #e74c3c;
}

.remove-btn svg {
  width: 14px;
  height: 14px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  color: #6c757d;
  font-size: 13px;
}

.empty-state .hint {
  font-size: 12px;
  color: #adb5bd;
  margin-top: 4px;
}
</style>
