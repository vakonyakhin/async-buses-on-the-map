import json
import asyncio
from itertools import cycle, islice
from random import randint, choice
from functools import wraps

import wsproto
import anyio
import logging
import zipfile
from httpx_ws import aconnect_ws, WebSocketDisconnect, WebSocketNetworkError
from httpx import HTTPStatusError, ConnectError
import asyncclick as click


async def load_routes(routes_number):
    max_routes = 0
    with zipfile.ZipFile('routes.zip', 'r') as zip_ref:
        for file in zip_ref.namelist():
            if file.endswith('.json') and max_routes < routes_number:
                max_routes += 1
                route = json.loads(zip_ref.read(file))
                logging.info('Get route from zip')
                yield route


# для генерации уникального индекса каждого автобуса
def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"


async def run_bus(url, bus_id, route_name, coordinates, send_channel):
    # возможность запуска нескольких автобусов с разных стартовых точек
    iterator = islice(cycle(coordinates), randint(1, 50), None)
    for lat, lng in iterator:
        bus_info = {
            "busId": bus_id,
            "lat": lat,
            "lng": lng,
            "route": route_name
        }
        await send_channel.send(json.dumps(bus_info, ensure_ascii=False))
        logging.info('Send bus info to channel')
        await asyncio.sleep(1)


def relaunch_on_disconnect(async_function):
    """Декоратор для автоматического переподключения WebSocket."""
    @wraps(async_function)
    async def wrapper(*args, **kwargs):
        initial_delay = 5
        max_delay = 60
        delay = initial_delay
        while True:
            try:
                # Вызываем оригинальную функцию
                await async_function(*args, **kwargs)
                # Если функция завершилась без ошибок, выходим из цикла.
                logging.info("WebSocket task finished gracefully.")
                break
            except (
                    ConnectError,
                    HTTPStatusError,
                    WebSocketDisconnect,
                    WebSocketNetworkError,
                    wsproto.utilities.LocalProtocolError
                ):
                logging.error(f'Connection failed to server_address. Retrying in {delay} seconds...')
                await asyncio.sleep(delay)
                # Увеличиваем задержку для следующей попытки (экспоненциальная задержка)
                delay = min(delay * 2, max_delay)
            except Exception as e:
                logging.error(f"An unexpected error occurred in websocket task: {e}", exc_info=True)
                raise
    return wrapper


@relaunch_on_disconnect
async def send_updates(server_address, receive_channel):
    async with aconnect_ws(server_address) as ws:
        logging.debug('Open websocket connection')
        async for value in receive_channel:
            await ws.send_text(value)
            logging.info('Send updates to server')
            await asyncio.sleep(1)


@click.command()
@click.option("--server", default='ws://127.0.0.1:8000/', help="Server address")
@click.option("--routes_number", default=3, help="Number of routes")
@click.option("--buses_per_route", default=2, help="Number of buses per route")
@click.option("--websockets_number", default=3, help="Number of websockets")
@click.option("--emulator_id", default='0', help="префикс к busId на случай запуска нескольких экземпляров имитатора")
@click.option("--verbosity", default='DEBUG', help="Verbosity")
async def main(server, routes_number, buses_per_route, websockets_number, emulator_id, verbosity):
    # Устанавливаем уровень логирования для httpx_ws на WARNING или выше
    logging.getLogger("httpx_ws").setLevel(logging.WARNING)

    logging.basicConfig(filename='app.log', level=verbosity, format='%(asctime)s - %(levelname)s - %(message)s')
    url = server + 'ws'
    send_streams, receive_streams = [], []
    # Пул каналов для ограничения исходящих WebSocket соединений с сервером
    for _ in range(websockets_number):
        send_stream, receive_stream = anyio.create_memory_object_stream(max_buffer_size=10)
        send_streams.append(send_stream)
        receive_streams.append(receive_stream)

    async with anyio.create_task_group() as tg:
        for channel in receive_streams:
            tg.start_soon(send_updates, url, channel)

        async for route in load_routes(routes_number):
            route_name = route.get("name", "not number")
            coordinates = route.get("coordinates", [])
            logging.info(f'Get bus info')
            # Запускаем все автобусы из архива с разным началом маршрута для отправки в случайный канал
            for _ in range(buses_per_route):
                bus_id = generate_bus_id(emulator_id, randint(1, 1000))
                tg.start_soon(run_bus, url, bus_id, route_name, coordinates, choice(send_streams))


if __name__ == "__main__":
    asyncio.run(main())
