/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { defineStore } from 'pinia'

import { describeCdrError, fetchDisplayConfig, updatePreferences } from 'src/services/cdrApi'
import { DEFAULT_PAGE_SIZE } from 'src/utils/cdrQuery'

let loadPromise = null

const SOURCE_LABELS = { replica: 'Read replica', primary: 'Primary' }

export const useCdrDisplayStore = defineStore('cdrDisplay', {
  state: () => ({
    config: null,
    loading: false,
    error: null,
    durationFormat: 'hms',
    savingPreference: false,
  }),

  getters: {
    help: (state) =>
      state.config?.help || { sdr: {}, cdr: {}, topics: {}, termination_reasons: {} },
    pageSizeOptions: (state) => state.config?.page_size_options || [25, 50, 100, 250, 500],
    defaultPageSize: (state) => state.config?.default_page_size || DEFAULT_PAGE_SIZE,
    maxMultiselect: (state) => state.config?.max_multiselect_values || 50,
    hourlyBucketMaxHours: (state) => state.config?.hourly_bucket_max_hours || 168,
    userDefinedFields: (state) => state.config?.user_defined_fields || {},
    mediaQuality: (state) => state.config?.media_quality || {},
    mediaByField: (state) => {
      const byField = {}
      Object.values(state.config?.media_quality || {}).forEach((config) => {
        if (config?.field) {
          byField[config.field] = config
        }
      })
      return byField
    },
    activeSource: (state) => state.config?.active_source || null,
    activeSourceLabel: (state) =>
      SOURCE_LABELS[state.config?.active_source] || state.config?.active_source || '',
    credentialUsable: (state) => state.config?.source_credential_usable !== false,
  },

  actions: {
    async load({ force = false } = {}) {
      if (this.config && !force) {
        return this.config
      }
      if (loadPromise) {
        return loadPromise
      }
      this.loading = true
      loadPromise = (async () => {
        try {
          const config = await fetchDisplayConfig()
          this.config = config
          this.durationFormat = config.duration_format || 'hms'
          this.error = null
          return config
        } catch (error) {
          this.error = describeCdrError(error, 'Unable to load CDR display settings.')
          return null
        } finally {
          this.loading = false
          loadPromise = null
        }
      })()
      return loadPromise
    },

    async setDurationFormat(format) {
      if (format === this.durationFormat) {
        return
      }
      const previous = this.durationFormat
      this.durationFormat = format
      this.savingPreference = true
      try {
        const data = await updatePreferences({ duration_format: format })
        this.durationFormat = data.duration_format
      } catch (error) {
        this.durationFormat = previous
        throw error
      } finally {
        this.savingPreference = false
      }
    },
  },
})
