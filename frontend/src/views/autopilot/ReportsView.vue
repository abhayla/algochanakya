<script setup>
/**
 * AutoPilot Reports View
 *
 * Phase 4: Generate P&L reports, tax summaries, and downloadable files.
 */
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAutopilotStore } from '@/stores/autopilot'
import KiteLayout from '@/components/layout/KiteLayout.vue'
import '@/assets/css/strategy-table.css'

const router = useRouter()
const store = useAutopilotStore()

// Reports list
const reports = computed(() => store.reports || [])
const reportsLoading = ref(false)
const reportsPagination = computed(() => store.reportsPagination || {})

// Generate report modal
const showGenerateModal = ref(false)
const generateLoading = ref(false)
const reportForm = ref({
  name: '',
  description: '',
  report_type: 'pnl',
  start_date: '',
  end_date: '',
  format: 'json',
  strategy_id: null
})
const validationError = ref('')

// Report details modal
const showDetailsModal = ref(false)
const selectedReport = ref(null)
const downloadingPdf = ref(false)
const downloadingExcel = ref(false)

// Delete confirmation modal
const showDeleteModal = ref(false)
const reportToDelete = ref(null)
const deleting = ref(false)

// Active tab: 'reports' or 'tax'
const activeTab = ref('reports')

// Filters
const typeFilter = ref('')
const sortDirection = ref('desc')

// Tax summary
const taxSummary = computed(() => store.taxSummary || null)
const taxLoading = ref(false)
const selectedFinancialYear = ref('')

// Report types
const reportTypes = [
  { value: 'pnl', label: 'P&L Report' },
  { value: 'monthly', label: 'Monthly Summary' },
  { value: 'strategy', label: 'Strategy Performance' },
  { value: 'tax', label: 'Tax Report' }
]

// Export formats
const exportFormats = [
  { value: 'json', label: 'JSON (View Online)' },
  { value: 'csv', label: 'CSV (Download)' },
  { value: 'excel', label: 'Excel (Download)' }
]

// Filtered and sorted reports
const filteredReports = computed(() => {
  let result = [...(store.reports || [])]

  // Filter by type
  if (typeFilter.value) {
    result = result.filter(r => r.report_type === typeFilter.value)
  }

  // Sort by generated_at
  result.sort((a, b) => {
    const dateA = new Date(a.generated_at || 0)
    const dateB = new Date(b.generated_at || 0)
    return sortDirection.value === 'asc' ? dateA - dateB : dateB - dateA
  })

  return result
})

// Financial years
const financialYears = computed(() => {
  const years = []
  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth()

  // Current FY starts in April
  const currentFY = currentMonth >= 3 ? currentYear : currentYear - 1

  for (let i = 0; i < 5; i++) {
    const fy = currentFY - i
    years.push({
      value: `${fy}-${(fy + 1).toString().slice(-2)}`,
      label: `FY ${fy}-${(fy + 1).toString().slice(-2)}`
    })
  }
  return years
})

// Initialize
onMounted(async () => {
  reportsLoading.value = true
  try {
    await store.fetchReports()

    // Set default dates for report form
    const today = new Date()
    const thirtyDaysAgo = new Date(today)
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
    reportForm.value.end_date = today.toISOString().split('T')[0]
    reportForm.value.start_date = thirtyDaysAgo.toISOString().split('T')[0]

    // Set default financial year
    selectedFinancialYear.value = financialYears.value[0]?.value || ''
  } finally {
    reportsLoading.value = false
  }
})

const handleGenerateReport = async () => {
  // Validate date range
  validationError.value = ''
  if (reportForm.value.start_date && reportForm.value.end_date) {
    if (new Date(reportForm.value.start_date) > new Date(reportForm.value.end_date)) {
      validationError.value = 'Start date must be before end date'
      return
    }
  }

  generateLoading.value = true
  try {
    await store.generateReport({
      name: reportForm.value.name || `${reportForm.value.report_type.toUpperCase()} Report`,
      description: reportForm.value.description,
      report_type: reportForm.value.report_type,
      start_date: reportForm.value.start_date,
      end_date: reportForm.value.end_date,
      format: reportForm.value.format,
      strategy_id: reportForm.value.strategy_id
    })
    showGenerateModal.value = false
    resetForm()
    await store.fetchReports()
  } finally {
    generateLoading.value = false
  }
}

