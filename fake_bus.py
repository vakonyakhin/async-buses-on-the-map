import trio
from sys import stderr
import json

import asyncio
from trio_websocket import open_websocket_url


async def send_bus(request):

    while True:
        try:
            with open("/home/vova/Рабочий стол/python/async-buses-on-the-map/156.json", "r", encoding="utf-8") as f:
                route_data = json.load(f)

            route_name = route_data.get("name", "156")
            coordinates = route_data.get("coordinates", [])

            for lat, lng in coordinates:
                message = {
                    #"msgType": "Buses",
                    "buses": [
                        {"busId": "c790сс", "lat": lat, "lng": lng, "route": route_name},
                    ]
                }
                await request.send_message(json.dumps(message))
                await trio.sleep(1)
        except Exception:
            # Handle potential exceptions like file not found or broken connection
            break


async def main():
    try:
        async with open_websocket_url('ws://127.0.0.1:8000/ws') as ws:
            await send_bus(ws)
            
    except OSError as ose:
        print('Connection attempt failed: %s' % ose, file=stderr)

trio.run(main)
