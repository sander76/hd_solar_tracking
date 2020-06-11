import asyncio
import json
import yaml
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Union
import pydantic_loader
from asyncio_mqtt import Client, MqttError
from xknx import XKNX
from xknx.devices import Cover
import blind
import dummy
import config
import logging

_LOGGER=logging.getLogger(__name__)

east_blinds = []
west_blinds = []
north_blinds = []
south_blinds = []


class BlindGroup:
    """Glue class between XKNX and MQTT."""

    def __init__(self, topic):
        self.shades: List[blind.Blind] = []
        self._topic = topic
        self.watch_task=None

    def start_watching(self,client):
        loop = asyncio.get_running_loop()
        self.watch_task = loop.create_task(self.handle_messages(client))

    def stop_watching(self):
        if not self.watch_task:
            return
        try:
            self.watch_task.cancel()
        except asyncio.CancelledError:
            print("cancelled watching task.")

    async def handle_position_angle(self,pos, angle):
        _LOGGER.debug("Sending out data to individual blinds.")
        await asyncio.gather(
            *(shade.handle_position_angle(pos, angle) for shade in self.shades)
        )

    async def handle_unknown_message_type(self,**kwargs):
        await asyncio.gather(
            *(shade.handle_unknown_message_type(**kwargs) for shade in self.shades)
        )

    async def handle_messages(self,client:Client):
        """Hier stop je logica in die inkomende berichten leest en 
        vervolgens jouw knx blind aanstuurt.
        """
        topic = f"{self._topic}/#"
        _LOGGER.debug(f"Start watching: {self._topic}")
        
        async with client.filtered_messages(topic) as messages:
            async for message in messages:
                data = json.loads(message.payload.decode("utf-8"))
                _LOGGER.debug("topic: %s data: %s",message.topic,data)
                
                if message.topic == f"{self._topic}/pos_ang":
                    _LOGGER.debug("Angle position topic found.")
                    position = data["pos"]
                    angle=data["ang"]
                    await self.handle_position_angle(position,angle)
                else:
                    _LOGGER.error("Incoming message with unknown topic: %s",message.topic)
                    await self.handle_unknown_message_type(**data)
                    
        _LOGGER.debug("Finished.")

def grouping(xknx: Union[XKNX, dummy.DummyXKNX]) -> List[BlindGroup]:
    group_north = BlindGroup("building/noordgevel")
    group_east = BlindGroup("building/oostgevel")
    group_south = BlindGroup("building/zuidgevel")
    group_west = BlindGroup("building/westgevel")

    for device in xknx.devices.values():
        if "East" in device.name:
            group_east.shades.append(blind.Blind(device))
        elif "West" in device.name:
            group_west.shades.append(blind.Blind(device))
        elif "South" in device.name:
            group_south.shades.append(blind.Blind(device))
        elif "North" in device.name:
            group_north.shades.append(blind.Blind(device))

    return group_north, group_east, group_south, group_west


async def start(
    app_config: "config.AppConfig",
    blind_groups:BlindGroup
):
    """Start."""

    async with Client(app_config.mqtt_address) as client:

        await client.subscribe("building/#")
        
        while True:
            try:
                for blind_group in blind_groups:
                    blind_group.start_watching(client)
                await asyncio.gather(*(blind_group.watch_task for blind_group in blind_groups))
            except MqttError as error:
                _LOGGER.error(error)
                await asyncio.sleep(3)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    _LOGGER.debug("Starting application.")
    loop = asyncio.get_event_loop()

    parser = ArgumentParser()
    parser.add_argument(
        "xknxconfig", help="yaml config files where your blinds are configured."
    )
    parser.add_argument("--appconfig", help="App config file.", default=None)
    parser.add_argument("--demo", help="Run the app in demo mode", action="store_true")
    args = parser.parse_args()

    app_config = pydantic_loader.load_json(config.AppConfig, args.appconfig)

    xknxconfig = Path(args.xknxconfig)

    if args.demo:
        xknx = dummy.DummyXKNX(config=str(xknxconfig))
    else:
        xknx = XKNX(config=str(xknxconfig))
    
    blind_groups = grouping(xknx)

    try:
        loop.run_until_complete(
            start(app_config=app_config,blind_groups=blind_groups)
        )
    except KeyboardInterrupt:
        _LOGGER.debug("User signalled to stop.")
        for blind_group in blind_groups:
            blind_group.stop_watching()
        
        
    loop.close()
    print("finished.")
