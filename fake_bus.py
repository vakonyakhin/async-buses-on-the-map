import json
import asyncio
from itertools import cycle, islice
from random import randint


import anyio
import zipfile
from httpx_ws import aconnect_ws


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
        await asyncio.sleep(1)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def run_bus(url, bus_id, route_name, coordinates):
    try:
        async with aconnect_ws(url) as ws:
            while True:
                iterator = islice(cycle(coordinates), randint(1, 50), None)
                for lat, lng in iterator:
                    bus_info = {
                            "busId": bus_id,
                            "lat": lat,
                            "lng": lng,
                            "route": route_name
                            }

                    await ws.send_text(json.dumps(bus_info, ensure_ascii=False))
                    await asyncio.sleep(1)
    except OSError as ose:
        print(f'Connection attempt failed: {ose}')
    except (OSError, anyio.EndOfStream) as e:
        print(f'Connection failed: {e}. Retrying in 5 seconds...')
    await asyncio.sleep(5)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def main():

    url = 'ws://127.0.0.1:8000/put_bus'
    async with anyio.create_task_group() as tg:

        async for route in load_routes():
            route_name = route.get("name", "not number")
            coordinates = route.get("coordinates", [])
            for _ in range(2):
                bus_id = generate_bus_id(route_name, randint(1, 1000))
                tg.start_soon(run_bus, url, bus_id, route_name, coordinates)


if __name__ == "__main__":
    asyncio.run(main())
