from aenum import IntFlag

class Mode(IntFlag):
    std = 1
    taiko = 2
    catch = 4
    mania = 8

class Status(IntFlag):
    bubble = 1
    qualify = 2
    disqualify = 4
    pop = 8
    ranked = 16
    loved = 32

class Hook:
    def __init__(self, res):
        self.hook_url = res[0]
        self.webhook_id = res[1]
        self.webhook_token = res[2]
        self.mode = Mode(int(res[3]))
        self.push_status = Status(int(res[4]))
        self.status = res[5]
        self.uid = res[6]
    
    def to_dict(self):
        return {
            "url": self.hook_url,
            "mode": int(self.mode),
            "push_status": int(self.push_status),
            "status": self.status,
            "id": self.webhook_id
        }

    def __hash__(self):
        return hash(self.to_dict())
    
    def __iter__(self):
        # hax
        temp = (
            self.hook_url,
            self.webhook_id,
            self.webhook_token,
            int(self.mode),
            int(self.push_status),
            self.status,
            self.uid
        )
        for m in temp:
            yield m