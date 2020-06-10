from asyncio_mqtt import Client
from xknx import XKNX
from argparse import ArgumentParser
from xknx.devices import Cover
from tracking import config
import pydantic_loader
import asyncio
import re

east_blinds  = []
west_blinds  = []
north_blinds = []
south_blinds = []

blind_group = {
    "oost":  east_blinds,
    "west":  west_blinds,
    "noord": north_blinds,
    "zuid":  south_blinds
}


class DummyXKNX:
    """Dummy xknx cover device."""

    def __init__(self, id, position = 0, angle = 0):
        self._id = id
        self._position = position
        self._angle = angle

    async def set_up(self):
        self._position = 0
        print("%s went up!" % (self._id))

    async def set_down(self):
        self._position = 100
        print("%s went down" % (self._id))

    async def set_angle(self, angle):
        self._angle = angle
        print("%s angle set to: %d" % (self._id, angle))

    async def set_position(self, position):
        self._position = position
        print("%s position set to: %d" % (self._id, position))



class Blind:
    """Glue class between XKNX and MQTT."""

    def __init__(self, xknx_cover, topic, client: Client):
        self._xknx_cover = xknx_cover
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
                cmd = message.payload.decode()
                print(f"{cmd}")
                p = re.compile(r'(\d+):(\d+)')
                m = p.match(cmd)
                pos = int(m.group(1))
                ang = int(m.group(2))
                if ang != self._angle:
                    print("ang %d prev_ang %d" % (ang, self._angle))
                    self._angle = ang
                else:
                    print("same angle")

                print("pos %d ang %d" % (pos, ang))
                print("topic: %s" % (self._topic))
                p = re.compile(r'building/(\w+)gevel')
                m = p.match(self._topic)
                gevel = m.group(1)
                print("gevel: %s" % (gevel))
                # await asyncio.gather(*[blind._xknx_cover.set_angle(ang) for blind in blind_group[gevel]])
                await self._xknx_cover.set_angle(ang)

                
                print(
                    f'[topic_filter="{self._topic}"]: {cmd}'
                )
                # await self._xknx_cover.open()


async def start(xknx_devices,blinds_config:"Path",app_config:"config.AppConfig"):  
    
    xknx = XKNX(config=str(blinds_config))

    async with Client(app_config.mqtt_address) as client:
        
        await client.subscribe("building/#")

        for device in xknx.devices:

            xknx_devices[device.name] = DummyXKNX(device.name, 0, 0)
            if "East" in device.name:
                east_blinds.append(
                    Blind(xknx_devices[device.name], "building/oostgevel", client)
                )
            elif "South" in device.name:
                south_blinds.append(
                    Blind(xknx_devices[device.name], "building/zuidgevel", client)
                )
            elif "West" in device.name:
                west_blinds.append(
                    Blind(xknx_devices[device.name], "building/westgevel", client)
                )
            elif "North" in device.name:
                north_blinds.append(
                    Blind(xknx_devices[device.name], "building/noordgevel", client)
                )
            else:
                print("Invalid orientation in device.name!")

            
        
        for blind in east_blinds + west_blinds + north_blinds + south_blinds:
            blind.start_watching()
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            for blind in east_blinds + west_blinds + north_blinds + south_blinds:
                blind.stop_watching()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("xknxconfig",help="yaml config files where your blinds are configured.")
    parser.add_argument("--appconfig",help="App config file.",default=None)
    args = parser.parse_args()

    app_config = pydantic_loader.load_json(config.AppConfig,args.appconfig)

    xknxconfig= Path(args.xknxconfig)

    loop = asyncio.get_event_loop()

    dummy_xknx_devices = {
        #"shutter_1": DummyXKNX(),
        #"shutter_2": DummyXKNX(),
        #"shutter_3": DummyXKNX(),
        #"shutter_4": DummyXKNX(),
    }

    loop.run_until_complete(start(dummy_xknx_devices,blinds_config=xknxconfig ,app_config=app_config))
    loop.close()
    print("finished.")
