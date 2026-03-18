<script setup>
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { usePositionsStore } from '../stores/positions'
import { useWatchlistStore } from '../stores/watchlist'
import KiteLayout from '../components/layout/KiteLayout.vue'
import BrokerUpgradeBanner from '../components/common/BrokerUpgradeBanner.vue'
import DataSourceBadge from '../components/common/DataSourceBadge.vue'

const router = useRouter()
const authStore = useAuthStore()
const positionsStore = usePositionsStore()
const watchlistStore = useWatchlistStore()

const totalPnl = computed(() => positionsStore.summary?.total_pnl ?? 0)
const totalPnlPct = computed(() => positionsStore.summary?.total_pnl_pct ?? 0)
const activePositions = computed(() => positionsStore.summary?.total_positions ?? 0)
const indexTicks = computed(() => watchlistStore.indexTicks)

const greeting = computed(() => {
  const hour = new Date().getHours()
  const name = authStore.user?.first_name
  const timeGreeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  return name ? `${timeGreeting}, ${name}` : timeGreeting
})

onMounted(async () => {
  try { await positionsStore.fetchPositions() } catch { /* silently fail */ }
})
</script>

<template>
  <KiteLayout>
    <!-- Main Content -->
    <div class="dashboard-container" data-testid="dashboard-page">
      <div class="dashboard-content">
        <BrokerUpgradeBanner screen="dashboard" />
        <div class="dashboard-header">
          <div class="dashboard-header-text">
            <h1 class="dashboard-title" data-testid="dashboard-title">{{ greeting }}</h1>
            <p class="dashboard-subtitle">
              Here's your trading overview for today.
            </p>
          </div>
          <DataSourceBadge screen="dashboard" />
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions" data-testid="dashboard-quick-actions">
          <router-link to="/strategy" class="quick-action-btn" data-testid="dashboard-quick-new-strategy">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            New Strategy
          </router-link>
          <router-link to="/positions" class="quick-action-btn" data-testid="dashboard-quick-positions">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            View Positions
          </router-link>
          <router-link to="/optionchain" class="quick-action-btn" data-testid="dashboard-quick-optionchain">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 3v18h18"/>
              <path d="M18 17V9"/>
              <path d="M13 17V5"/>
              <path d="M8 17v-3"/>
            </svg>
            Option Chain
          </router-link>
        </div>

        <!-- Portfolio Summary -->
        <div class="portfolio-summary" data-testid="dashboard-portfolio-summary">
          <div class="summary-card" data-testid="dashboard-pnl-card">
            <div class="summary-label">Today's P&L</div>
            <div :class="['summary-value', totalPnl >= 0 ? 'positive' : 'negative']">
              {{ totalPnl >= 0 ? '+' : '' }}{{ totalPnl.toLocaleString('en-IN', { minimumFractionDigits: 2 }) }}
            </div>
            <div :class="['summary-pct', totalPnlPct >= 0 ? 'positive' : 'negative']">
              ({{ totalPnlPct >= 0 ? '+' : '' }}{{ totalPnlPct.toFixed(2) }}%)
            </div>
          </div>
          <div class="summary-card" data-testid="dashboard-positions-count-card">
            <div class="summary-label">Active Positions</div>
            <div class="summary-value">{{ activePositions }}</div>
            <router-link to="/positions" class="summary-link">View all →</router-link>
          </div>
          <div class="summary-card" data-testid="dashboard-nifty-card">
            <div class="summary-label">NIFTY 50</div>
            <div class="summary-value">{{ indexTicks.nifty50?.ltp?.toLocaleString('en-IN') || '--' }}</div>
            <div :class="['summary-pct', (indexTicks.nifty50?.change || 0) >= 0 ? 'positive' : 'negative']">
              {{ (indexTicks.nifty50?.change || 0) >= 0 ? '+' : '' }}{{ (indexTicks.nifty50?.change || 0).toFixed(2) }}
              ({{ (indexTicks.nifty50?.change_percent || 0) >= 0 ? '+' : '' }}{{ (indexTicks.nifty50?.change_percent || 0).toFixed(2) }}%)
            </div>
          </div>
          <div class="summary-card" data-testid="dashboard-banknifty-card">
            <div class="summary-label">BANK NIFTY</div>
            <div class="summary-value">{{ indexTicks.niftyBank?.ltp?.toLocaleString('en-IN') || '--' }}</div>
            <div :class="['summary-pct', (indexTicks.niftyBank?.change || 0) >= 0 ? 'positive' : 'negative']">
              {{ (indexTicks.niftyBank?.change || 0) >= 0 ? '+' : '' }}{{ (indexTicks.niftyBank?.change || 0).toFixed(2) }}
              ({{ (indexTicks.niftyBank?.change_percent || 0) >= 0 ? '+' : '' }}{{ (indexTicks.niftyBank?.change_percent || 0).toFixed(2) }}%)
            </div>
          </div>
        </div>

        <!-- Feature Cards -->
        <div class="dashboard-cards" data-testid="dashboard-cards">
          <!-- Option Chain Card -->
          <router-link to="/optionchain" class="dashboard-card card-optionchain" data-testid="dashboard-optionchain-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 3v18h18"/>
                <path d="M18 17V9"/>
                <path d="M13 17V5"/>
                <path d="M8 17v-3"/>
              </svg>
            </div>
            <h3 class="card-title">Option Chain</h3>
            <p class="card-description">Open NIFTY, BANKNIFTY, or FINNIFTY chains — strike-by-strike OI, IV, and live Greeks</p>
          </router-link>

          <!-- OFO Card -->
          <router-link to="/ofo" class="dashboard-card card-ofo" data-testid="dashboard-ofo-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
            </div>
            <h3 class="card-title">OFO</h3>
            <p class="card-description">Scan all strikes and find the best risk-reward combinations — ranked by premium, margin, and probability</p>
          </router-link>

          <!-- Strategy Builder Card -->
          <router-link to="/strategy" class="dashboard-card card-strategy" data-testid="dashboard-strategy-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
              </svg>
            </div>
            <h3 class="card-title">Strategy Builder</h3>
            <p class="card-description">Add legs, see the P&L curve and breakeven points before placing any order</p>
          </router-link>

          <!-- Positions Card -->
          <router-link to="/positions" class="dashboard-card card-positions" data-testid="dashboard-positions-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
              </svg>
            </div>
            <h3 class="card-title">Positions</h3>
            <p class="card-description">See live P&L on all open F&O positions — exit individual legs or everything in one click</p>
          </router-link>

          <!-- Strategy Library Card -->
          <router-link to="/strategies" class="dashboard-card card-library" data-testid="dashboard-strategies-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                <path d="M8 7h8"/>
                <path d="M8 11h6"/>
              </svg>
            </div>
            <h3 class="card-title">Strategy Library</h3>
            <p class="card-description">Pick a ready-made strategy — Iron Condor, Straddle, Butterfly — and deploy it directly</p>
          </router-link>

          <!-- AutoPilot Card -->
          <router-link to="/autopilot" class="dashboard-card card-autopilot" data-testid="dashboard-autopilot-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2"/>
                <circle cx="12" cy="5" r="2"/>
                <path d="M12 7v4"/>
                <circle cx="8" cy="16" r="1"/>
                <circle cx="16" cy="16" r="1"/>
              </svg>
            </div>
            <h3 class="card-title">AutoPilot</h3>
            <p class="card-description">Set entry conditions, adjustments, and stop-loss rules — AutoPilot monitors and acts automatically</p>
          </router-link>
        </div>
      </div>
    </div>
  </KiteLayout>
