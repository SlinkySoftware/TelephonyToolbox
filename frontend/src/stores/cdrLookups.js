/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { defineStore } from 'pinia'

import {
  describeCdrError,
  fetchEgressIpGroups,
  fetchIngressIpGroups,
  fetchTerminationReasons,
} from 'src/services/cdrApi'

const LOADERS = {
  ingress: fetchIngressIpGroups,
  egress: fetchEgressIpGroups,
  terminationReasons: fetchTerminationReasons,
}

const pending = {}

function emptyLookup() {
  return { values: [], loaded: false, loading: false, error: null, stale: false, refreshedAt: null }
}

export const useCdrLookupsStore = defineStore('cdrLookups', {
  state: () => ({
    ingress: emptyLookup(),
    egress: emptyLookup(),
    terminationReasons: emptyLookup(),
    windowDays: null,
  }),

  actions: {
    async loadOne(name, { force = false } = {}) {
      const lookup = this[name]
      if ((lookup.loaded && !force) || pending[name]) {
        return pending[name]
      }
      lookup.loading = true
      pending[name] = (async () => {
        try {
          const data = await LOADERS[name]()
          lookup.values = Array.isArray(data.results) ? data.results : []
          lookup.stale = Boolean(data.stale)
          // A stale response still carries the reason the refresh failed.
          lookup.error = data.stale ? describeCdrError({ response: { status: 200, data } }) : null
          lookup.refreshedAt = data.refreshed_at || null
          lookup.loaded = true
          if (name === 'terminationReasons' && data.window_days) {
            this.windowDays = data.window_days
          }
        } catch (error) {
          lookup.error = describeCdrError(error, 'Lookup values are unavailable.')
        } finally {
          lookup.loading = false
          delete pending[name]
        }
      })()
      return pending[name]
    },

    loadAll(options = {}) {
      return Promise.all(Object.keys(LOADERS).map((name) => this.loadOne(name, options)))
    },

    reset() {
      this.ingress = emptyLookup()
      this.egress = emptyLookup()
      this.terminationReasons = emptyLookup()
      this.windowDays = null
    },
  },
})
