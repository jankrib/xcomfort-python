import rx

class LightState:
    def __init__(self, switch, dimmvalue):
        self.switch = switch
        self.dimmvalue = dimmvalue

    def __str__(self):
        return f"LightState({self.switch}, {self.dimmvalue})"

    __repr__ = __str__


class Light:
    def __init__(self, bridge, device_id, name, dimmable, state:LightState):
        self.bridge = bridge
        self.device_id = device_id
        self.name = name
        self.dimmable = dimmable

        self.state = rx.subject.BehaviorSubject(state)

    async def switch(self, switch:bool):
        await self.bridge.switch_device(self.device_id, switch)

    async def dimm(self, value:int):
        value = max(0, min(99, value))
        await self.bridge.dimm_device(self.device_id, value)

    def __str__(self):
        return f"Light({self.device_id}, \"{self.name}\", dimmable: {self.dimmable}, state:{self.state.value})"

    __repr__ = __str__

