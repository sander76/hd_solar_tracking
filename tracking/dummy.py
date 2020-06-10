import yaml


class DummyXKNX:
    def __init__(self,config):
        with open(config) as file:
            yml = yaml.load(file.read())

        self.config = yml
        self.devices={}
        for name,device in self.config['groups']['cover'].items():
            self.devices[name]=DummyXknxBlind(name,device)


class DummyXknxBlind:
    """Dummy xknx cover device."""

    def __init__(self,name, *args,**kwargs):
        self.name=name

    async def set_up(self):
        self._position = 0
        print("%s went up!" % (self.name))

    async def set_down(self):
        self._position = 100
        print("%s went down" % (self.name))

    async def set_angle(self, angle):
        self._angle = angle
        print("%s angle set to: %d" % (self.name, angle))

    async def set_position(self, position):
        self._position = position
        print("%s position set to: %d" % (self.name, position))