// Open report details
const openReportDetails = (report) => {
  selectedReport.value = report
  showDetailsModal.value = true
}

const closeReportDetails = () => {
  selectedReport.value = null
  showDetailsModal.value = false
}

// Download as PDF
const handleDownloadPdf = async () => {
  if (!selectedReport.value) return
  downloadingPdf.value = true
  try {
    await store.downloadReport(selectedReport.value.id, 'pdf')
  } finally {
    downloadingPdf.value = false
  }
}

// Download as Excel
const handleDownloadExcel = async () => {
  if (!selectedReport.value) return
  downloadingExcel.value = true
  try {
    await store.downloadReport(selectedReport.value.id, 'excel')
  } finally {
    downloadingExcel.value = false
  }
}

// Delete confirmation
const confirmDelete = (report) => {
  reportToDelete.value = report
  showDeleteModal.value = true
}

const cancelDelete = () => {
  reportToDelete.value = null
  showDeleteModal.value = false
}

const executeDelete = async () => {
  if (!reportToDelete.value) return
  deleting.value = true
  try {
    await store.deleteReport(reportToDelete.value.id)
    await store.fetchReports()
    showDeleteModal.value = false
    reportToDelete.value = null
  } finally {
    deleting.value = false
  }
}

// Toggle sort direction
const toggleSort = () => {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
}

// Filter by type
const handleFilterByType = (type) => {
  typeFilter.value = type
}

const handleFetchTaxSummary = async () => {
  if (!selectedFinancialYear.value) return
  taxLoading.value = true
  try {
    await store.fetchTaxSummary(selectedFinancialYear.value)
  } finally {
    taxLoading.value = false
  }
}

const handleDownload = async (report) => {
  if (report.file_path) {
    await store.downloadReport(report.id)
  }
}

const handleDelete = (report) => {
  confirmDelete(report)
}

const resetForm = () => {
  const today = new Date()
  const thirtyDaysAgo = new Date(today)
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

  reportForm.value = {
    name: '',
    description: '',
    report_type: 'pnl',
    start_date: thirtyDaysAgo.toISOString().split('T')[0],
    end_date: today.toISOString().split('T')[0],
    format: 'json',
    strategy_id: null
  }
}

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '₹0'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(value)
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  })
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const getPnLClass = (value) => {
  if (value > 0) return 'pnl-profit'
  if (value < 0) return 'pnl-loss'
  return 'pnl-neutral'
}

const getReportTypeBadgeClass = (type) => {
  const classes = {
    pnl: 'type-badge type-pnl',
    monthly: 'type-badge type-monthly',
    strategy: 'type-badge type-strategy',
    tax: 'type-badge type-tax'
  }
  return classes[type] || 'type-badge'
}

const navigateToDashboard = () => {
  router.push('/autopilot')
}

const navigateToAnalytics = () => {
  router.push('/autopilot/analytics')
}
</script>

