from xknx.devices import Cover
from typing import Union
from dummy import DummyCover


class Blind:
    def __init__(self, xknx_cover: Union[Cover, DummyCover]):
        self._cover = xknx_cover

    @property
    def name(self):
        return self._cover.name

    async def handle_position_angle(self,position, angle):
        print(f"Setting {self.name} to position({position}) angle({angle})")

    async def handle_unknown_message_type(self,**kwargs):
        print(f"Unknown message type with args: {kwargs}")
