from cucm.client_zeep import ZeepCucmClient


class Cucm14Client(ZeepCucmClient):
    version = '14'