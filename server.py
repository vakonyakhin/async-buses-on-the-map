import trio
from trio_websocket import serve_websocket, ConnectionClosed


async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            print(message)
            #await ws.send_message(f'Your message is - {message}')
        except ConnectionClosed:
            break

async def main():
    # The client connects to '/', so we specify that path here.
    await serve_websocket(echo_server, '127.0.0.1', 8000, ssl_context=None)

trio.run(main)