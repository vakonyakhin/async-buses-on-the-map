from pydantic import BaseModel, Field


class BoundsData(BaseModel):
    south_lat: float
    north_lat: float
    west_lng: float
    east_lng: float


class ClientMessage(BaseModel):
    msgType: str = Field(..., pattern="^newBounds$")
    bounds: BoundsData


class BusMessage(BaseModel):
    busId: str
    lat: float
    lng: float
    route: str
