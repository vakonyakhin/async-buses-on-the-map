import json
import asyncio

import anyio
import zipfile
from httpx_ws import aconnect_ws


from fastapi.websockets import WebSocketDisconnect

BUSES = {}


async def load_routes():

    with zipfile.ZipFile('routes.zip', 'r') as zip_ref:
        for file in zip_ref.namelist():
            if file.endswith('.json'):
                route = json.loads(zip_ref.read(file))

                yield route


async def talk_to_browser(request):
    
    while True:

        message = {
            "msgType": "Buses",
            "buses": list(BUSES.values())
        }
        await request.send_text(json.dumps(message))
        print(f'message - {message}')
        await asyncio.sleep(0.1)



async def run_bus(url, bus_id, route_name, coordinates):
    try:
        async with aconnect_ws(url) as ws:
            while True:
                for lat, lng in coordinates:
                    bus_info = {
                            "busId": bus_id + '-0',
                            "lat": lat,
                            "lng": lng,
                            "route": route_name
                            }

                    await ws.send_text(json.dumps(bus_info, ensure_ascii=False))
                    await asyncio.sleep(0.1)
    except OSError as ose:
        print(f'Connection attempt failed: {ose}')
    except (OSError, anyio.EndOfStream) as e:
        print(f'Connection failed: {e}. Retrying in 5 seconds...')
    await asyncio.sleep(5)


async def main():

    url = 'ws://127.0.0.1:8000/put_bus'
    async with anyio.create_task_group() as tg:

        async for route in load_routes():
            route_name = route.get("name", "not number")
            bus_id = route_name
            coordinates = route.get("coordinates", [])
            tg.start_soon(run_bus, url, bus_id, route_name, coordinates)


if __name__ == "__main__":
    asyncio.run(main())
