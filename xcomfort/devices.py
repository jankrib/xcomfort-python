from contextlib import nullcontext
import rx


class LightState:
    def __init__(self, switch, dimmvalue):
        self.switch = switch
        self.dimmvalue = dimmvalue

    def __str__(self):
        return f"LightState({self.switch}, {self.dimmvalue})"

    __repr__ = __str__


class Light:
    def __init__(self, bridge, device_id, name, dimmable):
        self.bridge = bridge
        self.device_id = device_id
        self.name = name
        self.dimmable = dimmable

        self.state = rx.subject.BehaviorSubject(None)

    def handle_state(self, payload):
        switch = payload['switch']
        dimmvalue = payload['dimmvalue'] if self.dimmable else 99

        self.state.on_next(LightState(switch, dimmvalue))

    async def switch(self, switch: bool):
        await self.bridge.switch_device(self.device_id, {"switch": switch})

    async def dimm(self, value: int):
        value = max(0, min(99, value))
        await self.bridge.slide_device(self.device_id, {"dimmvalue": value})

    def __str__(self):
        return f"Light({self.device_id}, \"{self.name}\", dimmable: {self.dimmable}, state:{self.state.value})"

    __repr__ = __str__


class RcTouchState:
    def __init__(self, temperature, humidity):
        self.temperature = temperature
        self.humidity = humidity

    def __str__(self):
        return f"RcTouchState({self.temperature}, {self.humidity})"

    __repr__ = __str__


class RcTouch:
    def __init__(self, bridge, device_id, name):
        self.bridge = bridge
        self.device_id = device_id
        self.name = name

        self.state = rx.subject.BehaviorSubject(None)

    def handle_state(self, payload):
        if 'info' in payload:
            for info in payload['info']:
                if info['text'] == "1222":
                    temperature = float(info['value'])
                if info['text'] == "1223":
                    humidity = float(info['value'])

        self.state.on_next(RcTouchState(temperature, humidity))
    
    async def set(self, value: float):
        await self.bridge.slide_device(self.device_id, {"setpoint": value})


class UnknownDevice:
    def __init__(self, bridge, device_id, name):
        self.bridge = bridge
        self.device_id = device_id
        self.name = name

        self.state = rx.subject.BehaviorSubject(None)

    def handle_state(self, payload):
        pass
