from asyncio_mqtt import Client
import asyncio
import json

topics = [
    "building/oostgevel",
    "building/zuidgevel",
    "building/westgevel",
    "building/noordgevel",
]


async def main():
    position = 100
    angle = 45
    async with Client("test.mosquitto.org") as client:
        for topic in topics:
            message = {"pos":position,"ang":angle}
            angle += 10
            print(f"topic:{topic} {message}")
            await client.publish(topic, json.dumps(message), qos=1)
            await asyncio.sleep(1)


asyncio.run(main())
