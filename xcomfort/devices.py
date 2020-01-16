
class Light:
    def __init__(self, device_id, name, dimmable):
        self.device_id = device_id
        self.name = name
        self.dimmable = dimmable
        self.dimmvalue = 0
        self.switch = False
    
    def __str__(self):
        return f"Light({self.device_id}, \"{self.name}\", dimmable: True)"

    __repr__ = __str__

