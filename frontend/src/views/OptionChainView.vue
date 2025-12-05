<template>
  <div class="h-screen flex flex-col bg-gray-100 overflow-hidden">

    <!-- Header -->
    <header class="bg-white border-b border-gray-200 shadow-sm px-6 py-4 flex-shrink-0">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-6">
          <!-- Navigation Links -->
          <div class="flex items-center gap-4 mr-4">
            <router-link to="/watchlist" class="text-sm text-gray-600 hover:text-blue-600">Watchlist</router-link>
            <router-link to="/optionchain" class="text-sm text-blue-600 font-semibold">Option Chain</router-link>
            <router-link to="/strategy" class="text-sm text-gray-600 hover:text-blue-600">Strategy Builder</router-link>
          </div>

          <div class="h-6 border-l border-gray-300"></div>

          <!-- Underlying Selector -->
          <div class="flex gap-1 p-1 bg-gray-100 rounded-lg">
            <button
              v-for="ul in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']"
              :key="ul"
              @click="handleUnderlyingChange(ul)"
              :class="[
                'px-4 py-2 text-sm font-semibold rounded-md transition-all',
                store.underlying === ul
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              ]"
            >
              {{ ul }}
            </button>
          </div>

          <!-- Expiry Selector -->
          <div class="flex items-center gap-2">
            <label class="text-sm text-gray-600">Expiry:</label>
            <select
              v-model="store.expiry"
              @change="handleExpiryChange"
              class="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="exp in store.expiries" :key="exp" :value="exp">{{ formatExpiry(exp) }}</option>
            </select>
          </div>
        </div>

        <!-- Spot Price & Controls -->
        <div class="flex items-center gap-6">
          <!-- Spot Price -->
          <div class="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg border border-blue-200">
            <span class="text-sm text-blue-600">Spot:</span>
            <span class="text-xl font-bold text-blue-700">{{ formatNumber(store.spotPrice) }}</span>
          </div>

          <!-- Days to Expiry -->
          <div class="flex items-center gap-2 px-3 py-2 bg-gray-100 rounded-lg">
            <span class="text-sm text-gray-600">DTE:</span>
            <span class="font-semibold text-gray-800">{{ store.daysToExpiry }}</span>
          </div>

          <!-- Toggle Greeks -->
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="store.showGreeks" class="w-4 h-4 rounded text-blue-600 focus:ring-blue-500"/>
            <span class="text-sm text-gray-600">Greeks</span>
          </label>

          <!-- Refresh -->
          <button
            @click="store.fetchOptionChain()"
            :disabled="store.isLoading"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <span v-if="store.isLoading">Loading...</span>
            <span v-else>Refresh</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Summary Bar -->
    <div class="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-8">
          <!-- PCR -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-500">PCR:</span>
            <span :class="[
              'text-lg font-bold',
              store.summary.pcr > 1 ? 'text-green-600' : store.summary.pcr < 0.7 ? 'text-red-600' : 'text-gray-800'
            ]">{{ store.summary.pcr }}</span>
          </div>

          <!-- Max Pain -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-500">Max Pain:</span>
            <span class="text-lg font-bold text-purple-600">{{ formatNumber(store.summary.max_pain) }}</span>
          </div>

          <!-- Total CE OI -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-500">CE OI:</span>
            <span class="text-lg font-semibold text-red-600">{{ formatOI(store.summary.total_ce_oi) }}</span>
          </div>

          <!-- Total PE OI -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-500">PE OI:</span>
            <span class="text-lg font-semibold text-green-600">{{ formatOI(store.summary.total_pe_oi) }}</span>
          </div>
        </div>

        <!-- Strikes Range -->
        <div class="flex items-center gap-2">
          <span class="text-sm text-gray-500">Strikes:</span>
          <select v-model="store.strikesRange" class="px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option :value="10">±10</option>
            <option :value="15">±15</option>
            <option :value="20">±20</option>
            <option :value="30">±30</option>
            <option :value="50">All</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="store.error" class="mx-6 mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg flex items-center justify-between">
      <span>{{ store.error }}</span>
      <button @click="store.error = null" class="text-red-500 hover:text-red-700 text-xl font-bold">&times;</button>
    </div>

    <!-- Loading State -->
    <div v-if="store.isLoading && store.chain.length === 0" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p class="text-gray-500">Loading option chain...</p>
      </div>
    </div>

    <!-- Main Content: Option Chain Table -->
    <div v-else class="flex-1 overflow-auto p-4">
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 sticky top-0 z-10">
            <tr>
              <!-- CE Headers -->
              <th class="px-2 py-3 text-center text-xs font-semibold text-red-600 bg-red-50 w-10">+</th>
              <th class="px-2 py-3 text-right text-xs font-semibold text-gray-600 bg-red-50 w-20">OI</th>
              <th class="px-2 py-3 text-right text-xs font-semibold text-gray-600 bg-red-50 w-16">Vol</th>
              <th class="px-2 py-3 text-right text-xs font-semibold text-gray-600 bg-red-50 w-12">IV</th>
              <th v-if="store.showGreeks" class="px-2 py-3 text-right text-xs font-semibold text-gray-600 bg-red-50 w-14">Delta</th>
              <th class="px-2 py-3 text-right text-xs font-semibold text-gray-600 bg-red-50 w-16">LTP</th>
              <th class="px-2 py-3 text-right text-xs font-semibold text-gray-600 bg-red-50 w-14">Chg%</th>

              <!-- Strike -->
              <th class="px-4 py-3 text-center text-xs font-bold text-gray-800 bg-gray-200 w-20">STRIKE</th>

              <!-- PE Headers -->
              <th class="px-2 py-3 text-left text-xs font-semibold text-gray-600 bg-green-50 w-14">Chg%</th>
              <th class="px-2 py-3 text-left text-xs font-semibold text-gray-600 bg-green-50 w-16">LTP</th>
              <th v-if="store.showGreeks" class="px-2 py-3 text-left text-xs font-semibold text-gray-600 bg-green-50 w-14">Delta</th>
              <th class="px-2 py-3 text-left text-xs font-semibold text-gray-600 bg-green-50 w-12">IV</th>
              <th class="px-2 py-3 text-left text-xs font-semibold text-gray-600 bg-green-50 w-16">Vol</th>
              <th class="px-2 py-3 text-left text-xs font-semibold text-gray-600 bg-green-50 w-20">OI</th>
              <th class="px-2 py-3 text-center text-xs font-semibold text-green-600 bg-green-50 w-10">+</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
              v-for="row in store.filteredChain"
              :key="row.strike"
              :class="[
                'transition-colors hover:bg-gray-50',
                row.is_atm ? 'bg-yellow-50 border-y-2 border-yellow-400' : '',
                !row.is_atm && row.is_itm_ce ? 'bg-red-50/30' : '',
                !row.is_atm && row.is_itm_pe ? 'bg-green-50/30' : ''
              ]"
            >
              <!-- CE Add Button -->
              <td class="px-2 py-2 text-center">
                <button
                  v-if="row.ce"
                  @click="toggleStrike(row.strike, 'CE')"
                  :class="[
                    'w-6 h-6 rounded-full text-xs font-bold transition-colors',
                    store.isStrikeSelected(row.strike, 'CE')
                      ? 'bg-red-500 text-white'
                      : 'bg-red-100 hover:bg-red-200 text-red-600'
                  ]"
                >{{ store.isStrikeSelected(row.strike, 'CE') ? '✓' : '+' }}</button>
              </td>

              <!-- CE OI -->
              <td class="px-2 py-2 text-right">
                <div class="flex items-center justify-end gap-1">
                  <div
                    class="h-2 bg-red-400 rounded-full"
                    :style="{ width: store.getOIBarWidth(row.ce?.oi, 'ce') + 'px' }"
                  ></div>
                  <span class="text-xs font-medium text-gray-700 w-12 text-right">{{ formatOI(row.ce?.oi) }}</span>
                </div>
              </td>

              <!-- CE Volume -->
              <td class="px-2 py-2 text-right text-xs text-gray-600">
                {{ formatOI(row.ce?.volume) }}
              </td>

              <!-- CE IV -->
              <td class="px-2 py-2 text-right text-xs font-medium text-gray-700">
                {{ row.ce?.iv || '-' }}
              </td>

              <!-- CE Delta -->
              <td v-if="store.showGreeks" class="px-2 py-2 text-right text-xs text-gray-600">
                {{ row.ce?.delta?.toFixed(2) || '-' }}
              </td>

              <!-- CE LTP -->
              <td class="px-2 py-2 text-right">
                <span class="font-semibold" :class="row.is_itm_ce ? 'text-red-700' : 'text-gray-900'">
                  {{ formatPrice(row.ce?.ltp) }}
                </span>
              </td>

              <!-- CE Change % -->
              <td class="px-2 py-2 text-right text-xs" :class="getChangeClass(row.ce?.change)">
                {{ formatChange(row.ce?.change_pct) }}
              </td>

              <!-- STRIKE -->
              <td class="px-4 py-2 text-center bg-gray-50">
                <span :class="[
                  'font-bold text-sm',
                  row.is_atm ? 'text-yellow-700 text-base' : 'text-gray-900'
                ]">
                  {{ row.strike }}
                </span>
                <span v-if="row.is_atm" class="ml-1 text-[10px] text-yellow-600 font-medium">ATM</span>
              </td>

              <!-- PE Change % -->
              <td class="px-2 py-2 text-left text-xs" :class="getChangeClass(row.pe?.change)">
                {{ formatChange(row.pe?.change_pct) }}
              </td>

              <!-- PE LTP -->
              <td class="px-2 py-2 text-left">
                <span class="font-semibold" :class="row.is_itm_pe ? 'text-green-700' : 'text-gray-900'">
                  {{ formatPrice(row.pe?.ltp) }}
                </span>
              </td>

              <!-- PE Delta -->
              <td v-if="store.showGreeks" class="px-2 py-2 text-left text-xs text-gray-600">
                {{ row.pe?.delta?.toFixed(2) || '-' }}
              </td>

              <!-- PE IV -->
              <td class="px-2 py-2 text-left text-xs font-medium text-gray-700">
                {{ row.pe?.iv || '-' }}
              </td>

              <!-- PE Volume -->
              <td class="px-2 py-2 text-left text-xs text-gray-600">
                {{ formatOI(row.pe?.volume) }}
              </td>

              <!-- PE OI -->
              <td class="px-2 py-2 text-left">
                <div class="flex items-center gap-1">
                  <span class="text-xs font-medium text-gray-700 w-12">{{ formatOI(row.pe?.oi) }}</span>
                  <div
                    class="h-2 bg-green-400 rounded-full"
                    :style="{ width: store.getOIBarWidth(row.pe?.oi, 'pe') + 'px' }"
                  ></div>
                </div>
              </td>

              <!-- PE Add Button -->
              <td class="px-2 py-2 text-center">
                <button
                  v-if="row.pe"
                  @click="toggleStrike(row.strike, 'PE')"
                  :class="[
                    'w-6 h-6 rounded-full text-xs font-bold transition-colors',
                    store.isStrikeSelected(row.strike, 'PE')
                      ? 'bg-green-500 text-white'
                      : 'bg-green-100 hover:bg-green-200 text-green-600'
                  ]"
                >{{ store.isStrikeSelected(row.strike, 'PE') ? '✓' : '+' }}</button>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Empty State -->
        <div v-if="store.chain.length === 0 && !store.isLoading" class="py-20 text-center text-gray-500">
          <p class="text-lg">No option chain data</p>
          <p class="text-sm mt-2">Select an expiry to view option chain</p>
        </div>
      </div>
    </div>

    <!-- Selected Strikes Bar (if any selected) -->
    <div v-if="store.selectedStrikes.length > 0" class="bg-white border-t border-gray-200 px-6 py-3 flex-shrink-0 shadow-lg">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-sm text-gray-600 font-medium">Selected:</span>
          <span
            v-for="s in store.selectedStrikes"
            :key="s.key"
            class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium"
            :class="s.type === 'CE' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'"
          >
            {{ s.type }} {{ s.strike }} @ {{ s.ltp?.toFixed(2) }}
            <button @click="store.toggleStrikeSelection(s.strike, s.type)" class="ml-1 hover:text-gray-900 font-bold">&times;</button>
          </span>
        </div>
        <div class="flex items-center gap-3">
          <button @click="store.clearSelection()" class="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 transition-colors">
            Clear
          </button>
          <button
            @click="goToStrategy()"
            class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            Add to Strategy Builder
            <span>&rarr;</span>
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useOptionChainStore } from '../stores/optionchain'
import { useStrategyStore } from '../stores/strategy'

