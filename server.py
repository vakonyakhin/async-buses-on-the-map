import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict

import anyio

@dataclass
class WindowBounds:
    south_lat: float
    north_lat: float
    west_lng: float
    east_lng: float

    def is_inside(self, lat, lng) -> bool:
        if not self:
            return True  # Если границы не установлены, показываем все автобусы
        try:
            if self.south_lat <= lat <= self.north_lat and \
                self.west_lng <= lng <= self.east_lng:
                    return True

        except KeyError:
            return False

    def update(self, bounds_storage: dict):

        bounds_storage["bounds"] = self


@dataclass
class Bus():
    busId: str
    lat: float
    lng: float
    route: str


logging.basicConfig(level=logging.INFO)
app = FastAPI()
BUSES = {}


@app.websocket("/put_bus")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()

        while True:
            data = await websocket.receive_text()
            bus_data = Bus(**json.loads(data))
            BUSES[bus_data.busId] = bus_data
    except WebSocketDisconnect:
        BUSES.clear()


async def talk_to_browser(ws: WebSocket, bounds_storage: dict):
    """Отправляет отфильтрованные по границам данные об автобусах в браузер."""
    while True:
        bounds = bounds_storage.get("bounds")

        # Фильтруем автобусы перед отправкой
        visible_buses = [
            asdict(bus) for bus in BUSES.values()
            if bounds is None or bounds.is_inside(bus.lat, bus.lng)
        ]
        message = {
            "msgType": "Buses",
            "buses": visible_buses
        }
        await ws.send_json(message)
        await anyio.sleep(1)


async def listen_browser(ws: WebSocket, bounds_storage: dict):
    """Слушает сообщения от браузера и обновляет границы видимой области."""
    async for data in ws.iter_text():
        message = json.loads(data)
        if message.get("msgType") == "newBounds":
            window_bounds = WindowBounds(**message.get("data"))
            window_bounds.update(bounds_storage)


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
