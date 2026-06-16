/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

const routes = [
  {
    path: '/login',
    component: () => import('pages/AuthLoginPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', component: () => import('pages/LandingRedirectPage.vue') },
      { path: 'diversions', component: () => import('pages/MyDiversionsPage.vue') },
      {
        path: 'diversions/:id/edit',
        component: () => import('pages/EditDiversionPage.vue'),
        props: true,
      },
      {
        path: 'admin',
        component: () => import('pages/AdminDashboardPage.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'admin/users',
        component: () => import('pages/AdminUsersPage.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'admin/groups',
        component: () => import('pages/AdminGroupsPage.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'admin/diversions',
        component: () => import('pages/AdminDiversionsPage.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'admin/audit',
        component: () => import('pages/AdminAuditPage.vue'),
        meta: { adminOnly: true },
      },
      {
        path: 'admin/health',
        component: () => import('pages/AdminHealthPage.vue'),
        meta: { adminOnly: true },
      },
    ],
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
]

export default routes
