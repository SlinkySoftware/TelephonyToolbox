/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { defineStore } from 'pinia'

import {
  fetchAuthOptions,
  fetchCurrentUser,
  ldapLogin,
  localLogin,
  logoutSession,
  startEntraLogin,
} from 'src/services/toolboxApi'

export const useSessionStore = defineStore('session', {
  state: () => ({
    user: null,
    authOptions: null,
    initialized: false,
    initializationPromise: null,
  }),

  actions: {
    async initialize() {
      if (this.initialized) {
        return
      }
      if (this.initializationPromise) {
        return this.initializationPromise
      }

      this.initializationPromise = (async () => {
        try {
          this.authOptions = await fetchAuthOptions()
        } catch (error) {
          // Keep router startup alive even when backend is temporarily unavailable.
          console.warn('Unable to load auth options during initialization', error)
          this.authOptions = {
            auth_mode: 'local',
            local_auth_enabled: true,
          }
        }
        try {
          this.user = await fetchCurrentUser()
        } catch {
          this.user = null
        }
        this.initialized = true
      })()

      try {
        await this.initializationPromise
      } finally {
        this.initializationPromise = null
      }
    },

    async refreshUser() {
      this.user = await fetchCurrentUser()
      return this.user
    },

    async signInLocal(payload) {
      this.user = await localLogin(payload)
      return this.user
    },

    async signInLdap(payload) {
      this.user = await ldapLogin(payload)
      return this.user
    },

    beginEntraLogin() {
      startEntraLogin()
    },

    async logout() {
      try {
        await logoutSession()
      } finally {
        this.user = null
      }
    },
  },
})