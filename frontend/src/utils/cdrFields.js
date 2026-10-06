/*
 * SPDX-FileCopyrightText: Copyright 2026, Slinky Software
 * SPDX-License-Identifier: GPL-3.0-only
 */

// Frontend labels and presentation hints for the AudioCodes source fields. Source field names are
// never renamed; these only describe how each raw value is shown.

export const SDR_LABELS = {
  id: 'SDR database ID',
  recordtype: 'Record type',
  sessionid: 'Session ID',
  setuptime: 'Setup time',
  connecttime: 'Connect time',
  releasetime: 'Release time',
  timetoconnect: 'Time to connect',
  callduration: 'Call duration',
  sourceip: 'Source IP',
  destinationip: 'Destination IP',
  ingressipgroup: 'Ingress IP group',
  egressipgroup: 'Egress IP group',
  ingressani: 'Ingress ANI',
  ingressdnis: 'Ingress DNIS',
  egressani: 'Egress ANI',
  egressdnis: 'Egress DNIS',
  ingresscallid: 'Ingress Call-ID',
  egresscallid: 'Egress Call-ID',
  ingressremotertpip: 'Ingress remote RTP IP',
  ingressremotertpport: 'Ingress remote RTP port',
  egressremotertpip: 'Egress remote RTP IP',
  egressremotertpport: 'Egress remote RTP port',
  globalsessionid: 'Global Session ID',
  ingressterminationreason: 'Ingress termination reason',
  egressterminationreason: 'Egress termination reason',
  ingresssipterminationreason: 'Ingress SIP termination reason',
  egresssipterminationreason: 'Egress SIP termination reason',
  issuccess: 'Success',
}

export const CDR_LABELS = {
  id: 'CDR database ID',
  cdrtype: 'CDR type',
  reporttype: 'Report type',
  callid: 'Call-ID',
  globalsessionid: 'Global Session ID',
  sessionid: 'Session ID',
  legid: 'Leg ID',
  callerdisplayid: 'Caller display ID',
  sourceusernamebeforemanip: 'Source username before manipulation',
  sourceusername: 'Source username',
  sourcetags: 'Source tags',
  calleedisplayid: 'Callee display ID',
  destinationusernamebeforemanip: 'Destination username before manipulation',
  destinationusername: 'Destination username',
  destinationtags: 'Destination tags',
  sipinterfacename: 'SIP interface name',
  ipgroupname: 'IP group name',
  proxysetname: 'Proxy set name',
  remoteip: 'Remote signalling IP',
  remoteport: 'Remote signalling port',
  remotertpip: 'Remote RTP IP',
  remotertpport: 'Remote RTP port',
  codertype: 'Coder type',
  callorig: 'Call origin',
  terminationside: 'Termination side',
  cdrtrigger: 'CDR trigger',
  alertingtime: 'Alerting time',
  callduration: 'Call duration',
  wascallstarted: 'Call started',
  callsuccess: 'Call success',
  setuptime: 'Setup time',
  connecttime: 'Connect time',
  releasetime: 'Release time',
  terminationreason: 'Termination reason',
  terminationreasoncategory: 'Termination reason category',
  sipterminationreason: 'SIP termination reason',
  sipterminationdescription: 'SIP termination description',
  terminationsideradius: 'Termination side (RADIUS)',
  terminationsideyesno: 'Termination side (yes/no)',
  terminationreasonvalue: 'Termination reason value',
  localjitter: 'Local jitter',
  localpacketloss: 'Local packet loss',
  localroundtripdelay: 'Local round-trip delay',
  remotejitter: 'Remote jitter',
  remotepacketloss: 'Remote packet loss',
  remoteroundtripdelay: 'Remote round-trip delay',
  varcalluserdefined1: 'User Defined 1',
  varcalluserdefined2: 'User Defined 2',
  varcalluserdefined3: 'User Defined 3',
  varcalluserdefined4: 'User Defined 4',
  varcalluserdefined5: 'User Defined 5',
}

const TIMESTAMP_FIELDS = new Set(['setuptime', 'connecttime', 'releasetime'])
const SDR_DURATION_FIELDS = new Set(['timetoconnect', 'callduration'])
const CDR_DURATION_FIELDS = new Set(['alertingtime', 'callduration'])
const COPY_FIELDS = new Set([
  'id',
  'sessionid',
  'globalsessionid',
  'ingresscallid',
  'egresscallid',
  'callid',
  'ingressani',
  'ingressdnis',
  'egressani',
  'egressdnis',
  'sourceusernamebeforemanip',
  'sourceusername',
  'destinationusernamebeforemanip',
  'destinationusername',
])
const MONO_FIELDS = new Set([
  'sourceip',
  'destinationip',
  'ingressremotertpip',
  'ingressremotertpport',
  'egressremotertpip',
  'egressremotertpport',
  'remoteip',
  'remoteport',
  'remotertpip',
  'remotertpport',
  'legid',
  'terminationreasonvalue',
])
export const SDR_TERMINATION_FIELDS = [
  'ingressterminationreason',
  'egressterminationreason',
  'ingresssipterminationreason',
  'egresssipterminationreason',
]
export const TERMINATION_FIELD_SHORT_LABELS = {
  ingressterminationreason: 'Ingress',
  egressterminationreason: 'Egress',
  ingresssipterminationreason: 'Ingress SIP',
  egresssipterminationreason: 'Egress SIP',
}
const CDR_TERMINATION_EXPLAINED = new Set(['terminationreason', 'sipterminationreason'])
export const MEDIA_FIELDS = new Set([
  'localjitter',
  'localpacketloss',
  'localroundtripdelay',
  'remotejitter',
  'remotepacketloss',
  'remoteroundtripdelay',
])
const TAG_FIELDS = new Set(['sourcetags', 'destinationtags'])
const SUCCESS_FIELDS = new Set(['issuccess', 'callsuccess'])
const BOOLEAN_FIELDS = new Set(['wascallstarted', 'terminationsideyesno'])

