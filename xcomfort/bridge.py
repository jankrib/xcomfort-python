import aiohttp
import asyncio
import string
import time
import rx
import rx.operators as ops
from enum import Enum
from .connection import Messages, SecureBridgeConnection, setup_secure_connection
from .devices import Light

class State(Enum):
    Initializing = 1
    Ready = 2


class Bridge:
    def __init__(self, ip_address:str, authkey:str, session, closeSession:bool):
        self.ip_address = ip_address
        self.authkey = authkey
        self.__session = session
        self.__closeSession = closeSession

        self.__devices = {}
        self.state = State.Initializing
        self.connection = None
        self.connection_subscription = None

    @staticmethod
    async def connect(ip_address:str, authkey:str, session = None):
        closeSession = False
        if session is None:
            session = aiohttp.ClientSession()
            closeSession = True

        bridge = Bridge(ip_address, authkey, session, closeSession)

        try:
            await bridge.__connect()
        except:
            if closeSession:
                await session.close()
            
            raise

        return bridge

    async def switch_device(self, device_id, switch:bool):
        await self.connection.send_message(Messages.ACTION_SWITCH_DEVICE, {"deviceId":device_id,"switch":switch})

    def __add_device(self, device):
        self.__devices[device.device_id] = device

    def __update_state_from_payload(self, payload):
        if 'lastItem' in payload:
            self.state = State.Ready
        
        if 'devices' in payload:
            for device in payload['devices']:
                device_id = device['deviceId']
                name = device['name']
                dimmable = device['dimmable']

                light = Light(device_id, name, dimmable)
                light.switch = device['switch']
                light.dimmvalue = device['dimmvalue']

                self.__add_device(light)

    def __onMessage(self, message):
        if message['type_int'] == Messages.SET_ALL_DATA:
            self.__update_state_from_payload(message['payload'])

    async def __connect(self):
        self.connection = await setup_secure_connection(self.__session, self.ip_address, self.authkey)
        self.connection_subscription = self.connection.messages.subscribe(self.__onMessage)

    async def close(self):
        if isinstance(self.connection, SecureBridgeConnection):
            self.connection_subscription.dispose()
            await self.connection.close()

        
        if self.__closeSession:
            await self.__session.close()

    async def get_devices(self):

        while self.state == State.Initializing:
            await asyncio.sleep(0.1)

        return self.__devices
