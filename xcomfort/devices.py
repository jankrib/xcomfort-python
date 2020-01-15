

class Light:
    def __init__(self, deviceId, name, dimmable):
        self.deviceId = deviceId
        self.name = name
        self.dimmable = dimmable
        self.dimmvalue = 0
        self.switch = False

    