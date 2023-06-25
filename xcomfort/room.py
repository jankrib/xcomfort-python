from unicodedata import numeric
import aiohttp
import asyncio
import string
import time
import rx
import rx.operators as ops
from enum import Enum
from .connection import SecureBridgeConnection, setup_secure_connection
from .messages import Messages
from .devices import (BridgeDevice, Light, RcTouch, Heater, Shade)

class RctMode(Enum):
    Cool = 1
    Eco = 2
    Comfort = 3

class RctState(Enum):
    Idle = 0
    Auto = 1
    Active = 2

class RctModeRange:
    def __init__(self, min:float, max:float):
        self.Min = min
        self.Max = max

class RoomState:
    def __init__(self, setpoint, temperature, humidity, power, mode:RctMode, state:RctState,  raw):
        self.setpoint = setpoint
        self.temperature = temperature
        self.humidity = humidity
        self.power = power
        self.mode = mode
        self.raw = raw
        self.rctstate = state

    def __str__(self):
        return f"RoomState({self.setpoint}, {self.temperature}, {self.humidity},{self.mode},{self.rctstate} {self.power})"

    __repr__ = __str__

class Room:
    def __init__(self, bridge, room_id, name: str):
        self.bridge = bridge
        self.room_id = room_id
        self.name = name
        self.state = rx.subject.BehaviorSubject(None)
        self.modesetpoints = dict()

    def handle_state(self, payload):
        print(f"Room.handle_state: {payload}")

        old_state = self.state.value

        if old_state is not None:
            old_state.raw.update(payload)
            payload = old_state.raw

        setpoint = payload.get('setpoint', None)
        temperature = payload.get('temp', None)
        humidity = payload.get('humidity', None)
        power = payload.get('power', 0.0)

        if 'currentMode' in payload:                # When handling from _SET_ALL_DATA
            mode = RctMode(payload.get('currentMode', None))
        if 'mode' in payload:                       # When handling from _SET_STATE_INFO
            mode = RctMode(payload.get('mode', None))

        # When handling from _SET_ALL_DATA, we get the setpoints for each mode/preset
        # Store these for later use
        if 'modes' in payload:
            for mode in payload["modes"]:
                self.modesetpoints[RctMode(mode["mode"])] = float(mode["value"])

        if 'state' in payload:
            currentstate = RctState(payload.get('state', None))

        self.state.on_next(RoomState(setpoint,temperature,humidity,power,mode,currentstate,payload))

    async def set_target_temperature(self, setpoint: float):

        # Validate that new setpoint is within allowed ranges.
        # if above/below allowed values, set to the edge value
        setpointrange = self.bridge.rctsetpointallowedvalues[RctMode(self.state.value.mode)]

        if setpointrange.Max < setpoint:
            setpoint = setpointrange.Max

        if setpoint < setpointrange.Min:
            setpoint = setpointrange.Min

        # Store new setpoint for current mode
        self.modesetpoints[self.state.value.mode.value] = setpoint

        await self.bridge.send_message(Messages.SET_HEATING_STATE, {"roomId":self.room_id,"mode":self.state.value.mode.value,"state":self.state.value.rctstate.value,"setpoint":setpoint,"confirmed":False})

    async def set_mode(self, mode:RctMode):

        #Find setpoint for the mode we are about to set, and use that
        #When transmitting heating_state message.
        newsetpoint = self.modesetpoints.get(mode)
        await self.bridge.send_message(Messages.SET_HEATING_STATE, {"roomId":self.room_id,"mode":mode.value,"state":self.state.value.rctstate.value,"setpoint":newsetpoint,"confirmed":False})

    def __str__(self):
        return f"Room({self.room_id}, \"{self.name}\")"

    __repr__ = __str__
