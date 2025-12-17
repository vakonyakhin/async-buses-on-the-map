import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
import json

from server import app, BUSES, Bus


@pytest.fixture
def client():
    """Provides a TestClient for the FastAPI app."""
    return TestClient(app)


def test_put_bus_endpoint_success(client: TestClient):
    """
    Tests that the /put_bus endpoint can successfully receive a bus message.
    The main goal is to ensure the server processes the message without hanging.
    """
    BUSES.clear()
    with client.websocket_connect("/put_bus") as websocket:
        data = {"busId": "test_bus_1", "lat": 55.75, "lng": 37.61, "route": "test_route"}
        websocket.send_json(data)
        # The server will process this message and then wait for the next one.
        # When the 'with' block exits, the client disconnects,
        # the server's receive_json() raises WebSocketDisconnect,
        # and the 'BUSES.clear()' is called in the exception handler.
        # This test passes if this whole sequence completes without hanging.


def test_put_bus_endpoint_validation_error(client: TestClient):
    """
    Tests that the /put_bus endpoint returns a validation error for invalid data.
    """
    with client.websocket_connect("/put_bus") as websocket:
        # Data is missing the 'route' field
        data = {"busId": "test_bus_2", "lat": 55.75, "lng": 37.61}
        websocket.send_json(data)
        response = websocket.receive_json()
        assert "error" in response
        assert "ValidationError" in response["error"]


def test_browser_ws_endpoint_sends_buses(client: TestClient):
    """
    Tests that the /ws endpoint (talk_to_browser) sends bus data.
    """
    # Populate the global BUSES dictionary with some data
    BUSES.clear()
    BUSES["bus1"] = Bus(busId="bus1", lat=55.75, lng=37.61, route="A")

    with client.websocket_connect("/ws") as websocket:
        # The talk_to_browser coroutine should send the bus list immediately
        response = websocket.receive_json()
        assert response["msgType"] == "Buses"
        assert len(response["buses"]) == 1
        assert response["buses"][0]["busId"] == "bus1"


def test_browser_ws_endpoint_receives_bounds(client: TestClient):
    """
    Tests that the /ws endpoint (listen_browser) can receive window bounds.
    """
    BUSES.clear()
    BUSES["bus_inside"] = Bus(busId="bus_inside", lat=10, lng=10, route="A")
    BUSES["bus_outside"] = Bus(busId="bus_outside", lat=30, lng=30, route="B")

    with client.websocket_connect("/ws") as websocket:
        # 1. Receive initial bus list (should contain both buses)
        response = websocket.receive_json()
        assert response["msgType"] == "Buses"
        assert len(response["buses"]) == 2

        # 2. Send new window bounds to the server
        bounds_data = {
            "msgType": "newBounds",
            "bounds": {
                "south_lat": 0,
                "north_lat": 20,
                "west_lng": 0,
                "east_lng": 20,
            }
        }
        websocket.send_json(bounds_data)

        # 3. Receive the updated, filtered bus list
        # The server will send a new bus list after a 1-second sleep.
        response = websocket.receive_json()
        assert response["msgType"] == "Buses"
        assert len(response["buses"]) == 1
        assert response["buses"][0]["busId"] == "bus_inside"

def test_browser_ws_endpoint_invalid_bounds(client: TestClient):
    """
    Tests that the /ws endpoint (listen_browser) handles invalid bounds data.
    """
    with client.websocket_connect("/ws") as websocket:
        # 1. Receive initial empty bus list
        response = websocket.receive_json()
        assert response["msgType"] == "Buses"
        assert len(response["buses"]) == 0
        
        # 2. Send invalid bounds data
        invalid_bounds = {
            "msgType": "newBounds",
            "bounds": {
                # Missing north_lat, etc.
                "south_lat": 0,
            }
        }
        websocket.send_json(invalid_bounds)
        
        # 3. Check for validation error response
        response = websocket.receive_json()
        assert "Response" in response
        assert "ValidationError" in response["Response"]