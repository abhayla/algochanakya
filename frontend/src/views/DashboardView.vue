<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import KiteLayout from '../components/layout/KiteLayout.vue'
import BrokerUpgradeBanner from '../components/common/BrokerUpgradeBanner.vue'

const router = useRouter()
const authStore = useAuthStore()
</script>

<template>
  <KiteLayout>
    <!-- Main Content -->
    <div class="dashboard-container" data-testid="dashboard-page">
      <div class="dashboard-content">
        <BrokerUpgradeBanner screen="dashboard" />
        <div class="dashboard-header">
          <h1 class="dashboard-title" data-testid="dashboard-title">Welcome to AlgoChanakya</h1>
          <p class="dashboard-subtitle">
            Your options trading platform is ready. Start building your strategies!
          </p>
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
            <p class="card-description">View real-time option chain with Open Interest, Implied Volatility, and Greeks for NIFTY, BANKNIFTY & FINNIFTY</p>
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
            <p class="card-description">Options For Options - Find optimal option combinations based on premium, margin, and risk-reward ratios</p>
          </router-link>

          <!-- Strategy Builder Card -->
          <router-link to="/strategy" class="dashboard-card card-strategy" data-testid="dashboard-strategy-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
              </svg>
            </div>
            <h3 class="card-title">Strategy Builder</h3>
            <p class="card-description">Build multi-leg option strategies with P&L visualization, breakeven analysis, and risk-reward charts</p>
          </router-link>

          <!-- Positions Card -->
          <router-link to="/positions" class="dashboard-card card-positions" data-testid="dashboard-positions-card">
            <div class="card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
              </svg>
            </div>
            <h3 class="card-title">Positions</h3>
            <p class="card-description">Monitor your F&O positions with live P&L tracking, day/net view toggle, and one-click exit options</p>
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
            <p class="card-description">Browse 20+ pre-built strategies like Iron Condor, Straddle, Butterfly with one-click deployment</p>
          </router-link>

          <!-- AutoPilot Card - HIDDEN: Feature not ready for production
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
            <p class="card-description">Automate your trading with condition-based entries, adjustments, and risk management rules</p>
          </router-link>
          -->
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

.dashboard-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
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
@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
  }

  .dashboard-title {
    font-size: 24px;
  }

  .dashboard-cards {
    grid-template-columns: 1fr;
  }

  .dashboard-card {
    padding: 20px;
  }
}
</style>
