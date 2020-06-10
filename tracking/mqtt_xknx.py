import asyncio
import json
import yaml
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Union
import pydantic_loader
from asyncio_mqtt import Client
from xknx import XKNX
from xknx.devices import Cover

import dummy
import config

east_blinds = []
west_blinds = []
north_blinds = []
south_blinds = []


class BlindGroup:
    """Glue class between XKNX and MQTT."""

    def __init__(self, topic, client: Client):
        self.shades=[]
        self._topic = topic
        self._client = client
        self._watch_task = None
        self._position = None
        self._angle = 0
        # print("Blind constructor called")

    def start_watching(self):
        loop = asyncio.get_running_loop()
        self._watch_task = loop.create_task(self.handle_message())

    def stop_watching(self):
        try:
            self._watch_task.cancel()
        except asyncio.CancelledError:
            print("cancelled watching task.")

    async def handle_message(self):
        """Hier stop je logica in die inkomende berichten leest en 
        vervolgens jouw knx blind aanstuurt.
        """
        print(f"Start watching: {self._topic}")

        async with self._client.filtered_messages(self._topic) as messages:
            async for message in messages:
                cmd = message.payload.decode("utf-8")
                data = json.loads(message.payload.decode("utf-8"))
                print(f"incoming data on {message.topic}")
                print(data)


def grouping(xknx:Union[XKNX,dummy.DummyXKNX],client)->List[BlindGroup]:
    group_north = BlindGroup("building/noordgevel",client)
    group_east = BlindGroup("building/oostgevel",client)
    group_south=BlindGroup("building/zuidgevel",client)
    group_west = BlindGroup("building/westgevel",client)


    for device in xknx.devices.values():
        if "East" in device.name:
            group_east.shades.append(device)
        elif "West" in device.name:
            group_west.shades.append(device)
        elif "South" in device.name:
            group_south.shades.append(device)
        elif "North" in device.name:
            group_north.shades.append(device)

    return group_north,group_east,group_south,group_west



async def start(
    xknx: Union[XKNX, dummy.DummyXKNX],
    blinds_config: "Path",
    app_config: "config.AppConfig",
):
    """Start."""

    async with Client(app_config.mqtt_address) as client:

        await client.subscribe("building/#")

        blind_groups = grouping(xknx,client)

        for blind_group in blind_groups:
            blind_group.start_watching()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            for blind in blind_groups:
                blind.stop_watching()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    parser = ArgumentParser()
    parser.add_argument(
        "xknxconfig", help="yaml config files where your blinds are configured."
    )
    parser.add_argument("--appconfig", help="App config file.", default=None)
    parser.add_argument("--demo",help="Run the app in demo mode",action="store_true")
    args = parser.parse_args()

    app_config = pydantic_loader.load_json(config.AppConfig, args.appconfig)

    xknxconfig = Path(args.xknxconfig)

    if args.demo:
        xknx = dummy.DummyXKNX(config=str(xknxconfig))
    else:
        xknx = XKNX(config=str(xknxconfig))    
    

    loop.run_until_complete(
        start(xknx, blinds_config=xknxconfig, app_config=app_config)
    )
    loop.close()
    print("finished.")
