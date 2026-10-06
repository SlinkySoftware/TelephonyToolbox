/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { defineStore } from 'pinia'

import {
  describeCdrError,
  fetchStatisticsIpGroups,
  fetchStatisticsSummary,
  fetchStatisticsTerminationReasons,
  fetchStatisticsTimeseries,
  isCancelled,
} from 'src/services/cdrApi'
import { cloneFilters, criteriaToParams, emptyCriteria } from 'src/utils/cdrQuery'

const SECTIONS = {
  summary: fetchStatisticsSummary,
  timeseries: fetchStatisticsTimeseries,
  ipGroups: fetchStatisticsIpGroups,
  terminationReasons: fetchStatisticsTerminationReasons,
}

let active = null

function emptySections() {
  return { summary: null, timeseries: null, ipGroups: null, terminationReasons: null }
}

export function statisticsParams({ preset, start, end, criteria }) {
  const range = preset === 'custom' ? { start, end } : { preset }
  return { ...range, ...criteriaToParams(criteria) }
}

export const useCdrStatisticsStore = defineStore('cdrStatistics', {
  state: () => ({
    // Applied selection; the page edits its own draft copy.
    applied: { preset: 'last_24h', start: null, end: null, criteria: emptyCriteria() },
    data: emptySections(),
    errors: emptySections(),
    loading: false,
    resultKey: null,
  }),

  getters: {
    // The first source-level failure drives the module banner.
    sourceError: (state) =>
      Object.values(state.errors).find((error) => error && (error.sourceIssue || error.timeout)) ||
      null,
    otherErrors: (state) =>
      Object.values(state.errors).filter((error) => error && !error.sourceIssue && !error.timeout),
    resolvedRange: (state) => state.data.summary?.filters || state.data.timeseries?.filters || null,
    hasErrors: (state) => Object.values(state.errors).some(Boolean),
  },

  actions: {
    load(selection, { force = false } = {}) {
      const applied = {
        preset: selection.preset,
        start: selection.start,
        end: selection.end,
        criteria: cloneFilters(selection.criteria),
      }
      const params = statisticsParams(applied)
      const key = JSON.stringify(params)

      if (active?.key === key) {
        return active.promise
      }
      if (!force && this.resultKey === key && !this.hasErrors) {
        return Promise.resolve()
      }

      active?.controller.abort()
      const controller = new AbortController()
      this.applied = applied
      this.loading = true
      this.errors = emptySections()

      const requests = Object.entries(SECTIONS).map(async ([name, fetcher]) => {
        try {
          const data = await fetcher(params, { signal: controller.signal })
          if (active?.controller === controller) {
            this.data[name] = data
          }
        } catch (error) {
          if (isCancelled(error) || active?.controller !== controller) {
            return
          }
          this.data[name] = null
          this.errors[name] = describeCdrError(error, 'Unable to load statistics.')
        }
      })

      const promise = Promise.all(requests).finally(() => {
        if (active?.controller === controller) {
          active = null
          this.loading = false
          this.resultKey = key
        }
      })
      active = { key, controller, promise }
      return promise
    },
  },
})
