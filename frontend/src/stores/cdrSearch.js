/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { defineStore } from 'pinia'

import { describeCdrError, isCancelled, searchSdrs } from 'src/services/cdrApi'
import {
  DEFAULT_DIRECTION,
  DEFAULT_PAGE_SIZE,
  DEFAULT_SORT,
  cloneFilters,
  filtersToParams,
  searchStateToQuery,
} from 'src/utils/cdrQuery'

// Kept outside reactive state: controllers and promises must not be proxied.
let active = null

function requestParams({ filters, sort, direction, page, pageSize }) {
  return { ...filtersToParams(filters), sort, direction, page, page_size: pageSize }
}

export const useCdrSearchStore = defineStore('cdrSearch', {
  state: () => ({
    filters: null,
    sort: DEFAULT_SORT,
    direction: DEFAULT_DIRECTION,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    results: [],
    total: 0,
    totalPages: 0,
    applied: null,
    loading: false,
    error: null,
    resultKey: null,
    lastQuery: null,
  }),

  actions: {
    /**
     * Run a search. An identical in-flight request is reused; a different one is aborted.
     * Results already loaded for the same parameters are reused unless ``force`` is set.
     */
    run(state, { force = false } = {}) {
      const params = requestParams(state)
      const key = JSON.stringify(params)

      if (active?.key === key) {
        return active.promise
      }
      if (!force && this.resultKey === key && !this.error) {
        return Promise.resolve()
      }

      active?.controller.abort()
      const controller = new AbortController()

      this.filters = cloneFilters(state.filters)
      this.sort = state.sort
      this.direction = state.direction
      this.page = state.page
      this.pageSize = state.pageSize
      this.lastQuery = searchStateToQuery(state)
      this.loading = true
      this.error = null

      const promise = (async () => {
        try {
          const data = await searchSdrs(params, { signal: controller.signal })
          if (active?.controller !== controller) {
            return
          }
          this.results = data.results || []
          this.total = data.count ?? 0
          this.totalPages = data.total_pages ?? 0
          this.page = data.page ?? state.page
          this.pageSize = data.page_size ?? state.pageSize
          this.sort = data.sort?.field || state.sort
          this.direction = data.sort?.direction || state.direction
          this.applied = data.filters || null
          this.resultKey = key
        } catch (error) {
          if (isCancelled(error) || active?.controller !== controller) {
            return
          }
          this.error = describeCdrError(error, 'Unable to search SDRs.')
          this.results = []
          this.total = 0
          this.totalPages = 0
          this.applied = null
          this.resultKey = null
        } finally {
          if (active?.controller === controller) {
            active = null
            this.loading = false
          }
        }
      })()

      active = { key, controller, promise }
      return promise
    },
  },
})
