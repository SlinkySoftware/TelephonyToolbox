/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { SYDNEY_TZ, parseInstant } from 'src/utils/cdrTime'

const timestampFormatter = new Intl.DateTimeFormat('en-AU', {
  timeZone: SYDNEY_TZ,
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  fractionalSecondDigits: 3,
  hourCycle: 'h23',
  timeZoneName: 'short',
})

const INTEGER_TEXT = /^\s*-?\d+\s*$/

const bucketHourFormatter = new Intl.DateTimeFormat('en-AU', {
  timeZone: SYDNEY_TZ,
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})
const bucketDayFormatter = new Intl.DateTimeFormat('en-AU', {
  timeZone: SYDNEY_TZ,
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})

/** Compact Sydney label for a statistics bucket start (chart axes). */
export function formatBucketLabel(value, bucket) {
  const date = parseInstant(value)
  if (!date) {
    return ''
  }
  return (bucket === 'hour' ? bucketHourFormatter : bucketDayFormatter).format(date)
}

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }

/** Escape source-derived text before it is placed in ECharts HTML tooltips. */
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => HTML_ESCAPES[char])
}

export const DURATION_FORMATS = [
  { value: 'hms', label: 'HH:MM:SS.ff' },
  { value: 'seconds', label: 'Seconds' },
]

export function isBlank(value) {
  return value === null || value === undefined || (typeof value === 'string' && !value.trim())
}

/** ``DD/MM/YYYY HH:mm:ss.SSS z`` in Australia/Sydney. Unparseable values are returned unchanged. */
export function formatSydneyTimestamp(value) {
  if (isBlank(value)) {
    return ''
  }
  const date = parseInstant(value)
  if (!date) {
    return String(value)
  }
  const p = {}
  for (const { type, value: part } of timestampFormatter.formatToParts(date)) {
    p[type] = part
  }
  const hour = String(Number(p.hour) % 24).padStart(2, '0')
  return `${p.day}/${p.month}/${p.year} ${hour}:${p.minute}:${p.second}.${p.fractionalSecond} ${p.timeZoneName}`
}

function pad2(value) {
  return value.toString().padStart(2, '0')
}

/**
 * Interpret a duration in hundredths of a second.
 * Returns ``{ kind: 'blank' | 'invalid' | 'ok', hundredths }`` (hundredths is a BigInt when ok).
 */
export function parseHundredths(raw) {
  if (isBlank(raw)) {
    return { kind: 'blank', hundredths: null }
  }
  if (typeof raw === 'number') {
    return Number.isFinite(raw)
      ? { kind: 'ok', hundredths: BigInt(Math.round(raw)) }
      : { kind: 'invalid', hundredths: null }
  }
  if (typeof raw === 'bigint') {
    return { kind: 'ok', hundredths: raw }
  }
  if (typeof raw === 'string' && INTEGER_TEXT.test(raw)) {
    return { kind: 'ok', hundredths: BigInt(raw.trim()) }
  }
  return { kind: 'invalid', hundredths: null }
}

export function formatHundredths(hundredths, format = 'hms') {
  const negative = hundredths < 0n
  const absolute = negative ? -hundredths : hundredths
  const sign = negative ? '-' : ''
  const fraction = pad2(absolute % 100n)
  const totalSeconds = absolute / 100n
  if (format === 'seconds') {
    return `${sign}${totalSeconds}.${fraction} s`
  }
  const hours = totalSeconds / 3600n
  const minutes = (totalSeconds % 3600n) / 60n
  const seconds = totalSeconds % 60n
  return `${sign}${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}.${fraction}`
}

/**
 * Format a raw hundredths value. ``unformatted`` is true when a non-blank value is not numeric; the
 * original value is then returned as the text.
 */
export function formatDuration(raw, format = 'hms') {
  const parsed = parseHundredths(raw)
  if (parsed.kind === 'blank') {
    return { text: '', unformatted: false }
  }
  if (parsed.kind === 'invalid') {
    return { text: String(raw), unformatted: true }
  }
  return { text: formatHundredths(parsed.hundredths, format), unformatted: false }
}

export function formatDurationText(raw, format = 'hms') {
  return formatDuration(raw, format).text
}

export function displayValue(value) {
  if (value === null || value === undefined) {
    return ''
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  return String(value)
}

export function formatCount(value) {
  return typeof value === 'number' ? value.toLocaleString('en-AU') : ''
}

export function formatPercent(value) {
  return typeof value === 'number' ? `${value.toFixed(2)}%` : ''
}

export const OUTCOMES = {
  successful: {
    label: 'Successful',
    icon: 'check_circle',
    color: 'positive',
    className: 'cdr-status--ok',
  },
  unsuccessful: {
    label: 'Unsuccessful',
    icon: 'cancel',
    color: 'negative',
    className: 'cdr-status--fail',
  },
  unknown: { label: 'Unknown', icon: 'help', color: 'grey-7', className: 'cdr-status--unknown' },
}

export function outcomeFromBoolean(value) {
  if (value === true) {
    return 'successful'
  }
  if (value === false) {
    return 'unsuccessful'
  }
  return 'unknown'
}

export const MEDIA_STATUSES = {
  ok: { label: 'Within threshold', icon: 'check_circle', className: 'cdr-media--ok' },
  warning: { label: 'Warning', icon: 'warning', className: 'cdr-media--warning' },
  critical: { label: 'Critical', icon: 'error', className: 'cdr-media--critical' },
}

/** Threshold status for a media metric; ``none`` until a unit and threshold are configured. */
export function mediaStatus(value, config) {
  if (!config?.configured || isBlank(value)) {
    return 'none'
  }
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return 'none'
  }
  if (config.critical !== null && config.critical !== undefined && numeric >= config.critical) {
    return 'critical'
  }
  if (config.warning !== null && config.warning !== undefined && numeric >= config.warning) {
    return 'warning'
  }
  return 'ok'
}
