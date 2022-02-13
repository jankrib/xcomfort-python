import aiohttp
import asyncio
import string
import time
import rx
import rx.operators as ops
from enum import Enum
from .connection import Messages, SecureBridgeConnection, setup_secure_connection
from .devices import (Light, LightState)

class State(Enum):
    Uninitialized = 0
    Initializing = 1
    Ready = 2
    Closing = 10


class Bridge:
    def __init__(self, ip_address:str, authkey:str, session = None):
        self.ip_address = ip_address
        self.authkey = authkey

        if session is None:
            session = aiohttp.ClientSession()
            closeSession = True
        else:
            closeSession = False

        self._session = session
        self._closeSession = closeSession

        self._devices = {}
        self.state = State.Uninitialized
        self.connection = None
        self.connection_subscription = None
        self.logger = lambda x: None
  
    async def run(self):
        if self.state != State.Uninitialized:
            raise Exception("Run can only be called once at a time")

        self.state = State.Initializing

        while self.state != State.Closing:
            try:
                self.logger(f"Connecting...")
                await self._connect()
                await self.connection.pump()

            except Exception as e:
                self.logger(f"Error: {repr(e)}")
                await asyncio.sleep(5)

            if self.connection_subscription is not None:
                self.connection_subscription.dispose()
        
        self.state = State.Uninitialized

    async def switch_device(self, device_id, switch:bool):
        await self.connection.send_message(Messages.ACTION_SWITCH_DEVICE, {"deviceId":device_id,"switch":switch})

    async def dimm_device(self, device_id, value:int):
        await self.connection.send_message(Messages.ACTION_SLIDE_DEVICE, {"deviceId":device_id,"dimmvalue":value})

    def _add_device(self, device):
        self._devices[device.device_id] = device

    def _handle_SET_DEVICE_STATE(self, payload):
        try:
            device = self._devices[payload['deviceId']]

            if isinstance(device, Light):
                device.state.on_next(LightState(payload['switch'], payload['dimmvalue']))
        except KeyError:
            return
    
    def _handle_SET_STATE_INFO(self, payload):
        for item in payload['item']:
            try:
                deviceId = item['deviceId']
                device = self._devices[deviceId]

                if isinstance(device, Light):
                    device.state.on_next(LightState(item['switch'], item['dimmvalue']))
            except KeyError:
                continue

    def _handle_SET_ALL_DATA(self, payload):
        if 'lastItem' in payload:
            self.state = State.Ready
        
        if 'devices' in payload:
            for device in payload['devices']:
                try:
                    device_id = device['deviceId']
                    name = device['name']
                    dimmable = device['dimmable']
                except KeyError:
                    continue
                state = LightState(device['switch'], device['dimmvalue'])

                light = Light(self, device_id, name, dimmable, state)

                self._add_device(light)


    def _handle_UNKNOWN(self, message_type, payload):
        self.logger(f"Unhandled package [{message_type.name}]: {payload}")
        pass

    def _onMessage(self, message):
        if 'payload' in message:
            message_type = Messages(message['type_int'])
            method_name = '_handle_' + message_type.name
            method = getattr(self, method_name, lambda p: self._handle_UNKNOWN(message_type, p))
            method(message['payload'])
        else:
            self.logger(f"Not known: {message}")


    async def _connect(self):
        self.connection = await setup_secure_connection(self._session, self.ip_address, self.authkey)
        self.connection_subscription = self.connection.messages.subscribe(self._onMessage)

    async def close(self):
        self.state = State.Closing

        if isinstance(self.connection, SecureBridgeConnection):
            self.connection_subscription.dispose()
            await self.connection.close()

        
        if self._closeSession:
            await self._session.close()

    async def get_devices(self):
        if self.state == State.Uninitialized:
            await asyncio.sleep(0.1)

        while self.state == State.Initializing:
            await asyncio.sleep(0.1)

        return self._devices
