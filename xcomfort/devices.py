

class Light:
    def __init__(self, deviceId, name, dimmable):
        self.deviceId = deviceId
        self.name = name
        self.dimmable = dimmable
        self.dimmvalue = 0
        self.switch = False
    
    def __str__(self):
        return f"Light({self.deviceId}, \"{self.name}\", dimmable: True)"

    __repr__ = __str__

    