<template>
  <KiteLayout>
    <div class="reports-view" data-testid="autopilot-reports-page">
      <!-- Header -->
      <div class="reports-header" data-testid="autopilot-reports-header">
        <div>
          <div class="header-breadcrumb">
            <button @click="navigateToDashboard" class="breadcrumb-link">AutoPilot</button>
            <span class="breadcrumb-separator">/</span>
            <span class="breadcrumb-current">Reports</span>
          </div>
          <h1 class="reports-title">Reports</h1>
          <p class="reports-subtitle">Generate and download P&L reports and tax summaries</p>
        </div>
        <div class="reports-actions">
          <button
            @click="navigateToAnalytics"
            class="strategy-btn strategy-btn-outline"
            data-testid="autopilot-reports-analytics-btn"
          >
            Analytics
          </button>
          <button
            @click="showGenerateModal = true"
            class="strategy-btn strategy-btn-primary"
            data-testid="autopilot-reports-generate-btn"
          >
            + Generate Report
          </button>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="tabs-nav">
        <button
          :class="['tab-btn', activeTab === 'reports' ? 'tab-active' : '']"
          @click="activeTab = 'reports'"
          data-testid="autopilot-reports-reports-tab"
        >
          Reports
        </button>
        <button
          :class="['tab-btn', activeTab === 'tax' ? 'tab-active' : '']"
          @click="activeTab = 'tax'"
          data-testid="autopilot-reports-tax-tab"
        >
          Tax Summary
        </button>
      </div>

      <!-- Tax Summary Section -->
      <div v-if="activeTab === 'tax'" class="tax-summary-card" data-testid="autopilot-reports-tax-summary">
        <div class="card-header">
          <h2 class="section-title">Tax Summary</h2>
          <div class="tax-controls">
            <select
              v-model="selectedFinancialYear"
              class="filter-select"
              data-testid="autopilot-reports-fy-select"
            >
              <option v-for="fy in financialYears" :key="fy.value" :value="fy.value">
                {{ fy.label }}
              </option>
            </select>
            <button
              @click="handleFetchTaxSummary"
              :disabled="taxLoading || !selectedFinancialYear"
              class="strategy-btn strategy-btn-outline"
              data-testid="autopilot-reports-generate-tax"
            >
              {{ taxLoading ? 'Loading...' : 'Get Summary' }}
            </button>
          </div>
        </div>

        <div v-if="taxSummary" class="tax-summary-content" data-testid="autopilot-reports-tax-data">
          <div class="tax-grid">
            <div class="tax-stat">
              <span class="tax-label">Financial Year</span>
              <span class="tax-value">{{ taxSummary.financial_year }}</span>
            </div>
            <div class="tax-stat">
              <span class="tax-label">Total Turnover</span>
              <span class="tax-value">{{ formatCurrency(taxSummary.total_turnover) }}</span>
            </div>
            <div class="tax-stat">
              <span class="tax-label">Speculative P&L</span>
              <span class="tax-value" :class="getPnLClass(taxSummary.speculative_pnl)">
                {{ formatCurrency(taxSummary.speculative_pnl) }}
              </span>
            </div>
            <div class="tax-stat">
              <span class="tax-label">Non-Speculative P&L</span>
              <span class="tax-value" :class="getPnLClass(taxSummary.non_speculative_pnl)">
                {{ formatCurrency(taxSummary.non_speculative_pnl) }}
              </span>
            </div>
            <div class="tax-stat">
              <span class="tax-label">Total Brokerage</span>
              <span class="tax-value">{{ formatCurrency(taxSummary.total_brokerage) }}</span>
            </div>
            <div class="tax-stat">
              <span class="tax-label">Taxes Paid (STT, GST)</span>
              <span class="tax-value">{{ formatCurrency(taxSummary.total_taxes_paid) }}</span>
            </div>
            <div class="tax-stat highlight">
              <span class="tax-label">Net Taxable Income</span>
              <span class="tax-value" :class="getPnLClass(taxSummary.net_taxable_income)">
                {{ formatCurrency(taxSummary.net_taxable_income) }}
              </span>
            </div>
            <div class="tax-stat">
              <span class="tax-label">Trade Count</span>
              <span class="tax-value">{{ taxSummary.trade_count }}</span>
            </div>
          </div>

          <div v-if="taxSummary.audit_required" class="audit-warning" data-testid="autopilot-reports-audit-warning">
            <svg class="warning-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>
            <span>Tax Audit Required: Turnover exceeds Rs. 6 Crore threshold</span>
          </div>
        </div>

        <div v-else class="tax-empty">
          <p>Select a financial year and click "Get Summary" to view tax details</p>
        </div>
      </div>

      <!-- Reports List -->
      <div v-if="activeTab === 'reports'" class="reports-list-card" data-testid="autopilot-reports-list">
        <div class="card-header">
          <h2 class="section-title">Generated Reports</h2>
          <div class="header-controls">
            <select
              v-model="typeFilter"
              class="filter-select filter-sm"
              data-testid="autopilot-reports-type-filter"
            >
              <option value="">All Types</option>
              <option v-for="type in reportTypes" :key="type.value" :value="type.value">
                {{ type.label }}
              </option>
            </select>
            <button
              @click="toggleSort"
              class="sort-btn"
              data-testid="autopilot-reports-sort-date"
            >
              Date {{ sortDirection === 'asc' ? '↑' : '↓' }}
            </button>
            <span class="reports-count">{{ filteredReports.length }} reports</span>
          </div>
        </div>

        <div v-if="reportsLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <p class="loading-text">Loading reports...</p>
        </div>

        <div v-else-if="reports.length === 0" class="empty-state" data-testid="autopilot-reports-empty">
          <svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <p class="empty-text">No reports generated yet</p>
          <button
            @click="showGenerateModal = true"
            class="strategy-btn strategy-btn-primary"
          >
            Generate Your First Report
          </button>
        </div>

        <div v-else class="reports-table-wrapper">
          <table class="reports-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Date Range</th>
                <th>Format</th>
                <th>Size</th>
                <th>Generated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="report in filteredReports"
                :key="report.id"
                :data-testid="`autopilot-report-row-${report.id}`"
                class="report-row clickable"
                @click="openReportDetails(report)"
              >
                <td>
                  <div class="report-name">{{ report.name }}</div>
                  <div v-if="report.description" class="report-desc">{{ report.description }}</div>
                </td>
                <td>
                  <span :class="getReportTypeBadgeClass(report.report_type)">
                    {{ report.report_type }}
                  </span>
                </td>
                <td>
                  <span class="report-dates">
                    {{ formatDate(report.start_date) }} - {{ formatDate(report.end_date) }}
                  </span>
                </td>
                <td>
                  <span class="report-format">{{ report.format?.toUpperCase() }}</span>
                </td>
                <td>
                  <span class="report-size">{{ formatFileSize(report.file_size_bytes) }}</span>
                </td>
                <td>
                  <span class="report-generated">{{ formatDate(report.generated_at) }}</span>
                </td>
                <td>
                  <div class="report-actions">
                    <button
                      v-if="report.file_path"
                      @click="handleDownload(report)"
                      class="action-btn action-download"
                      :data-testid="`autopilot-report-download-${report.id}`"
                    >
                      Download
                    </button>
                    <button
                      @click="handleDelete(report)"
                      class="action-btn action-delete"
                      :data-testid="`autopilot-report-delete-${report.id}`"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Generate Report Modal -->
      <div
        v-if="showGenerateModal"
        class="modal-overlay"
        @click.self="showGenerateModal = false"
        data-testid="autopilot-reports-generate-modal"
      >
        <div class="modal-content modal-md">
          <div class="modal-header">
            <h3 class="modal-title">Generate Report</h3>
            <button @click="showGenerateModal = false" class="modal-close">
              <svg class="close-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="form-group">
              <label class="form-label">Report Name (Optional)</label>
              <input
                v-model="reportForm.name"
                type="text"
                class="form-input"
                placeholder="e.g., Monthly P&L Report"
                data-testid="autopilot-reports-name-input"
              />
            </div>

            <div class="form-group">
              <label class="form-label">Description (Optional)</label>
              <textarea
                v-model="reportForm.description"
                class="form-textarea"
                placeholder="Add notes about this report..."
                rows="2"
                data-testid="autopilot-reports-desc-input"
              ></textarea>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Report Type</label>
                <select
                  v-model="reportForm.report_type"
                  class="form-select"
                  data-testid="autopilot-reports-type-select"
                >
                  <option v-for="type in reportTypes" :key="type.value" :value="type.value">
                    {{ type.label }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label class="form-label">Export Format</label>
                <select
                  v-model="reportForm.format"
                  class="form-select"
                  data-testid="autopilot-reports-format-select"
                >
                  <option v-for="fmt in exportFormats" :key="fmt.value" :value="fmt.value">
                    {{ fmt.label }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Start Date</label>
                <input
                  v-model="reportForm.start_date"
                  type="date"
                  class="form-input"
                  data-testid="autopilot-reports-start-date"
                />
              </div>

              <div class="form-group">
                <label class="form-label">End Date</label>
                <input
                  v-model="reportForm.end_date"
                  type="date"
                  class="form-input"
                  data-testid="autopilot-reports-end-date"
                />
              </div>
            </div>

            <!-- Validation Error -->
            <div v-if="validationError" class="validation-error" data-testid="autopilot-reports-validation-error">
              {{ validationError }}
            </div>
          </div>

          <div class="modal-footer">
            <button
              @click="showGenerateModal = false"
              class="strategy-btn strategy-btn-outline"
              data-testid="autopilot-reports-cancel-btn"
            >
              Cancel
            </button>
            <button
              @click="handleGenerateReport"
              :disabled="generateLoading || !reportForm.start_date || !reportForm.end_date"
              class="strategy-btn strategy-btn-primary"
              data-testid="autopilot-reports-submit-btn"
            >
              {{ generateLoading ? 'Generating...' : 'Generate Report' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Report Details Modal -->
      <div
        v-if="showDetailsModal && selectedReport"
        class="modal-overlay"
        @click.self="closeReportDetails"
        data-testid="autopilot-report-details-page"
      >
        <div class="modal-content modal-lg">
          <div class="modal-header">
            <h3 class="modal-title">{{ selectedReport.name }}</h3>
            <button @click="closeReportDetails" class="modal-close">
              <svg class="close-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Report Summary Section -->
            <div class="report-summary" data-testid="autopilot-report-summary-section">
              <div class="summary-grid">
                <div class="summary-item">
                  <span class="summary-label">Report Type</span>
                  <span :class="getReportTypeBadgeClass(selectedReport.report_type)">
                    {{ selectedReport.report_type }}
                  </span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">Date Range</span>
                  <span class="summary-value">
                    {{ formatDate(selectedReport.start_date) }} - {{ formatDate(selectedReport.end_date) }}
                  </span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">Format</span>
                  <span class="summary-value">{{ selectedReport.format?.toUpperCase() }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">Generated</span>
                  <span class="summary-value">{{ formatDate(selectedReport.generated_at) }}</span>
                </div>
                <div class="summary-item">
                  <span class="summary-label">File Size</span>
                  <span class="summary-value">{{ formatFileSize(selectedReport.file_size_bytes) }}</span>
                </div>
              </div>

              <div v-if="selectedReport.description" class="report-description">
                <span class="summary-label">Description</span>
                <p>{{ selectedReport.description }}</p>
              </div>
            </div>

            <!-- Download Buttons -->
            <div class="download-section">
              <h4 class="download-title">Download Report</h4>
              <div class="download-buttons">
                <button
                  @click="handleDownloadPdf"
                  :disabled="downloadingPdf"
                  class="download-btn download-pdf"
                  data-testid="autopilot-report-download-pdf"
                >
                  <svg class="download-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                  </svg>
                  {{ downloadingPdf ? 'Downloading...' : 'Download PDF' }}
                </button>
                <button
                  @click="handleDownloadExcel"
                  :disabled="downloadingExcel"
                  class="download-btn download-excel"
                  data-testid="autopilot-report-download-excel"
                >
                  <svg class="download-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                  </svg>
                  {{ downloadingExcel ? 'Downloading...' : 'Download Excel' }}
                </button>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button @click="closeReportDetails" class="strategy-btn strategy-btn-outline">
              Close
            </button>
          </div>
        </div>
      </div>

      <!-- Delete Confirmation Modal -->
      <div
        v-if="showDeleteModal && reportToDelete"
        class="modal-overlay"
        @click.self="cancelDelete"
      >
        <div class="modal-content modal-sm">
          <div class="modal-header">
            <h3 class="modal-title">Delete Report</h3>
          </div>

          <div class="modal-body">
            <p class="delete-text">
              Are you sure you want to delete the report "<strong>{{ reportToDelete.name }}</strong>"?
              This action cannot be undone.
            </p>
          </div>

          <div class="modal-footer">
            <button @click="cancelDelete" class="strategy-btn strategy-btn-outline">
              Cancel
            </button>
            <button
              @click="executeDelete"
              :disabled="deleting"
              class="strategy-btn strategy-btn-danger"
              data-testid="autopilot-report-delete-confirm"
            >
              {{ deleting ? 'Deleting...' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="store.error" class="error-banner" data-testid="autopilot-reports-error">
        <p class="error-text">{{ store.error }}</p>
        <button @click="store.clearError" class="error-dismiss">Dismiss</button>
      </div>
    </div>
  </KiteLayout>
</template>

<style scoped>
/* ===== Page Container ===== */
.reports-view {
  padding: 24px;
}

/* ===== Header ===== */
.reports-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.breadcrumb-link {
  font-size: 0.875rem;
  color: var(--kite-blue);
  background: none;
  border: none;
  cursor: pointer;
}

.breadcrumb-link:hover {
  text-decoration: underline;
}

.breadcrumb-separator {
  color: var(--kite-text-muted);
}

.breadcrumb-current {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.reports-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--kite-text-primary);
}

.reports-subtitle {
  color: var(--kite-text-secondary);
  margin-top: 4px;
}

.reports-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ===== Cards ===== */
.tax-summary-card,
.reports-list-card {
  background: white;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.card-header {
  padding: 16px;
  border-bottom: 1px solid var(--kite-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

/* ===== Tax Summary ===== */
.tax-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.tax-summary-content {
  padding: 16px;
}

.tax-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 768px) {
  .tax-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.tax-stat {
  padding: 12px;
  background: var(--kite-table-header);
  border-radius: 4px;
}

.tax-stat.highlight {
  background: var(--kite-blue-light, #e3f2fd);
}

.tax-label {
  display: block;
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-bottom: 4px;
}

.tax-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--kite-text-primary);
}

.audit-warning {
  margin-top: 16px;
  padding: 12px;
  background: var(--kite-orange-light, #fff3e0);
  border: 1px solid var(--kite-orange);
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--kite-orange);
  font-weight: 500;
}

.warning-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.tax-empty {
  padding: 32px;
  text-align: center;
  color: var(--kite-text-secondary);
}

/* ===== Reports List ===== */
.reports-count {
  font-size: 0.875rem;
  color: var(--kite-text-secondary);
}

.reports-table-wrapper {
  overflow-x: auto;
}

.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  padding: 12px 16px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: var(--kite-text-secondary);
  background: var(--kite-table-header);
  text-align: left;
}

.reports-table td {
  padding: 12px 16px;
  font-size: 0.875rem;
  color: var(--kite-text-primary);
  border-bottom: 1px solid var(--kite-border-light);
}

.report-name {
  font-weight: 500;
}

.report-desc {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
  margin-top: 2px;
}

.report-dates,
.report-format,
.report-size,
.report-generated {
  color: var(--kite-text-secondary);
}

.report-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 4px 12px;
  font-size: 0.75rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.action-download {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.action-download:hover {
  background: #bbdefb;
}

.action-delete {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
}

.action-delete:hover {
  background: #ffcdd2;
}

/* ===== Type Badge ===== */
.type-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.75rem;
  border-radius: 4px;
  text-transform: uppercase;
}

.type-pnl {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
}

.type-monthly {
  background: var(--kite-blue-light, #e3f2fd);
  color: var(--kite-blue);
}

.type-strategy {
  background: #f3e5f5;
  color: #7b1fa2;
}

.type-tax {
  background: var(--kite-orange-light, #fff3e0);
  color: var(--kite-orange);
}

/* ===== Modal ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
  width: calc(100% - 32px);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content.modal-md {
  max-width: 500px;
}

.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--kite-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
}

.modal-close {
  padding: 4px;
  background: transparent;
  border: none;
  color: var(--kite-text-secondary);
  cursor: pointer;
}

.modal-close:hover {
  color: var(--kite-text-primary);
}

.close-icon {
  width: 20px;
  height: 20px;
}

.modal-body {
  padding: 24px;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--kite-border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ===== Form Styles ===== */
.form-group {
  margin-bottom: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
  margin-bottom: 4px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
}

.form-textarea {
  resize: vertical;
}

.filter-select {
  padding: 8px 12px;
  font-size: 0.875rem;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  color: var(--kite-text-primary);
  background: white;
}

/* ===== P&L Colors ===== */
.pnl-profit {
  color: var(--kite-green) !important;
}

.pnl-loss {
  color: var(--kite-red) !important;
}

.pnl-neutral {
  color: var(--kite-text-secondary) !important;
}

/* ===== Loading & Empty States ===== */
.loading-state {
  text-align: center;
  padding: 48px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 2px solid var(--kite-border);
  border-top-color: var(--kite-blue);
  border-radius: 50%;
  margin: 0 auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: var(--kite-text-secondary);
}

.empty-state {
  padding: 48px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: var(--kite-text-muted);
  margin: 0 auto 16px;
}

.empty-text {
  color: var(--kite-text-secondary);
  margin-bottom: 16px;
}

/* ===== Error Banner ===== */
.error-banner {
  margin-top: 16px;
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red-border, #ffcdd2);
  border-radius: 4px;
  padding: 16px;
}

.error-text {
  color: var(--kite-red);
}

.error-dismiss {
  color: var(--kite-red);
  background: none;
  border: none;
  text-decoration: underline;
  margin-top: 8px;
  cursor: pointer;
}

/* ===== Button Styles ===== */
.strategy-btn {
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.strategy-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.strategy-btn-primary {
  background: var(--kite-blue);
  color: white;
  border-color: var(--kite-blue);
}

.strategy-btn-primary:hover:not(:disabled) {
  background: var(--kite-blue-dark, #1565c0);
}

.strategy-btn-outline {
  background: white;
  color: var(--kite-text-primary);
  border-color: var(--kite-border);
}

.strategy-btn-outline:hover:not(:disabled) {
  background: var(--kite-table-hover);
}

.strategy-btn-danger {
  background: var(--kite-red);
  color: white;
  border-color: var(--kite-red);
}

.strategy-btn-danger:hover:not(:disabled) {
  background: #c62828;
}

/* ===== Tab Navigation ===== */
.tabs-nav {
  display: flex;
  gap: 0;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--kite-border);
}

.tab-btn {
  padding: 12px 24px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tab-btn:hover {
  color: var(--kite-text-primary);
}

.tab-btn.tab-active {
  color: var(--kite-blue);
  border-bottom-color: var(--kite-blue);
}

/* ===== Header Controls ===== */
.header-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-sm {
  padding: 6px 10px;
  font-size: 0.8125rem;
}

.sort-btn {
  padding: 6px 12px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--kite-text-secondary);
  background: white;
  border: 1px solid var(--kite-border);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.sort-btn:hover {
  background: var(--kite-table-hover);
  color: var(--kite-text-primary);
}

/* ===== Clickable Row ===== */
.report-row.clickable {
  cursor: pointer;
  transition: background 0.15s ease;
}

.report-row.clickable:hover {
  background: var(--kite-table-hover);
}

/* ===== Validation Error ===== */
.validation-error {
  margin-top: 12px;
  padding: 10px 14px;
  font-size: 0.875rem;
  color: var(--kite-red);
  background: var(--kite-red-light, #ffebee);
  border: 1px solid var(--kite-red-border, #ffcdd2);
  border-radius: 4px;
}

/* ===== Report Summary in Modal ===== */
.report-summary {
  margin-bottom: 24px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (min-width: 640px) {
  .summary-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-label {
  font-size: 0.75rem;
  color: var(--kite-text-secondary);
}

.summary-value {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--kite-text-primary);
}

.report-description {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--kite-border-light);
}

.report-description p {
  margin-top: 4px;
  font-size: 0.875rem;
  color: var(--kite-text-primary);
}

/* ===== Download Section ===== */
.download-section {
  padding-top: 16px;
  border-top: 1px solid var(--kite-border-light);
}

.download-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--kite-text-primary);
  margin-bottom: 12px;
}

.download-buttons {
  display: flex;
  gap: 12px;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 4px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.download-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.download-pdf {
  background: var(--kite-red-light, #ffebee);
  color: var(--kite-red);
  border-color: var(--kite-red-border, #ffcdd2);
}

.download-pdf:hover:not(:disabled) {
  background: #ffcdd2;
}

.download-excel {
  background: var(--kite-green-light, #e8f5e9);
  color: var(--kite-green);
  border-color: var(--kite-green-border, #c8e6c9);
}

.download-excel:hover:not(:disabled) {
  background: #c8e6c9;
}

.download-icon {
  width: 18px;
  height: 18px;
}

/* ===== Delete Modal ===== */
.modal-sm {
  max-width: 400px;
}

.modal-lg {
  max-width: 600px;
}

.delete-text {
  font-size: 0.9375rem;
  color: var(--kite-text-primary);
  line-height: 1.5;
}

.delete-text strong {
  font-weight: 600;
}
</style>
