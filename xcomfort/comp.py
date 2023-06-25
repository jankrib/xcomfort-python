import rx

class CompState:
    def __init__(self, raw):
        self.raw = raw

    def __str__(self):
        return f"CompState({self.raw})"

    __repr__ = __str__

class Comp:
    def __init__(self, bridge, comp_id, comp_type, name: str, payload: dict):
        self.bridge = bridge
        self.comp_id = comp_id
        self.comp_type = comp_type
        self.name = name
        self.payload = payload

        self.state = rx.subject.BehaviorSubject(None)

    def handle_state(self, payload):
        self.state.on_next(CompState(payload))

    def __str__(self):
        return f'Comp({self.comp_id}, "{self.name}", comp_type: {self.comp_type}, payload: {self.payload})'

    __repr__ = __str__
