import json
import asyncio
from itertools import cycle, islice
from random import randint, choice

import anyio
import zipfile
from httpx_ws import aconnect_ws
import asyncclick as click


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
        #print(list(BUSES.values()))
        await request.send_text(json.dumps(message))
        await asyncio.sleep(1)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def run_bus(url, bus_id, route_name, coordinates, send_channel):

    iterator = islice(cycle(coordinates), randint(1, 50), None)
    for lat, lng in iterator:
        bus_info = {
            "busId": bus_id,
            "lat": lat,
            "lng": lng,
            "route": route_name
        }
        #print(send_channel)
        await send_channel.send(json.dumps(bus_info, ensure_ascii=False))
        await asyncio.sleep(1)


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def send_updates(server_address, receive_channel):

    try:
        async with aconnect_ws(server_address) as ws:
            async for value in receive_channel:
                #print((receive_channel))
                await ws.send_text(value)
    except (OSError, anyio.EndOfStream):
        print(f'Connection failed. Retrying in 5 seconds...')
        await asyncio.sleep(5)

@click.command()
@click.option("--server", default='ws://127.0.0.1:8000/', help="Server address")
@click.option("--routes_number", default=1, help="Number of routes")
@click.option("--buses_per_route", default=20, help="Number of buses per route")
@click.option("--websockets_number", default=3, help="Number of websockets")
@click.option("--verbosity", default='DEBUG', help="Verbosity")
async def main(server, routes_number, buses_per_route, websockets_number, verbosity):

    url = server + 'put_bus'
    send_streams, receive_streams = [], []
    # Пул каналов для ограничения исходящих WebSocket соединений с сервером
    for _ in range(websockets_number):
        send_stream, receive_stream = anyio.create_memory_object_stream(max_buffer_size=10)
        send_streams.append(send_stream)
        receive_streams.append(receive_stream)

    async with anyio.create_task_group() as tg:
        for channel in receive_streams:
            tg.start_soon(send_updates, url, channel)
        async for route in load_routes():
            route_name = route.get("name", "not number")
            coordinates = route.get("coordinates", [])

            # Запускаем все автобусы из архива с разным началом маршрута для отправки в случайный канал
            for _ in range(buses_per_route):
                bus_id = generate_bus_id(route_name, randint(1, 1000))
                tg.start_soon(run_bus, url, bus_id, route_name, coordinates, choice(send_streams))


if __name__ == "__main__":
    asyncio.run(main())
