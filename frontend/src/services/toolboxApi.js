/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { api } from 'boot/api'

export async function fetchAuthOptions() {
  const { data } = await api.get('auth/options/')
  return data
}

export async function fetchCurrentUser() {
  const { data } = await api.get('auth/me/')
  return data
}

export async function localLogin(payload) {
  const { data } = await api.post('auth/login/local/', payload)
  return data
}

export async function ldapLogin(payload) {
  const { data } = await api.post('auth/login/ldap/', payload)
  return data
}

export function startEntraLogin() {
  window.location.href = '/api/auth/login/entra/'
}

export async function logoutSession() {
  const { data } = await api.post('auth/logout/')
  return data
}

export async function listDiversions() {
  const { data } = await api.get('diversions/')
  return data.results
}

export async function getDiversion(id) {
  const { data } = await api.get(`diversions/${id}/`)
  return data
}

export async function validateDiversionDestination(id, destination) {
  const { data } = await api.post(`diversions/${id}/validate-destination/`, { destination })
  return data
}

export async function updateDiversionDestination(id, destination) {
  const { data } = await api.post(`diversions/${id}/update-destination/`, { destination })
  return data
}

export async function refreshDiversion(id) {
  const { data } = await api.post(`diversions/${id}/refresh/`)
  return data
}

export async function listUsers(params = {}) {
  const { data } = await api.get('admin/users/', { params })
  return data
}

export async function validateExternalUser(email) {
  const { data } = await api.post('admin/users/validate/', { email })
  return data
}

export async function createUser(payload) {
  const { data } = await api.post('admin/users/', payload)
  return data
}

export async function updateUser(id, payload) {
  const { data } = await api.patch(`admin/users/${id}/`, payload)
  return data
}

export async function deleteUser(id) {
  await api.delete(`admin/users/${id}/`)
}

export async function listGroups(params = {}) {
  const { data } = await api.get('admin/groups/', { params })
  return data
}

export async function createGroup(payload) {
  const { data } = await api.post('admin/groups/', payload)
  return data
}

export async function updateGroup(id, payload) {
  const { data } = await api.patch(`admin/groups/${id}/`, payload)
  return data
}

export async function deleteGroup(id) {
  await api.delete(`admin/groups/${id}/`)
}

export async function listAdminDiversions() {
  const { data } = await api.get('admin/diversions/')
  return data.results
}

export async function validateSourceNumber(sourceNumber) {
  const { data } = await api.post('admin/diversions/validate-source/', { source_number: sourceNumber })
  return data
}

export async function createDiversion(payload) {
  const { data } = await api.post('admin/diversions/', payload)
  return data
}

export async function updateAdminDiversion(id, payload) {
  const { data } = await api.patch(`admin/diversions/${id}/`, payload)
  return data
}

export async function deleteAdminDiversion(id) {
  await api.delete(`admin/diversions/${id}/`)
}

export async function listAudit(params = {}) {
  const { data } = await api.get('admin/audit/', { params })
  return data
}

export async function getAdminHealth() {
  const { data } = await api.get('admin/health/')
  return data
}