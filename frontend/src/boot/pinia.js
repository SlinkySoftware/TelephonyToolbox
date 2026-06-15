/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

import { boot } from 'quasar/wrappers'
import pinia from 'src/stores'

export default boot(({ app }) => {
  app.use(pinia)
})