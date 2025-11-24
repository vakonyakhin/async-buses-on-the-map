import json
import asyncio

import anyio
import zipfile
from httpx_ws import aconnect_ws


async def load_routes():

    with zipfile.ZipFile('routes.zip', 'r') as zip_ref:
        for file in zip_ref.namelist():
            if file.endswith('.json'):
                route = json.loads(zip_ref.read(file))

                yield route


async def run_bus():
    async for route in load_routes():
        route_name = route.get("name", "not number")
        coordinates = route.get("coordinates", [])
        while True:
            for lat, lng in coordinates:
                    message = {
                        "msgType": "Buses",
                        "buses":
                                [
                                    {
                                    "busId": route_name + '-0',
                                    "lat": lat,
                                    "lng": lng,
                                    "route": route_name
                                    }
                                ]
                    }
            try:
                async with aconnect_ws('ws://127.0.0.1:8000/ws') as ws:

                    while True:
                        await ws.send_text(json.dumps(message, ensure_ascii=False))
                        await asyncio.sleep(1)
            except OSError as ose:
                print(f'Connection attempt failed: {ose}')


async def main():
    async with anyio.create_task_group() as tg:
        tg.start_soon(run_bus)


if __name__ == "__main__":
    asyncio.run(main())
