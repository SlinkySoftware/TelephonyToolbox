# SPDX-FileCopyrightText: Copyright 2026, Slinky Software
# SPDX-License-Identifier: GPL-3.0-only

"""Unmanaged, read-only mappings of the AudioCodes ``public.sdr`` and ``public.cdr`` tables.

Field names must match the source columns exactly; never rename them here.
"""

from django.db import models

from audiocodes_cdr.exceptions import SourceWriteForbidden


def _forbidden(*args, **kwargs):
    raise SourceWriteForbidden('The AudioCodes source database is read-only.')


class ReadOnlySourceQuerySet(models.QuerySet):
    create = _forbidden
    bulk_create = _forbidden
    bulk_update = _forbidden
    get_or_create = _forbidden
    update_or_create = _forbidden
    update = _forbidden
    delete = _forbidden
    select_for_update = _forbidden
    _update = _forbidden
    _insert = _forbidden
    _raw_delete = _forbidden


ReadOnlySourceManager = models.Manager.from_queryset(ReadOnlySourceQuerySet)


class ReadOnlySourceModel(models.Model):
    objects = ReadOnlySourceManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        _forbidden()

    def delete(self, *args, **kwargs):
        _forbidden()


class Sdr(ReadOnlySourceModel):
    id = models.BigIntegerField(primary_key=True)
    recordtype = models.CharField(max_length=255, null=True)
    sessionid = models.CharField(max_length=255, null=True)
    setuptime = models.DateTimeField(null=True)
    connecttime = models.DateTimeField(null=True)
    releasetime = models.DateTimeField(null=True)
    timetoconnect = models.BigIntegerField(null=True)
    # Text in the source; only numeric strings may be cast.
    callduration = models.CharField(max_length=255, null=True)
    sourceip = models.CharField(max_length=255, null=True)
    destinationip = models.CharField(max_length=255, null=True)
    ingressipgroup = models.CharField(max_length=255, null=True)
    egressipgroup = models.CharField(max_length=255, null=True)
    ingressani = models.CharField(max_length=255, null=True)
    ingressdnis = models.CharField(max_length=255, null=True)
    egressani = models.CharField(max_length=255, null=True)
    egressdnis = models.CharField(max_length=255, null=True)
    ingresscallid = models.CharField(max_length=255, null=True)
    egresscallid = models.CharField(max_length=255, null=True)
    ingressremotertpip = models.CharField(max_length=255, null=True)
    ingressremotertpport = models.BigIntegerField(null=True)
    egressremotertpip = models.CharField(max_length=255, null=True)
    egressremotertpport = models.BigIntegerField(null=True)
    globalsessionid = models.CharField(max_length=255, null=True)
    ingressterminationreason = models.CharField(max_length=255, null=True)
    egressterminationreason = models.CharField(max_length=255, null=True)
    ingresssipterminationreason = models.CharField(max_length=255, null=True)
    egresssipterminationreason = models.CharField(max_length=255, null=True)
    issuccess = models.BooleanField(null=True)

    class Meta:
        managed = False
        db_table = 'sdr'
        default_permissions = ()

    def __str__(self):
        return f'SDR {self.pk}'


class Cdr(ReadOnlySourceModel):
    id = models.BigIntegerField(primary_key=True)
    cdrtype = models.CharField(max_length=255, null=True)
    reporttype = models.CharField(max_length=255, null=True)
    callid = models.CharField(max_length=255, null=True)
    globalsessionid = models.CharField(max_length=255, null=True)
    sessionid = models.CharField(max_length=255, null=True)
    legid = models.BigIntegerField(null=True)
    callerdisplayid = models.CharField(max_length=255, null=True)
    sourceusernamebeforemanip = models.CharField(max_length=255, null=True)
    sourceusername = models.CharField(max_length=255, null=True)
    sourcetags = models.CharField(max_length=255, null=True)
    calleedisplayid = models.CharField(max_length=255, null=True)
    destinationusernamebeforemanip = models.CharField(max_length=255, null=True)
    destinationusername = models.CharField(max_length=255, null=True)
    destinationtags = models.CharField(max_length=255, null=True)
    sipinterfacename = models.CharField(max_length=255, null=True)
    ipgroupname = models.CharField(max_length=255, null=True)
    proxysetname = models.CharField(max_length=255, null=True)
    remoteip = models.CharField(max_length=255, null=True)
    remoteport = models.BigIntegerField(null=True)
    remotertpip = models.CharField(max_length=255, null=True)
    remotertpport = models.BigIntegerField(null=True)
    codertype = models.CharField(max_length=255, null=True)
    callorig = models.CharField(max_length=255, null=True)
    terminationside = models.CharField(max_length=255, null=True)
    cdrtrigger = models.CharField(max_length=255, null=True)
    alertingtime = models.BigIntegerField(null=True)
    callduration = models.BigIntegerField(null=True)
    wascallstarted = models.BooleanField(null=True)
    callsuccess = models.BooleanField(null=True)
    setuptime = models.DateTimeField(null=True)
    connecttime = models.DateTimeField(null=True)
    releasetime = models.DateTimeField(null=True)
    terminationreason = models.CharField(max_length=255, null=True)
    terminationreasoncategory = models.CharField(max_length=255, null=True)
    sipterminationreason = models.CharField(max_length=255, null=True)
    sipterminationdescription = models.CharField(max_length=255, null=True)
    terminationsideradius = models.CharField(max_length=255, null=True)
    terminationsideyesno = models.BooleanField(null=True)
    terminationreasonvalue = models.BigIntegerField(null=True)
    localjitter = models.BigIntegerField(null=True)
    localpacketloss = models.BigIntegerField(null=True)
    localroundtripdelay = models.BigIntegerField(null=True)
    remotejitter = models.BigIntegerField(null=True)
    remotepacketloss = models.BigIntegerField(null=True)
    remoteroundtripdelay = models.BigIntegerField(null=True)
    varcalluserdefined1 = models.CharField(max_length=255, null=True)
    varcalluserdefined2 = models.CharField(max_length=255, null=True)
    varcalluserdefined3 = models.CharField(max_length=255, null=True)
    varcalluserdefined4 = models.CharField(max_length=255, null=True)
    varcalluserdefined5 = models.CharField(max_length=255, null=True)

    class Meta:
        managed = False
        db_table = 'cdr'
        default_permissions = ()

    def __str__(self):
        return f'CDR {self.pk}'


SDR_FIELDS = tuple(field.attname for field in Sdr._meta.concrete_fields)
CDR_FIELDS = tuple(field.attname for field in Cdr._meta.concrete_fields)
