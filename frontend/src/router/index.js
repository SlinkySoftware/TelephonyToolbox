/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { defineRouter } from '#q-app/wrappers'
import {
  createRouter,
  createMemoryHistory,
  createWebHistory,
  createWebHashHistory,
} from 'vue-router'
import routes from './routes'
import pinia from 'src/stores'
import { useSessionStore } from 'src/stores/session'

/*
 * If not building with SSR mode, you can
 * directly export the Router instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Router instance.
 */

export default defineRouter((/* { store, ssrContext } */) => {
  const createHistory = process.env.SERVER
    ? createMemoryHistory
    : process.env.VUE_ROUTER_MODE === 'history'
      ? createWebHistory
      : createWebHashHistory

  const Router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,

    // Leave this as is and make changes in quasar.conf.js instead!
    // quasar.conf.js -> build -> vueRouterMode
    // quasar.conf.js -> build -> publicPath
    history: createHistory(process.env.VUE_ROUTER_BASE),
  })

  Router.beforeEach(async (to) => {
    const session = useSessionStore(pinia)
    await session.initialize()

    if (to.meta.guestOnly && session.user) {
      return session.user.role === 'app_admin' ? '/admin' : '/diversions'
    }

    if (to.meta.requiresAuth && !session.user) {
      return {
        path: '/login',
        query: to.fullPath === '/' ? {} : { redirect: to.fullPath },
      }
    }

    if (to.meta.adminOnly && session.user?.role !== 'app_admin') {
      return '/diversions'
    }

    return true
  })

  return Router
})
