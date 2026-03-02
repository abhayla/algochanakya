<template>
  <KiteLayout>
    <div class="positions-page" data-testid="positions-page">

      <BrokerUpgradeBanner screen="positions" />

      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <h1 class="page-title">Positions</h1>

          <!-- Day/Net Toggle -->
          <div class="type-toggle" data-testid="positions-type-toggle">
            <button
              :class="['toggle-btn', { active: store.positionType === 'day' }]"
              @click="store.setPositionType('day')"
              data-testid="positions-day-button"
            >
              Day
            </button>
            <button
              :class="['toggle-btn', { active: store.positionType === 'net' }]"
              @click="store.setPositionType('net')"
              data-testid="positions-net-button"
            >
              Net
            </button>
          </div>
        </div>

        <div class="header-right">
          <DataSourceBadge screen="positions" />
          <!-- Total P&L Box -->
          <div :class="['pnl-box', store.summary.total_pnl >= 0 ? 'profit' : 'loss']" data-testid="positions-pnl-box">
            <span class="pnl-label">Total P&L</span>
            <span class="pnl-value">
              {{ store.summary.total_pnl >= 0 ? '+' : '' }}{{ formatNumber(store.summary.total_pnl) }}
            </span>
            <span class="pnl-pct">
              ({{ store.summary.total_pnl_pct >= 0 ? '+' : '' }}{{ store.summary.total_pnl_pct }}%)
            </span>
          </div>

          <!-- Auto Refresh -->
          <label class="auto-refresh-toggle">
            <input type="checkbox" v-model="autoRefresh" @change="toggleAutoRefresh" />
            <span>Auto Refresh</span>
          </label>

          <!-- Refresh Button -->
          <button @click="store.fetchPositions()" class="refresh-btn" :disabled="store.isLoading" data-testid="positions-refresh-btn">
            <span v-if="store.isLoading" class="spinner"></span>
            {{ store.isLoading ? '' : 'Refresh' }}
          </button>

          <!-- Exit All -->
          <button
            @click="confirmExitAll = true"
            class="exit-all-btn"
            :disabled="store.positions.length === 0"
          >
            Exit All
          </button>
        </div>
      </div>

      <!-- Summary Bar -->
      <div class="summary-bar" v-if="store.positions.length > 0" data-testid="positions-summary-bar">
        <div class="summary-item">
          <span class="label">Positions</span>
          <span class="value">{{ store.summary.total_positions }}</span>
        </div>
        <div class="summary-item">
          <span class="label">Quantity</span>
          <span class="value">{{ store.summary.total_quantity }}</span>
        </div>
        <div class="summary-item">
          <span class="label">Realized</span>
          <span :class="['value', store.summary.realized_pnl >= 0 ? 'text-green' : 'text-red']">
            {{ formatNumber(store.summary.realized_pnl) }}
          </span>
        </div>
        <div class="summary-item">
          <span class="label">Unrealized</span>
          <span :class="['value', store.summary.unrealized_pnl >= 0 ? 'text-green' : 'text-red']">
            {{ formatNumber(store.summary.unrealized_pnl) }}
          </span>
        </div>
        <div class="summary-item">
          <span class="label">Margin Used</span>
          <span class="value">{{ formatNumber(store.summary.margin_used) }}</span>
        </div>
        <div class="summary-item">
          <span class="label">Available</span>
          <span class="value text-green">{{ formatNumber(store.summary.margin_available) }}</span>
        </div>
      </div>

      <!-- Positions Table -->
      <div class="positions-table-container scrollable-container" ref="tableContainer" data-testid="positions-table-container">
        <table class="positions-table" v-if="store.positions.length > 0" data-testid="positions-table">
          <thead>
            <tr>
              <th class="instrument-col">Instrument</th>
              <th class="text-center">Product</th>
              <th class="text-right">Qty</th>
              <th class="text-right">Avg Price</th>
              <th class="text-right">LTP</th>
              <th class="text-right">Day Chg</th>
              <th class="text-right">P&L</th>
              <th class="text-right">Chg%</th>
              <th class="actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="pos in store.positions"
              :key="pos.tradingsymbol"
              :class="['position-row', { 'profit': pos.pnl > 0, 'loss': pos.pnl < 0 }]"
              :data-testid="`positions-row-${pos.tradingsymbol}`"
            >
              <!-- Instrument -->
              <td class="instrument-col">
                <div class="instrument-info">
                  <div class="instrument-header">
                    <span class="instrument-name">{{ pos.tradingsymbol }}</span>
                    <AutoPilotBadge
                      v-if="pos.is_autopilot"
                      :strategy="{
                        id: pos.autopilot_strategy_id,
                        name: pos.autopilot_strategy_name,
                        trading_mode: pos.autopilot_trading_mode
                      }"
                    />
                  </div>
                  <div class="instrument-meta">
                    <span class="underlying">{{ pos.underlying }}</span>
                    <span v-if="pos.option_type" :class="['option-badge', pos.option_type.toLowerCase()]">
                      {{ pos.option_type }}
                    </span>
                    <span class="strike" v-if="pos.strike">{{ pos.strike }}</span>
                  </div>
                </div>
              </td>

              <!-- Product -->
              <td class="text-center">
                <span class="product-badge">{{ pos.product }}</span>
              </td>

              <!-- Quantity -->
              <td class="text-right">
                <span :class="['qty', pos.quantity > 0 ? 'long' : 'short']">
                  {{ pos.quantity > 0 ? '+' : '' }}{{ pos.quantity }}
                </span>
              </td>

              <!-- Avg Price -->
              <td class="text-right">{{ formatPrice(pos.average_price) }}</td>

              <!-- LTP -->
              <td class="text-right font-semibold">{{ formatPrice(pos.ltp) }}</td>

              <!-- Day Change -->
              <td class="text-right" :class="pos.day_change >= 0 ? 'text-green' : 'text-red'">
                {{ pos.day_change >= 0 ? '+' : '' }}{{ formatPrice(pos.day_change) }}
                <span class="change-pct">({{ pos.day_change_pct >= 0 ? '+' : '' }}{{ pos.day_change_pct.toFixed(2) }}%)</span>
              </td>

              <!-- P&L -->
              <td class="text-right">
                <span :class="['pnl', pos.pnl >= 0 ? 'profit' : 'loss']"
                  :data-pnl-polarity="pos.pnl >= 0 ? 'positive' : 'negative'">
                  {{ pos.pnl >= 0 ? '+' : '' }}{{ formatNumber(pos.pnl) }}
                </span>
              </td>

              <!-- Change % -->
              <td class="text-right">
                <span :class="['pnl-pct', pos.pnl_pct >= 0 ? 'profit' : 'loss']">
                  {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct.toFixed(2) }}%
                </span>
              </td>

              <!-- Actions -->
              <td class="actions-col">
                <div class="action-buttons">
                  <button @click="store.openExitModal(pos)" class="btn-exit" :data-testid="`positions-exit-button-${pos.tradingsymbol}`">
                    Exit
                  </button>
                  <button @click="store.openAddModal(pos)" class="btn-add" :data-testid="`positions-add-button-${pos.tradingsymbol}`">
                    Add
                  </button>
                </div>
              </td>
            </tr>
          </tbody>

          <!-- Total Row -->
          <tfoot>
            <tr class="total-row">
              <td colspan="6" class="text-right font-semibold">Total</td>
              <td class="text-right">
                <span :class="['pnl', 'font-bold', store.summary.total_pnl >= 0 ? 'profit' : 'loss']">
                  {{ store.summary.total_pnl >= 0 ? '+' : '' }}{{ formatNumber(store.summary.total_pnl) }}
                </span>
              </td>
              <td class="text-right">
                <span :class="['pnl-pct', store.summary.total_pnl_pct >= 0 ? 'profit' : 'loss']">
                  {{ store.summary.total_pnl_pct >= 0 ? '+' : '' }}{{ store.summary.total_pnl_pct }}%
                </span>
              </td>
              <td></td>
            </tr>
          </tfoot>
        </table>

        <!-- Empty State -->
        <div v-else-if="!store.isLoading" class="empty-state" data-testid="positions-empty-state">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
          </div>
          <h3>No Open Positions</h3>
          <p>You don't have any open F&O positions.</p>
          <router-link to="/optionchain" class="btn-primary">
            Go to Option Chain
          </router-link>
        </div>

        <!-- Loading State -->
        <div v-else class="loading-state">
          <div class="spinner large"></div>
          <p>Loading positions...</p>
        </div>
      </div>

      <!-- Exit Modal -->
      <div v-if="store.exitModal.show" class="modal-overlay" @click.self="store.closeExitModal()" data-testid="positions-exit-modal-overlay">
        <div class="modal" data-testid="positions-exit-modal">
          <div class="modal-header">
            <h3>Exit Position</h3>
            <button @click="store.closeExitModal()" class="modal-close" data-testid="positions-exit-modal-close">&times;</button>
          </div>

          <div class="modal-body">
            <div class="position-summary">
              <span class="symbol">{{ store.exitModal.position?.tradingsymbol }}</span>
              <span :class="['qty', store.exitModal.position?.quantity > 0 ? 'long' : 'short']">
                {{ store.exitModal.position?.quantity > 0 ? 'LONG' : 'SHORT' }}
                {{ Math.abs(store.exitModal.position?.quantity) }}
              </span>
            </div>

            <div class="form-group">
              <label>Order Type</label>
              <div class="order-type-toggle">
                <button
                  :class="['toggle-btn', { active: store.exitModal.orderType === 'MARKET' }]"
                  @click="store.exitModal.orderType = 'MARKET'"
                >
                  Market
                </button>
                <button
                  :class="['toggle-btn', { active: store.exitModal.orderType === 'LIMIT' }]"
                  @click="store.exitModal.orderType = 'LIMIT'"
                >
                  Limit
                </button>
              </div>
            </div>

            <div class="form-group" v-if="store.exitModal.orderType === 'LIMIT'">
              <label>Price</label>
              <input
                type="number"
                v-model.number="store.exitModal.price"
                step="0.05"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label>Quantity</label>
              <input
                type="number"
                v-model.number="store.exitModal.quantity"
                :max="Math.abs(store.exitModal.position?.quantity)"
                class="form-input"
              />
            </div>
          </div>

          <div class="modal-footer">
            <button @click="store.closeExitModal()" class="btn-secondary">Cancel</button>
            <button @click="executeExit()" class="btn-danger" :disabled="isExiting">
              {{ isExiting ? 'Exiting...' : 'Exit Position' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Add Modal -->
      <div v-if="store.addModal.show" class="modal-overlay" @click.self="store.closeAddModal()" data-testid="positions-add-modal-overlay">
        <div class="modal" data-testid="positions-add-modal">
          <div class="modal-header">
            <h3>Add to Position</h3>
            <button @click="store.closeAddModal()" class="modal-close" data-testid="positions-add-modal-close">&times;</button>
          </div>

          <div class="modal-body">
            <div class="position-summary">
              <span class="symbol">{{ store.addModal.position?.tradingsymbol }}</span>
              <span class="ltp">LTP: {{ formatPrice(store.addModal.position?.ltp) }}</span>
            </div>

            <div class="form-group">
              <label>Transaction</label>
              <div class="order-type-toggle">
                <button
                  :class="['toggle-btn buy', { active: store.addModal.transactionType === 'BUY' }]"
                  @click="store.addModal.transactionType = 'BUY'"
                >
                  BUY
                </button>
                <button
                  :class="['toggle-btn sell', { active: store.addModal.transactionType === 'SELL' }]"
                  @click="store.addModal.transactionType = 'SELL'"
                >
                  SELL
                </button>
              </div>
            </div>

            <div class="form-group">
              <label>Price</label>
              <input
                type="number"
                v-model.number="store.addModal.price"
                step="0.05"
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label>Quantity</label>
              <input
                type="number"
                v-model.number="store.addModal.quantity"
                class="form-input"
              />
            </div>
          </div>

          <div class="modal-footer">
            <button @click="store.closeAddModal()" class="btn-secondary">Cancel</button>
            <button
              @click="executeAdd()"
              :class="['btn-action', store.addModal.transactionType === 'BUY' ? 'btn-buy' : 'btn-sell']"
              :disabled="isAdding"
            >
              {{ isAdding ? 'Placing...' : store.addModal.transactionType }}
            </button>
          </div>
        </div>
      </div>

      <!-- Exit All Confirmation -->
      <div v-if="confirmExitAll" class="modal-overlay" @click.self="confirmExitAll = false">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h3>Confirm Exit All</h3>
          </div>
          <div class="modal-body">
            <p>Are you sure you want to exit <strong>{{ store.positions.length }} positions</strong>?</p>
            <p class="text-red warning-text">This will place MARKET orders to close all positions.</p>
          </div>
          <div class="modal-footer">
            <button @click="confirmExitAll = false" class="btn-secondary">Cancel</button>
            <button @click="executeExitAll()" class="btn-danger" :disabled="isExitingAll">
              {{ isExitingAll ? 'Exiting...' : 'Yes, Exit All' }}
            </button>
          </div>
        </div>
      </div>

    </div>
  </KiteLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import KiteLayout from '@/components/layout/KiteLayout.vue';
import AutoPilotBadge from '@/components/autopilot/positions/AutoPilotBadge.vue';
import { usePositionsStore } from '@/stores/positions';
import { useScrollIndicator } from '@/composables/useScrollIndicator';
import BrokerUpgradeBanner from '@/components/common/BrokerUpgradeBanner.vue';
import DataSourceBadge from '@/components/common/DataSourceBadge.vue';

const store = usePositionsStore();

// Table scroll indicator
const tableContainer = ref(null);
useScrollIndicator(tableContainer);

const autoRefresh = ref(false);
const confirmExitAll = ref(false);
const isExiting = ref(false);
const isAdding = ref(false);
const isExitingAll = ref(false);

// Formatters
const formatNumber = (num) => {
  if (num === null || num === undefined) return '0';
  return new Intl.NumberFormat('en-IN').format(Math.round(num));
};

const formatPrice = (price) => {
  if (!price) return '-';
  return price.toFixed(2);
};

// Auto refresh toggle
const toggleAutoRefresh = () => {
  if (autoRefresh.value) {
    store.startAutoRefresh(5000);
  } else {
    store.stopAutoRefresh();
  }
};

// Execute Exit
const executeExit = async () => {
  isExiting.value = true;
  try {
    await store.exitPosition(
      store.exitModal.position,
      store.exitModal.orderType,
      store.exitModal.price
    );
    store.closeExitModal();
    alert('Exit order placed successfully!');
  } catch (error) {
    alert('Failed to exit: ' + (error.response?.data?.detail || error.message));
  } finally {
    isExiting.value = false;
  }
};

// Execute Add
const executeAdd = async () => {
  isAdding.value = true;
  try {
    await store.addToPosition(
      store.addModal.position,
      store.addModal.transactionType,
      store.addModal.quantity,
      store.addModal.price
    );
    store.closeAddModal();
    alert('Order placed successfully!');
  } catch (error) {
    alert('Failed to place order: ' + (error.response?.data?.detail || error.message));
  } finally {
    isAdding.value = false;
  }
};

// Execute Exit All
const executeExitAll = async () => {
  isExitingAll.value = true;
  try {
    const result = await store.exitAllPositions();
    confirmExitAll.value = false;
    alert(result.message);
  } catch (error) {
    alert('Failed: ' + (error.response?.data?.detail || error.message));
  } finally {
    isExitingAll.value = false;
  }
};

// Lifecycle
onMounted(() => {
  store.fetchPositions();
});

onUnmounted(() => {
  store.stopAutoRefresh();
});
</script>

<style scoped>
.positions-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px - 32px);
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: hidden;
  padding: 0 16px;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  margin-bottom: 12px;
  min-width: 0;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex-shrink: 1;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #212529;
  margin: 0;
}

