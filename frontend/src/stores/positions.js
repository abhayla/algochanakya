import { defineStore } from 'pinia';
import api from '@/services/api';

export const usePositionsStore = defineStore('positions', {
  state: () => ({
    positions: [],
    summary: {
      total_pnl: 0,
      total_pnl_pct: 0,
      realized_pnl: 0,
      unrealized_pnl: 0,
      total_positions: 0,
      total_quantity: 0,
      margin_used: 0,
      margin_available: 0
    },
    positionType: 'day', // 'day' or 'net'
    groupBy: null, // null, 'underlying', 'expiry'
    isLoading: false,
    error: null,

    // For exit modal
    exitModal: {
      show: false,
      position: null,
      orderType: 'MARKET',
      price: null,
      quantity: 0
    },

    // For add modal
    addModal: {
      show: false,
      position: null,
      transactionType: 'BUY',
      orderType: 'LIMIT',
      price: null,
      quantity: 0
    },

    // Auto refresh
    autoRefresh: false,
    refreshInterval: null
  }),

  getters: {
    profitPositions: (state) => state.positions.filter(p => p.pnl > 0),
    lossPositions: (state) => state.positions.filter(p => p.pnl < 0),

    longPositions: (state) => state.positions.filter(p => p.quantity > 0),
    shortPositions: (state) => state.positions.filter(p => p.quantity < 0),

    positionsByUnderlying: (state) => {
      const groups = {};
      state.positions.forEach(p => {
        const key = p.underlying || 'Other';
        if (!groups[key]) {
          groups[key] = { name: key, positions: [], total_pnl: 0 };
        }
        groups[key].positions.push(p);
        groups[key].total_pnl += p.pnl;
      });
      return Object.values(groups);
    }
  },

  actions: {
    async fetchPositions() {
      this.isLoading = true;
      this.error = null;

      try {
        // Use annotated endpoint to get AutoPilot metadata
        const response = await api.get('/api/positions/annotated', {
          params: { position_type: this.positionType }
        });

        this.positions = response.data.positions;
        this.summary = response.data.summary;

      } catch (error) {
        console.error('Error fetching positions:', error);
        this.error = error.response?.data?.detail || 'Failed to load positions';
      } finally {
        this.isLoading = false;
      }
    },

    async exitPosition(position, orderType = 'MARKET', price = null) {
      try {
        const quantity = Math.abs(position.quantity);
        const transactionType = position.quantity > 0 ? 'SELL' : 'BUY';

        const response = await api.post('/api/positions/exit', {
          tradingsymbol: position.tradingsymbol,
          exchange: position.exchange,
          transaction_type: transactionType,
          quantity: quantity,
          product: position.product,
          order_type: orderType,
          price: orderType === 'LIMIT' ? price : null
        });

        if (response.data.success) {
          // Refresh positions after exit
          await this.fetchPositions();
          return { success: true, order_id: response.data.order_id };
        }

      } catch (error) {
        console.error('Error exiting position:', error);
        throw error;
      }
    },

    async addToPosition(position, transactionType, quantity, price) {
      try {
        const response = await api.post('/api/positions/add', {
          tradingsymbol: position.tradingsymbol,
          exchange: position.exchange,
          transaction_type: transactionType,
          quantity: quantity,
          product: position.product,
          order_type: 'LIMIT',
          price: price
        });

        if (response.data.success) {
          await this.fetchPositions();
          return { success: true, order_id: response.data.order_id };
        }

      } catch (error) {
        console.error('Error adding to position:', error);
        throw error;
      }
    },

    async exitAllPositions() {
      try {
        const response = await api.post('/api/positions/exit-all');

        if (response.data.success || response.data.orders_placed?.length > 0) {
          await this.fetchPositions();
        }

        return response.data;

      } catch (error) {
        console.error('Error exiting all positions:', error);
        throw error;
      }
    },

    setPositionType(type) {
      this.positionType = type;
      this.fetchPositions();
    },

    // Exit Modal
    openExitModal(position) {
      this.exitModal = {
        show: true,
        position: position,
        orderType: 'MARKET',
        price: position.ltp,
        quantity: Math.abs(position.quantity)
      };
    },

    closeExitModal() {
      this.exitModal.show = false;
      this.exitModal.position = null;
    },

    // Add Modal
    openAddModal(position) {
      this.addModal = {
        show: true,
        position: position,
        transactionType: position.quantity > 0 ? 'BUY' : 'SELL',
        orderType: 'LIMIT',
        price: position.ltp,
        quantity: Math.abs(position.quantity)
      };
    },

    closeAddModal() {
      this.addModal.show = false;
      this.addModal.position = null;
    },

    // Auto Refresh
    startAutoRefresh(intervalMs = 5000) {
      this.autoRefresh = true;
      this.refreshInterval = setInterval(() => {
        if (this.autoRefresh) {
          this.fetchPositions();
        }
      }, intervalMs);
    },

    stopAutoRefresh() {
      this.autoRefresh = false;
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval);
        this.refreshInterval = null;
      }
    }
  }
});
