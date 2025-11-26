from fastapi import FastAPI, WebSocket
import json
import asyncio

import anyio



BUSES = {}
app = FastAPI()


@app.get("/")
async def get():
    return {"status": "ok"}


async def talk_to_browser(ws):
    while True:
        for bus in BUSES:
            message = {
                "msgType": "Buses",
                "buses":[
                    {
                        bus[1]
                        }
                ]
            }
        await ws.send_text(json.dumps(message))
        print(f'{message} sent')
        await asyncio.sleep(1)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async with anyio.create_task_group() as tg:
        tg.start_soon(talk_to_browser(websocket))
    # while True:
    #     for bus in BUSES.items():
    #         message = {
    #             "msgType": "Buses",
    #             "buses":[
                    
    #                     bus[1]
                        
    #             ]
    #         }
            
    #         await websocket.send_text(json.dumps(message))
    #         print(f'{message} sent')
    #         await asyncio.sleep(1)

    # while True:
    #     data = await websocket.receive_text()
    #     print(data)


@app.websocket("/put_bus")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        bus_data = json.loads(data)
        
        BUSES['busId'] = bus_data
        print(f'BUSES - {BUSES}')
    
        
