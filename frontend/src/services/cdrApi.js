/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import axios from 'axios'

import { api } from 'boot/api'

const BASE = 'admin/cdr/'

const SOURCE_ERROR_CODES = new Set([
  'source_error',
  'source_not_configured',
  'source_unavailable',
  'source_configuration_error',
  'encryption_key_missing',
  'encryption_key_invalid',
  'credential_decrypt_failed',
])
const TIMEOUT_CODES = new Set(['source_timeout', 'source_query_cancelled'])

/** Repeat keys for arrays (``key=a&key=b``) and drop empty values. */
export function toSearchParams(params = {}) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      value.forEach((item) => search.append(key, item))
    } else if (value !== null && value !== undefined && value !== '') {
      search.append(key, value)
    }
  }
  return search
}

async function get(path, { params, signal } = {}) {
  const { data } = await api.get(`${BASE}${path}`, {
    params: params ? toSearchParams(params) : undefined,
    signal,
  })
  return data
}

export function searchSdrs(params, options = {}) {
  return get('sdr/', { ...options, params })
}

export function getSdrDetail(id, options = {}) {
  return get(`sdr/${encodeURIComponent(id)}/`, options)
}

export function fetchIngressIpGroups(options = {}) {
  return get('lookups/ingress-ip-groups/', options)
}

export function fetchEgressIpGroups(options = {}) {
  return get('lookups/egress-ip-groups/', options)
}

export function fetchTerminationReasons(options = {}) {
  return get('lookups/termination-reasons/', options)
}

export function fetchStatisticsSummary(params, options = {}) {
  return get('statistics/summary/', { ...options, params })
}

export function fetchStatisticsTimeseries(params, options = {}) {
  return get('statistics/timeseries/', { ...options, params })
}

export function fetchStatisticsIpGroups(params, options = {}) {
  return get('statistics/ip-groups/', { ...options, params })
}

export function fetchStatisticsTerminationReasons(params, options = {}) {
  return get('statistics/termination-reasons/', { ...options, params })
}

export function fetchDisplayConfig(options = {}) {
  return get('config/display/', options)
}

export async function updatePreferences(payload) {
  const { data } = await api.put(`${BASE}preferences/`, payload)
  return data
}

export function fetchModuleSettings(options = {}) {
  return get('settings/', options)
}

export async function updateModuleSettings(payload) {
  const { data } = await api.put(`${BASE}settings/`, payload)
  return data
}

export function isCancelled(error) {
  return axios.isCancel(error) || error?.code === 'ERR_CANCELED' || error?.name === 'AbortError'
}

/**
 * Normalise an API failure into a safe, user-facing description.
 * ``fieldErrors`` holds DRF validation messages keyed by field (possibly nested).
 */
export function describeCdrError(error, fallback = 'The request could not be completed.') {
  const response = error?.response
  const data = response && typeof response.data === 'object' ? response.data : null
  const status = response?.status ?? null
  const code = typeof data?.error_code === 'string' ? data.error_code : null
  const detail = typeof data?.detail === 'string' ? data.detail : null

  const info = {
    status,
    code,
    message: detail || fallback,
    fieldErrors: data?.errors && typeof data.errors === 'object' ? data.errors : null,
    sourceIssue: false,
    timeout: false,
    notFound: false,
  }

  if (!response) {
    info.message = 'Unable to reach the Telephony Toolbox server. Check your connection and retry.'
    return info
  }
  if (status === 401) {
    info.message = 'Your session has expired. Sign in again to continue.'
  } else if (status === 403) {
    info.message = detail || 'App Admin access is required for the AudioCodes CDR module.'
  } else if (status === 404) {
    info.notFound = true
  } else if (TIMEOUT_CODES.has(code) || status === 504) {
    info.timeout = true
    info.message =
      detail ||
      'The query exceeded the time limit. Narrow the date range or use exact or starts-with matching.'
  } else if (SOURCE_ERROR_CODES.has(code) || (code?.startsWith('source_') ?? false)) {
    info.sourceIssue = true
  } else if (status === 400 && !code && data) {
    // Plain DRF validation errors (settings and preferences) are keyed by field.
    info.fieldErrors = data
    info.message = detail || 'Some values are invalid. Review the highlighted fields.'
  } else if (status >= 500 && !detail) {
    info.message = 'The server could not complete the request. Try again shortly.'
  }
  return info
}
