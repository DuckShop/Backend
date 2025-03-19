from sqlalchemy.orm import Session
import models
import httpx


def get_location(db: Session, location_id: int):
    return db.query(models.Location).filter(models.Location.id == location_id).first()


def get_location_by_name(db: Session, location_name: str):
    return db.query(models.Location).filter(models.Location.name == location_name).first()


async def get_locations_with_weather(db: Session, skip: int = 0, limit: int = 10):
    locations = db.query(models.Location).offset(skip).limit(limit).all()

    # Fetch weather data for each location
    location_with_weather = []
    for location in locations:
        weather_data = await get_weather(location.latitude, location.longitude)
        location_with_weather.append({
            "name": location.name,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "weather": weather_data  # Add the weather data
        })
    return location_with_weather


def create_location(db: Session, name: str, latitude: float, longitude: float):
    db_location = models.Location(
        name=name, latitude=latitude, longitude=longitude)
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


async def get_weekly_forecast(latitude: float, longitude: float):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=temperature_2m_min,temperature_2m_max&timezone=auto&current_weather=true"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

    if "daily" in data:
        daily_data = data["daily"]
        # Extract min and max temperatures for each day
        forecast = []
        for i in range(len(daily_data["temperature_2m_min"])):
            forecast.append({
                "date": daily_data["time"][i],
                "min_temperature": daily_data["temperature_2m_min"][i],
                "max_temperature": daily_data["temperature_2m_max"][i]
            })
        return forecast
    else:
        raise ValueError("Could not retrieve forecast data")


async def get_weather(latitude: float, longitude: float):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        weather_data = response.json()

    if "current_weather" in weather_data:
        current_weather = weather_data["current_weather"]
        # Current temperature in Celsius
        temperature = current_weather["temperature"]
        # Today's rainfall (mm), default to 0 if not available
        rain = current_weather.get("precipitation", 0)
        # Weather condition code (e.g., sunny, cloudy, etc.)
        weather_condition = current_weather.get("weathercode", None)

        # Return a formatted response
        return {
            "temperature": temperature,
            "rain": rain,
            "weather_condition": weather_condition
        }
    else:
        raise ValueError("Could not retrieve current weather data")


async def get_location_weather(db: Session, location_id: int):
    location = db.query(models.Location).filter(
        models.Location.id == location_id).first()
    if location:
        weather_data = await get_weather(location.latitude, location.longitude)
        return weather_data
    return None
