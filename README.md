# xcomfort-python
Unofficial python package for communicating with Eaton xComfort Bridge

## Usage
```python
import asyncio
from xcomfort import Bridge


async def main():
    bridge = await Bridge.connect(<ip_address>, <auth_key>)

    devices = await bridge.get_devices()
    print(devices)
    
    await bridge.close()

asyncio.run(main())
```