export const SDR_SECTIONS = {
  overview: [
    'setuptime',
    'connecttime',
    'releasetime',
    'timetoconnect',
    'callduration',
    'ingressipgroup',
    'egressipgroup',
    'ingressani',
    'ingressdnis',
    'egressani',
    'egressdnis',
  ],
  path: [
    'sourceip',
    'destinationip',
    'ingressipgroup',
    'egressipgroup',
    'ingressani',
    'ingressdnis',
    'egressani',
    'egressdnis',
  ],
  timing: ['setuptime', 'connecttime', 'releasetime', 'timetoconnect', 'callduration'],
  termination: [...SDR_TERMINATION_FIELDS, 'issuccess'],
  media: ['ingressremotertpip', 'ingressremotertpport', 'egressremotertpip', 'egressremotertpport'],
  identifiers: [
    'id',
    'recordtype',
    'sessionid',
    'globalsessionid',
    'ingresscallid',
    'egresscallid',
  ],
}

export const CDR_GROUPS = [
  {
    key: 'identity',
    label: 'Identity',
    fields: ['id', 'cdrtype', 'reporttype', 'callid', 'sessionid', 'globalsessionid', 'legid'],
  },
  {
    key: 'parties',
    label: 'Calling and called party',
    fields: [
      'callerdisplayid',
      'sourceusernamebeforemanip',
      'sourceusername',
      'sourcetags',
      'calleedisplayid',
      'destinationusernamebeforemanip',
      'destinationusername',
      'destinationtags',
    ],
  },
  {
    key: 'routing',
    label: 'Routing',
    fields: [
      'sipinterfacename',
      'ipgroupname',
      'proxysetname',
      'remoteip',
      'remoteport',
      'callorig',
      'terminationside',
    ],
  },
  {
    key: 'media',
    label: 'Media',
    topic: 'media_quality',
    fields: [
      'remotertpip',
      'remotertpport',
      'codertype',
      'localjitter',
      'localpacketloss',
      'localroundtripdelay',
      'remotejitter',
      'remotepacketloss',
      'remoteroundtripdelay',
    ],
  },
  {
    key: 'timing',
    label: 'Timing and outcome',
    topic: 'timing',
    fields: [
      'cdrtrigger',
      'alertingtime',
      'callduration',
      'wascallstarted',
      'callsuccess',
      'setuptime',
      'connecttime',
      'releasetime',
    ],
  },
  {
    key: 'termination',
    label: 'Termination',
    topic: 'termination_reason',
    fields: [
      'terminationreason',
      'terminationreasoncategory',
      'sipterminationreason',
      'sipterminationdescription',
      'terminationsideradius',
      'terminationsideyesno',
      'terminationreasonvalue',
    ],
  },
  {
    key: 'user_defined',
    label: 'User-defined fields',
    fields: [
      'varcalluserdefined1',
      'varcalluserdefined2',
      'varcalluserdefined3',
      'varcalluserdefined4',
      'varcalluserdefined5',
    ],
  },
]

function fieldType(key, kind) {
  if (TIMESTAMP_FIELDS.has(key)) {
    return 'timestamp'
  }
  if ((kind === 'sdr' ? SDR_DURATION_FIELDS : CDR_DURATION_FIELDS).has(key)) {
    return 'duration'
  }
  if (SUCCESS_FIELDS.has(key)) {
    return 'status'
  }
  if (BOOLEAN_FIELDS.has(key)) {
    return 'boolean'
  }
  if (kind === 'cdr' && MEDIA_FIELDS.has(key)) {
    return 'media'
  }
  if (kind === 'cdr' && TAG_FIELDS.has(key)) {
    return 'tags'
  }
  return 'text'
}

/**
 * Build CdrFieldGrid items for raw source fields.
 * ``context`` supplies help text, user-defined labels, media thresholds and termination explanations.
 */
export function buildFieldItems(kind, keys, raw, context = {}) {
  const labels = kind === 'sdr' ? SDR_LABELS : CDR_LABELS
  const help = context.help?.[kind] || {}
  const explanations = context.help?.termination_reasons || {}
  return keys.map((key) => {
    const value = raw?.[key] ?? null
    const userDefined = context.userDefinedFields?.[key]
    const item = {
      key,
      label: userDefined?.label || labels[key] || key,
      sourceName: key,
      value,
      type: fieldType(key, kind),
      help: [help[key], userDefined?.description].filter(Boolean).join(' '),
      copy: COPY_FIELDS.has(key),
      mono: COPY_FIELDS.has(key) || MONO_FIELDS.has(key),
    }
    if (item.type === 'media') {
      item.mediaConfig = context.mediaByField?.[key] || null
    }
    if (item.type === 'tags') {
      item.parsedTags = context.parsedTags?.[key] ?? null
    }
    const explained =
      kind === 'sdr' ? SDR_TERMINATION_FIELDS.includes(key) : CDR_TERMINATION_EXPLAINED.has(key)
    if (explained && typeof value === 'string' && explanations[value]) {
      item.note = explanations[value]
    }
    return item
  })
}
