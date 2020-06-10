from asyncio_mqtt import Client
import asyncio

topics = ["building/oostgevel", "building/zuidgevel", "building/westgevel", "building/noordgevel"]



async def main():
    position = 100
    angle = 45
    async with Client("localhost") as client:
        for topic in topics:
            message = "%d:%d" % (position, angle)
            angle += 10
            print(f"topic:{topic} {message}")
            await client.publish(topic, message, qos=1)
            await asyncio.sleep(1)


asyncio.run(main())
