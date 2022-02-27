import pytest
import json
from xcomfort.devices import (Light, LightState, RcTouch)


def test_lightstate_switch_on():
    device = Light(None, 1, "", True)

    payload = {
        "switch": True,
        "dimmvalue": 50
    }

    device.handle_state(payload)

    assert device.state.value.switch == True
    assert device.state.value.dimmvalue == 50

def test_lightstate_switch_on_when_not_dimmable():
    device = Light(None, 1, "", False)

    payload = {
        "switch": True
    }

    device.handle_state(payload)

    assert device.state.value.switch == True

def test_rctouchstate():
    payload = {"deviceId":17,"info":[{"text":"1222","type":2,"value":"20.9"},{"text":"1223","type":2,"icon":1,"value":"42.5"}]}

    device = RcTouch(None, 1, "")

    device.handle_state(payload)
    assert device.state.value.temperature == 20.9
    assert device.state.value.humidity == 42.5
