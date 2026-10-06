/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { parseInstant, todayRange } from 'src/utils/cdrTime'

export const MATCH_MODE_OPTIONS = [
  { value: 'exact', label: 'Exact' },
  { value: 'startswith', label: 'Starts with' },
  { value: 'endswith', label: 'Ends with' },
  { value: 'contains', label: 'Contains' },
]
export const MATCH_MODES = MATCH_MODE_OPTIONS.map((option) => option.value)
export const SLOW_MATCH_MODES = new Set(['endswith', 'contains'])

export const STATUS_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'successful', label: 'Successful' },
  { value: 'unsuccessful', label: 'Unsuccessful' },
  { value: 'unknown', label: 'Unknown (blank)' },
]
const STATUS_VALUES = STATUS_OPTIONS.map((option) => option.value)

export const MULTI_FILTERS = ['ingress_ip_group', 'egress_ip_group', 'termination_reason']
// [value key, match key, default match mode]; defaults mirror the backend.
export const TEXT_FILTERS = [
  ['ani', 'ani_match', 'contains'],
  ['dnis', 'dnis_match', 'contains'],
  ['call_id', 'call_id_match', 'exact'],
  ['termination_text', 'termination_match', 'contains'],
]

export const SORT_FIELDS = [
  'setuptime',
  'ingressani',
  'ingressdnis',
  'egressani',
  'egressdnis',
  'ingressipgroup',
  'egressipgroup',
  'issuccess',
  'id',
]
export const DEFAULT_SORT = 'setuptime'
export const DEFAULT_DIRECTION = 'desc'
export const DEFAULT_PAGE_SIZE = 100
export const MAX_TEXT_LENGTH = 255

export const STATISTICS_PRESETS = [
  { value: 'last_24h', label: 'Last 24 hours' },
  { value: 'last_48h', label: 'Last 48 hours' },
  { value: 'last_7d', label: 'Last 7 days' },
  { value: 'last_month', label: 'Last month' },
  { value: 'custom', label: 'Custom' },
]

/** Filters without a range, used by both search and statistics. */
export function emptyCriteria() {
  const criteria = { status: 'all' }
  MULTI_FILTERS.forEach((key) => {
    criteria[key] = []
  })
  TEXT_FILTERS.forEach(([key, matchKey, defaultMode]) => {
    criteria[key] = ''
    criteria[matchKey] = defaultMode
  })
  return criteria
}

export function defaultFilters(now = new Date()) {
  return { ...todayRange(now), ...emptyCriteria() }
}

export function cloneFilters(filters) {
  const copy = { ...filters }
  MULTI_FILTERS.forEach((key) => {
    copy[key] = [...(filters[key] || [])]
  })
  return copy
}

/** API query parameters for the non-range criteria. Match modes are sent only with a value. */
export function criteriaToParams(filters) {
  const params = {}
  MULTI_FILTERS.forEach((key) => {
    if (filters[key]?.length) {
      params[key] = [...filters[key]]
    }
  })
  TEXT_FILTERS.forEach(([key, matchKey]) => {
    const value = (filters[key] || '').trim()
    if (value) {
      params[key] = value
      params[matchKey] = filters[matchKey]
    }
  })
  if (filters.status && filters.status !== 'all') {
    params.status = filters.status
  }
  return params
}

export function filtersToParams(filters) {
  return { start: filters.start, end: filters.end, ...criteriaToParams(filters) }
}

function asList(value) {
  if (value === undefined || value === null) {
    return []
  }
  return (Array.isArray(value) ? value : [value]).filter(
    (item) => typeof item === 'string' && item.trim(),
  )
}

function asText(value) {
  const text = Array.isArray(value) ? value[0] : value
  return typeof text === 'string' ? text.slice(0, MAX_TEXT_LENGTH) : ''
}

function asChoice(value, allowed, fallback) {
  const text = asText(value)
  return allowed.includes(text) ? text : fallback
}

function asPositiveInt(value, fallback) {
  const number = Number.parseInt(asText(value), 10)
  return Number.isInteger(number) && number > 0 ? number : fallback
}

export function criteriaFromQuery(query) {
  const criteria = emptyCriteria()
  MULTI_FILTERS.forEach((key) => {
    criteria[key] = [...new Set(asList(query[key]))]
  })
  TEXT_FILTERS.forEach(([key, matchKey, defaultMode]) => {
    criteria[key] = asText(query[key])
    criteria[matchKey] = asChoice(query[matchKey], MATCH_MODES, defaultMode)
  })
  criteria.status = asChoice(query.status, STATUS_VALUES, 'all')
  return criteria
}

export function criteriaToQuery(filters) {
  const query = {}
  MULTI_FILTERS.forEach((key) => {
    if (filters[key]?.length) {
      query[key] = [...filters[key]]
    }
  })
  TEXT_FILTERS.forEach(([key, matchKey, defaultMode]) => {
    if (filters[key]) {
      query[key] = filters[key]
      if (filters[matchKey] !== defaultMode) {
        query[matchKey] = filters[matchKey]
      }
    }
  })
  if (filters.status && filters.status !== 'all') {
    query.status = filters.status
  }
  return query
}

/** Route query for a search state. Only non-default values are included; no credentials ever. */
export function searchStateToQuery({ filters, sort, direction, page, pageSize }) {
  const query = { start: filters.start, end: filters.end, ...criteriaToQuery(filters) }
  if (sort && sort !== DEFAULT_SORT) {
    query.sort = sort
  }
  if (direction && direction !== DEFAULT_DIRECTION) {
    query.direction = direction
  }
  if (page && page > 1) {
    query.page = String(page)
  }
  if (pageSize && pageSize !== DEFAULT_PAGE_SIZE) {
    query.page_size = String(pageSize)
  }
  return query
}

export function searchStateFromQuery(query, { pageSizeOptions = null } = {}) {
  const defaults = todayRange()
  const start = asText(query.start)
  const end = asText(query.end)
  const pageSize = asPositiveInt(query.page_size, DEFAULT_PAGE_SIZE)
  return {
    filters: {
      start: start && parseInstant(start) ? start : defaults.start,
      end: end && parseInstant(end) ? end : defaults.end,
      ...criteriaFromQuery(query),
    },
    sort: asChoice(query.sort, SORT_FIELDS, DEFAULT_SORT),
    direction: asChoice(query.direction, ['asc', 'desc'], DEFAULT_DIRECTION),
    page: asPositiveInt(query.page, 1),
    pageSize: !pageSizeOptions || pageSizeOptions.includes(pageSize) ? pageSize : DEFAULT_PAGE_SIZE,
  }
}

function normaliseQueryValue(value) {
  return Array.isArray(value) ? value.map(String) : [String(value)]
}

export function sameQuery(a = {}, b = {}) {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)])
  for (const key of keys) {
    const left = a[key] === undefined ? [] : normaliseQueryValue(a[key])
    const right = b[key] === undefined ? [] : normaliseQueryValue(b[key])
    if (left.length !== right.length || left.some((value, index) => value !== right[index])) {
      return false
    }
  }
  return true
}

export function hasQuery(query = {}) {
  return Object.keys(query).length > 0
}
