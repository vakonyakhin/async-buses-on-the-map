import json
from fastapi import FastAPI, WebSocket

import anyio

from fake_bus import talk_to_browser, BUSES


app = FastAPI()


@app.websocket("/put_bus")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        bus_data = json.loads(data)
        BUSES[bus_data['busId']] = bus_data
        print(len(list(BUSES.values())))


@app.websocket('/ws')
async def browser_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async with anyio.create_task_group() as tg:
        tg.start_soon(talk_to_browser, websocket)
