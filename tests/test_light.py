import pytest
import json
from xcomfort.devices import (Light, LightState)


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

