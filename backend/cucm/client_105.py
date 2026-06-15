from cucm.client_zeep import ZeepCucmClient


class Cucm105Client(ZeepCucmClient):
    version = '10.5'