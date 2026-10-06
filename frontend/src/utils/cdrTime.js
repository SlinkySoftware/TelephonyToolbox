/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

// Australia/Sydney wall-clock helpers. Instants are exchanged with the API as ISO 8601 strings with an
// explicit offset so DST-ambiguous local times are never re-interpreted.

export const SYDNEY_TZ = 'Australia/Sydney'
export const MAX_RANGE_MONTHS = 12

const ISO_WITH_OFFSET = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?)(\.\d+)?(Z|[+-]\d{2}:?\d{2})$/i
const LOCAL_DATE_TIME = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?$/
const DAY_MS = 24 * 60 * 60 * 1000

const partsFormatter = new Intl.DateTimeFormat('en-AU', {
  timeZone: SYDNEY_TZ,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hourCycle: 'h23',
})

function pad(value, length = 2) {
  return String(value).padStart(length, '0')
}

export function daysInMonth(year, month) {
  return new Date(Date.UTC(year, month, 0)).getUTCDate()
}

export function sydneyParts(date) {
  const parts = {}
  for (const { type, value } of partsFormatter.formatToParts(date)) {
    parts[type] = value
  }
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    hour: Number(parts.hour) % 24,
    minute: Number(parts.minute),
    second: Number(parts.second),
  }
}

export function sydneyOffsetMinutes(date) {
  const seconds = Math.floor(date.getTime() / 1000) * 1000
  const p = sydneyParts(date)
  const wall = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second)
  return Math.round((wall - seconds) / 60000)
}

/**
 * Convert Sydney wall-clock parts to an instant. Ambiguous times (DST end) resolve to the first
 * occurrence, matching the backend. Returns null for times skipped by the DST start gap.
 */
export function sydneyLocalToDate({ year, month, day, hour = 0, minute = 0, second = 0 }) {
  const wall = Date.UTC(year, month - 1, day, hour, minute, second)
  const offsets = new Set([
    sydneyOffsetMinutes(new Date(wall - DAY_MS)),
    sydneyOffsetMinutes(new Date(wall + DAY_MS)),
  ])
  const matches = []
  for (const offset of offsets) {
    const instant = new Date(wall - offset * 60000)
    if (sydneyOffsetMinutes(instant) === offset) {
      matches.push(instant)
    }
  }
  if (!matches.length) {
    return null
  }
  matches.sort((a, b) => a - b)
  return matches[0]
}

function formatOffset(minutes) {
  const sign = minutes < 0 ? '-' : '+'
  const absolute = Math.abs(minutes)
  return `${sign}${pad(Math.floor(absolute / 60))}:${pad(absolute % 60)}`
}

export function toSydneyIso(date) {
  const p = sydneyParts(date)
  const ms = date.getMilliseconds()
  const fraction = ms ? `.${pad(ms, 3)}` : ''
  return (
    `${p.year}-${pad(p.month)}-${pad(p.day)}T${pad(p.hour)}:${pad(p.minute)}:${pad(p.second)}` +
    `${fraction}${formatOffset(sydneyOffsetMinutes(date))}`
  )
}

/** Parse an API/route instant. Values without an offset are treated as Sydney wall-clock time. */
export function parseInstant(value) {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  if (typeof value !== 'string' || !value.trim()) {
    return null
  }
  const text = value.trim()
  const iso = ISO_WITH_OFFSET.exec(text)
  if (iso) {
    // Browsers only keep milliseconds; trimming keeps parsing consistent for microsecond values.
    const fraction = iso[2] ? iso[2].slice(0, 4) : ''
    const date = new Date(`${iso[1]}${fraction}${iso[3]}`)
    return Number.isNaN(date.getTime()) ? null : date
  }
  const local = parseLocalInput(text)
  return local.date
}

/**
 * Parse ``YYYY-MM-DD HH:mm[:ss]`` as Sydney wall-clock time.
 * Returns ``{ date, error }`` where error is ``format`` | ``nonexistent`` | null.
 */
export function parseLocalInput(text) {
  const match = LOCAL_DATE_TIME.exec((text || '').trim())
  if (!match) {
    return { date: null, error: 'format' }
  }
  const [year, month, day, hour, minute, second = '0'] = match.slice(1).map((part) => Number(part))
  if (
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > daysInMonth(year, month) ||
    hour > 23 ||
    minute > 59 ||
    second > 59
  ) {
    return { date: null, error: 'format' }
  }
  const date = sydneyLocalToDate({ year, month, day, hour, minute, second })
  return date ? { date, error: null } : { date: null, error: 'nonexistent' }
}

export function formatLocalInput(value) {
  const date = parseInstant(value)
  if (!date) {
    return ''
  }
  const p = sydneyParts(date)
  return `${p.year}-${pad(p.month)}-${pad(p.day)} ${pad(p.hour)}:${pad(p.minute)}:${pad(p.second)}`
}

export function addSydneyMonths(date, months) {
  const p = sydneyParts(date)
  const index = p.month - 1 + months
  const year = p.year + Math.floor(index / 12)
  const month = (((index % 12) + 12) % 12) + 1
  const day = Math.min(p.day, daysInMonth(year, month))
  return (
    sydneyLocalToDate({ ...p, year, month, day }) ||
    new Date(Date.UTC(year, month - 1, day, p.hour, p.minute, p.second) - 10 * 60 * 60 * 1000)
  )
}

export function rangeExceedsLimit(start, end, months = MAX_RANGE_MONTHS) {
  return end.getTime() > addSydneyMonths(start, months).getTime()
}

/** Today in Sydney: local midnight through the current time, rounded up to the next minute. */
export function todayRange(now = new Date()) {
  const p = sydneyParts(now)
  const start = sydneyLocalToDate({ year: p.year, month: p.month, day: p.day })
  const end = new Date(Math.floor(now.getTime() / 60000) * 60000 + 60000)
  return { start: toSydneyIso(start), end: toSydneyIso(end) }
}

export function sydneyZoneName(value) {
  const date = parseInstant(value)
  if (!date) {
    return ''
  }
  const part = new Intl.DateTimeFormat('en-AU', { timeZone: SYDNEY_TZ, timeZoneName: 'short' })
    .formatToParts(date)
    .find((item) => item.type === 'timeZoneName')
  return part ? part.value : ''
}
