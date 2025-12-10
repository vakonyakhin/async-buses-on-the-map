import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import anyio


logging.basicConfig(level=logging.INFO)
app = FastAPI()
BUSES = {}


def is_inside(bounds: dict, lat, lng) -> bool:
    if not bounds:
        return True  # Если границы не установлены, показываем все автобусы
    try:
        if bounds['south_lat'] <= lat <= bounds['north_lat'] and \
             bounds['west_lng'] <= lng <= bounds['east_lng']:
            return True

    except KeyError:
        return False


@app.websocket("/put_bus")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()

        while True:
            data = await websocket.receive_text()
            bus_data = json.loads(data)
            BUSES[bus_data['busId']] = bus_data
    except WebSocketDisconnect:
        BUSES.clear()


async def talk_to_browser(ws: WebSocket, bounds_storage: dict):
    """Отправляет отфильтрованные по границам данные об автобусах в браузер."""
    while True:
        # Фильтруем автобусы перед отправкой
        visible_buses = [
            bus for bus in BUSES.values()
            if is_inside(bounds_storage["bounds"], bus.get('lat'), bus.get('lng'))
        ]
        message = {
            "msgType": "Buses",
            "buses": visible_buses
        }
        await ws.send_text(json.dumps(message))
        await anyio.sleep(1)


async def listen_browser(ws: WebSocket, bounds_storage: dict):
    """Слушает сообщения от браузера и обновляет границы видимой области."""
    async for data in ws.iter_text():
        message = json.loads(data)
        if message.get("msgType") == "newBounds":
            bounds_storage["bounds"] = message.get("data")


@app.websocket('/ws')
async def browser_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Локальное хранилище границ для этой конкретной WebSocket сессии
    bounds_storage = {"bounds": None}

    try:
        async with anyio.create_task_group() as tg:
            # Теперь мы передаем bounds_storage в качестве аргумента
            tg.start_soon(talk_to_browser, websocket, bounds_storage)
            tg.start_soon(listen_browser, websocket, bounds_storage)
    except WebSocketDisconnect:
        logging.info("Browser disconnected.")
    except anyio.get_cancelled_exc_class():
        # Это исключение возникает, когда группа задач отменяется.
        # Просто выходим, ничего дополнительно делать не нужно.
        pass