</template>

<style scoped>
.dashboard-container {
  padding: 24px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: hidden;
  height: calc(100vh - 48px);
  overflow-y: auto;
  background: #f8f9fa;
}

.dashboard-content {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.dashboard-title {
  font-size: 28px;
  font-weight: 700;
  color: #212529;
  margin: 0 0 8px 0;
}

.dashboard-subtitle {
  font-size: 15px;
  color: #6c757d;
  margin: 0;
}

.portfolio-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.summary-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 18px 20px;
}

.summary-label {
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
  margin-bottom: 6px;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}

.summary-value.positive { color: #16a34a; }
.summary-value.negative { color: #dc2626; }

.summary-pct {
  font-size: 13px;
  font-weight: 500;
  margin-top: 2px;
}

.summary-pct.positive { color: #16a34a; }
.summary-pct.negative { color: #dc2626; }

.summary-link {
  font-size: 12px;
  color: #3b82f6;
  text-decoration: none;
  margin-top: 4px;
  display: inline-block;
}

.summary-link:hover { text-decoration: underline; }

.quick-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
}

.quick-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.15s ease;
}

.quick-action-btn svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

.quick-action-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
  color: #111827;
}

.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.dashboard-card {
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.dashboard-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.card-icon svg {
  width: 24px;
  height: 24px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #212529;
  margin: 0 0 8px 0;
}

.card-description {
  font-size: 14px;
  color: #6c757d;
  margin: 0;
  line-height: 1.5;
}

/* Option Chain - Purple theme */
.card-optionchain {
  background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
}
.card-optionchain:hover {
  border-color: #a855f7;
}
.card-optionchain .card-icon {
  background: #a855f7;
  color: white;
}

/* OFO - Indigo theme */
.card-ofo {
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
}
.card-ofo:hover {
  border-color: #6366f1;
}
.card-ofo .card-icon {
  background: #6366f1;
  color: white;
}

/* Strategy Builder - Green theme */
.card-strategy {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
}
.card-strategy:hover {
  border-color: #22c55e;
}
.card-strategy .card-icon {
  background: #22c55e;
  color: white;
}

/* Positions - Orange theme */
.card-positions {
  background: linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%);
}
.card-positions:hover {
  border-color: #f97316;
}
.card-positions .card-icon {
  background: #f97316;
  color: white;
}

/* Strategy Library - Blue theme */
.card-library {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
}
.card-library:hover {
  border-color: #3b82f6;
}
.card-library .card-icon {
  background: #3b82f6;
  color: white;
}

/* AutoPilot - Cyan/Teal theme */
.card-autopilot {
  background: linear-gradient(135deg, #cffafe 0%, #a5f3fc 100%);
}
.card-autopilot:hover {
  border-color: #06b6d4;
}
.card-autopilot .card-icon {
  background: #06b6d4;
  color: white;
}

/* Responsive adjustments */
@media (max-width: 1024px) {
  .dashboard-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
  }

  .dashboard-title {
    font-size: 24px;
  }

  .quick-actions {
    flex-wrap: wrap;
  }

  .dashboard-cards {
    grid-template-columns: 1fr;
  }

  .dashboard-card {
    padding: 20px;
  }
}
</style>
