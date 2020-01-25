# xcomfort-python
Unofficial python package for communicating with Eaton xComfort Bridge

## Usage
```python
import asyncio
from xcomfort import Bridge


async def main():
    bridge = await Bridge.connect(<ip_address>, <auth_key>)

    devices = await bridge.get_devices()

    for device in devices.values():
        device.state.subscribe(lambda state: print(f"State [Device#{device.device_id}]: {state}"))
    
    # Wait 50 seconds. Try flipping the light switch manually while you wait
    await asyncio.sleep(50) 

    # Turn off all the lights.
    for device in devices.values():
        await device.switch(False)


    await asyncio.sleep(10)
    
    await bridge.close()

asyncio.run(main())
```