.type-toggle {
  display: flex;
  gap: 2px;
  background: #f0f0f0;
  padding: 2px;
  border-radius: 4px;
}

.toggle-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: transparent;
  border: none;
  color: #6c757d;
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.15s ease;
}

.toggle-btn:hover {
  color: #212529;
}

.toggle-btn.active {
  background: white;
  color: #212529;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
  flex-shrink: 1;
  flex-wrap: wrap;
}

/* P&L Box */
.pnl-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 4px;
}

.pnl-box.profit {
  background: linear-gradient(135deg, #e6f7f2 0%, #c8f7e6 100%);
}

.pnl-box.loss {
  background: linear-gradient(135deg, #fdeaea 0%, #fbd5d5 100%);
}

.pnl-label {
  font-size: 11px;
  color: #6c757d;
  text-transform: uppercase;
}

.pnl-value {
  font-size: 18px;
  font-weight: 700;
}

.pnl-box.profit .pnl-value { color: #00b386; }
.pnl-box.loss .pnl-value { color: #e74c3c; }

.pnl-box .pnl-pct {
  font-size: 12px;
}

.pnl-box.profit .pnl-pct { color: #00b386; }
.pnl-box.loss .pnl-pct { color: #e74c3c; }

.auto-refresh-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6c757d;
  cursor: pointer;
}

.auto-refresh-toggle input {
  width: 14px;
  height: 14px;
}

.refresh-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  min-width: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.refresh-btn:hover { background: #1976d2; }
.refresh-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.exit-all-btn {
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 500;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.exit-all-btn:hover { background: #c0392b; }
.exit-all-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Spinner */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner.large {
  width: 32px;
  height: 32px;
  border-width: 3px;
  border-color: rgba(33,150,243,0.3);
  border-top-color: #2196f3;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Summary Bar */
.summary-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 10px 16px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 12px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.summary-item .label {
  font-size: 11px;
  color: #6c757d;
  text-transform: uppercase;
}

.summary-item .value {
  font-size: 14px;
  font-weight: 600;
  color: #212529;
}

.text-green { color: #00b386 !important; }
.text-red { color: #e74c3c !important; }

/* Positions Table */
.positions-table-container {
  flex: 1;
  overflow: auto;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

.positions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.positions-table th {
  padding: 10px 12px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #6c757d;
  background: #fafafa;
  border-bottom: 2px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.positions-table td {
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.position-row:hover {
  background: #f8f9fa;
}

.instrument-col {
  min-width: 200px;
}

.instrument-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.instrument-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.instrument-name {
  font-size: 13px;
  font-weight: 600;
  color: #2196f3;
}

.instrument-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.underlying {
  font-size: 10px;
  color: #6c757d;
}

.option-badge {
  font-size: 9px;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 2px;
}

.option-badge.ce {
  background: #ffcdd2;
  color: #c62828;
}

.option-badge.pe {
  background: #c8e6c9;
  color: #2e7d32;
}

.strike {
  font-size: 10px;
  color: #6c757d;
}

.product-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: #f0f0f0;
  border-radius: 2px;
  color: #6c757d;
}

.qty {
  font-weight: 600;
}

.qty.long { color: #00b386; }
.qty.short { color: #e74c3c; }

.change-pct {
  font-size: 10px;
  opacity: 0.8;
}

.pnl {
  font-weight: 600;
}

.pnl.profit { color: #00b386; }
.pnl.loss { color: #e74c3c; }

.pnl-pct.profit { color: #00b386; }
.pnl-pct.loss { color: #e74c3c; }

.actions-col {
  width: 140px;
}

.action-buttons {
  display: flex;
  gap: 6px;
}

.btn-exit {
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 500;
  background: #ffebee;
  color: #c62828;
  border: 1px solid #ffcdd2;
  border-radius: 3px;
  cursor: pointer;
}

.btn-exit:hover {
  background: #e74c3c;
  color: white;
  border-color: #e74c3c;
}

.btn-add {
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 500;
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid #bbdefb;
  border-radius: 3px;
  cursor: pointer;
}

.btn-add:hover {
  background: #2196f3;
  color: white;
  border-color: #2196f3;
}

/* Total Row */
.total-row {
  background: #fafafa;
}

.total-row td {
  border-top: 2px solid #e0e0e0;
  font-weight: 600;
}

.font-semibold { font-weight: 600; }
.font-bold { font-weight: 700; }
.text-right { text-align: right; }
.text-center { text-align: center; }

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: #9aa3ad;
  margin-bottom: 16px;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #212529;
}

.empty-state p {
  margin: 0 0 20px;
  color: #6c757d;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.loading-state p {
  margin-top: 16px;
  color: #6c757d;
}

.btn-primary {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  background: #2196f3;
  color: white;
  border: none;
  border-radius: 3px;
  text-decoration: none;
  cursor: pointer;
}

.btn-primary:hover { background: #1976d2; }

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 400px;
  max-width: 90%;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}

.modal-sm {
  width: 360px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #6c757d;
  cursor: pointer;
  line-height: 1;
}

.modal-body {
  padding: 20px;
}

.position-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-bottom: 16px;
}

.position-summary .symbol {
  font-weight: 600;
  color: #212529;
}

.position-summary .qty.long { color: #00b386; }
.position-summary .qty.short { color: #e74c3c; }

.position-summary .ltp {
  color: #6c757d;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: #6c757d;
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  outline: none;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #2196f3;
}

.order-type-toggle {
  display: flex;
  gap: 2px;
  background: #f0f0f0;
  padding: 2px;
  border-radius: 4px;
}

.order-type-toggle .toggle-btn {
  flex: 1;
}

.order-type-toggle .toggle-btn.buy.active {
  background: #00b386;
  color: white;
}

.order-type-toggle .toggle-btn.sell.active {
  background: #e74c3c;
  color: white;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid #e0e0e0;
}

.btn-secondary {
  padding: 8px 16px;
  font-size: 13px;
  background: white;
  color: #6c757d;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover { background: #f5f5f5; }

.btn-danger {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-danger:hover { background: #c0392b; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-buy {
  background: #00b386;
  color: white;
  border: none;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
}

.btn-buy:hover { background: #009973; }

.btn-sell {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
}

.btn-sell:hover { background: #c0392b; }

.btn-action:disabled { opacity: 0.6; cursor: not-allowed; }

.warning-text {
  font-size: 13px;
  margin-top: 8px;
}
</style>
