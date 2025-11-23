from fastapi import FastAPI, WebSocket


app = FastAPI()


@app.get("/")
async def get():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        print(data)
