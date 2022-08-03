# xcomfort-python
Unofficial python package for communicating with Eaton xComfort Bridge

## Usage
```python
import asyncio
from xcomfort import Bridge

def observe_device(device):
    device.state.subscribe(lambda state: print(f"Device state [{device.device_id}] '{device.name}': {state}"))

async def main():
    bridge = Bridge(<ip_address>, <auth_key>)

    runTask = asyncio.create_task(bridge.run())

    devices = await bridge.get_devices()

    for device in devices.values():
        observe_device(device)
        
    # Wait 50 seconds. Try flipping the light switch manually while you wait
    await asyncio.sleep(50) 

    # Turn off all the lights.
    # for device in devices.values():
    #     await device.switch(False)
    #
    # await asyncio.sleep(5)

    await bridge.close()
    await runTask

asyncio.run(main())

```

## Tests
```python
python -m pytest
```
