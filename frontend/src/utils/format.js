export function formatDateTime(value) {
  if (!value) {
    return 'Not yet recorded'
  }
  return new Intl.DateTimeFormat('en-AU', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function extractApiMessage(error, fallback = 'Something went wrong.') {
  const data = error?.response?.data
  if (typeof data?.message === 'string') {
    return data.message
  }
  if (typeof data?.detail === 'string') {
    return data.detail
  }
  if (typeof data?.error_code === 'string') {
    return data.error_code
  }
  return fallback
}

export function buildCsvExportUrl(filters = {}) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value)
    }
  })
  const query = params.toString()
  return query ? `/api/admin/audit/export.csv?${query}` : '/api/admin/audit/export.csv'
}