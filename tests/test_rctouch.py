import pytest
import json
from xcomfort.devices import (RcTouch)

def test_rctouchstate():
    payload = {"deviceId":17,"info":[{"text":"1222","type":2,"value":"20.9"},{"text":"1223","type":2,"icon":1,"value":"42.5"}]}

    device = RcTouch(None, 1, "")

    device.handle_state(payload)
    assert device.state.value.temperature == 20.9
    assert device.state.value.humidity == 42.5
