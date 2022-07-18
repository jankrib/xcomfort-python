import pytest
from mock import patch, Mock
import json
from xcomfort.bridge import Bridge
from xcomfort.devices import (Light, LightState)
from xcomfort.messages import Messages


class MockBridge(Bridge):
    def __init__(self):
        self._sent_message = None

    async def send_message(self, message_type, message):
        self._sent_message = message


@pytest.mark.asyncio
async def test_light_switch_on():
    bridge = MockBridge()
    device = Light(bridge, 1, "", True)

    await device.switch(True)

    assert bridge._sent_message == {"deviceId": 1, "switch": True}


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
