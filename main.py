from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import crud
import models
from pydantic import BaseModel
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENCAGE_API_KEY = "3bb1bcd80fc3463f981391960e885770"
OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"


class LocationCreate(BaseModel):
    name: str


def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_lat_lon_from_name(name: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(OPENCAGE_URL, params={
            'q': name,
            'key': OPENCAGE_API_KEY,
            'language': 'en'
        })
        data = response.json()

    if data['results']:
        location = data['results'][0]
        latitude = location['geometry']['lat']
        longitude = location['geometry']['lng']
        return latitude, longitude
    else:
        raise HTTPException(status_code=404, detail="Location not found")


@app.get("/locations")
async def get_locations(db: Session = Depends(get_db)):
    locations_with_weather = await crud.get_locations_with_weather(db)
    return locations_with_weather


@app.post("/locations")
async def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    existing_location = db.query(models.Location).filter(
        models.Location.name == location.name).first()

    if existing_location:
        raise HTTPException(
            status_code=400,
            detail=f"Location '{location.name}' already exists"
        )

    latitude, longitude = await get_lat_lon_from_name(location.name)

    return crud.create_location(db, location.name, latitude, longitude)


@app.delete("/locations/{location_name}")
def delete_location_by_name(location_name: str, db: Session = Depends(get_db)):
    db_location = crud.get_location_by_name(db, location_name)
    if db_location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    db.delete(db_location)
    db.commit()
    return {"message": "Location deleted"}


@app.get("/forecast/{location_name}")
async def get_forecast_by_name(location_name: str, db: Session = Depends(get_db)):
    location = db.query(models.Location).filter(
        models.Location.name == location_name).first()
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")

    forecast = await crud.get_weekly_forecast(location.latitude, location.longitude)

    return {"location": location.name, "forecast": forecast}