const store = useOptionChainStore()
const strategyStore = useStrategyStore()
const router = useRouter()

// Format helpers
const formatNumber = (num) => {
  if (!num) return '-'
  return new Intl.NumberFormat('en-IN').format(Math.round(num))
}

const formatPrice = (price) => {
  if (!price && price !== 0) return '-'
  return price.toFixed(2)
}

const formatOI = (oi) => {
  if (!oi) return '-'
  if (oi >= 10000000) return (oi / 10000000).toFixed(2) + 'Cr'
  if (oi >= 100000) return (oi / 100000).toFixed(2) + 'L'
  if (oi >= 1000) return (oi / 1000).toFixed(1) + 'K'
  return oi.toString()
}

const formatChange = (pct) => {
  if (!pct && pct !== 0) return '-'
  const prefix = pct > 0 ? '+' : ''
  return prefix + pct.toFixed(2) + '%'
}

const formatExpiry = (dateStr) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return dateStr
  }
}

const getChangeClass = (value) => {
  if (!value && value !== 0) return 'text-gray-400'
  if (value > 0) return 'text-green-600'
  if (value < 0) return 'text-red-600'
  return 'text-gray-600'
}

// Actions
const handleUnderlyingChange = async (ul) => {
  await store.setUnderlying(ul)
  if (store.expiry) {
    await store.fetchOptionChain()
  }
}

const handleExpiryChange = async () => {
  if (store.expiry) {
    await store.fetchOptionChain()
  }
}

const toggleStrike = (strike, type) => {
  store.toggleStrikeSelection(strike, type)
}

const goToStrategy = () => {
  const payload = store.getAddToStrategyPayload()

  // Set underlying in strategy store
  strategyStore.setUnderlying(store.underlying)

  // Add each selected strike as a leg
  payload.forEach(leg => {
    strategyStore.addLegFromOptionChain(leg)
  })

  store.clearSelection()
  router.push('/strategy')
}

// Initialize
onMounted(async () => {
  await store.fetchExpiries()
  if (store.expiry) {
    await store.fetchOptionChain()
  }
})
</script>
