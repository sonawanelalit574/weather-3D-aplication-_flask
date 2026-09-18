import os
import webbrowser
from datetime import datetime
from threading import Timer

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request


load_dotenv()

app = Flask(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")


# ============================================================
# WEATHER CODE MAPPING
# ============================================================

WEATHER_CODES = {
    0: {
        "main": "Clear",
        "description": "Clear sky",
        "icon": "☀️"
    },

    1: {
        "main": "Clear",
        "description": "Mainly clear",
        "icon": "🌤️"
    },

    2: {
        "main": "Clouds",
        "description": "Partly cloudy",
        "icon": "⛅"
    },

    3: {
        "main": "Clouds",
        "description": "Overcast",
        "icon": "☁️"
    },

    45: {
        "main": "Fog",
        "description": "Fog",
        "icon": "🌫️"
    },

    48: {
        "main": "Fog",
        "description": "Depositing rime fog",
        "icon": "🌫️"
    },

    51: {
        "main": "Drizzle",
        "description": "Light drizzle",
        "icon": "🌦️"
    },

    53: {
        "main": "Drizzle",
        "description": "Moderate drizzle",
        "icon": "🌦️"
    },

    55: {
        "main": "Drizzle",
        "description": "Dense drizzle",
        "icon": "🌧️"
    },

    56: {
        "main": "Freezing Drizzle",
        "description": "Light freezing drizzle",
        "icon": "🌧️"
    },

    57: {
        "main": "Freezing Drizzle",
        "description": "Dense freezing drizzle",
        "icon": "🌧️"
    },

    61: {
        "main": "Rain",
        "description": "Slight rain",
        "icon": "🌦️"
    },

    63: {
        "main": "Rain",
        "description": "Moderate rain",
        "icon": "🌧️"
    },

    65: {
        "main": "Heavy Rain",
        "description": "Heavy rain",
        "icon": "🌧️"
    },

    66: {
        "main": "Freezing Rain",
        "description": "Light freezing rain",
        "icon": "🌧️"
    },

    67: {
        "main": "Freezing Rain",
        "description": "Heavy freezing rain",
        "icon": "🌧️"
    },

    71: {
        "main": "Snow",
        "description": "Slight snowfall",
        "icon": "🌨️"
    },

    73: {
        "main": "Snow",
        "description": "Moderate snowfall",
        "icon": "❄️"
    },

    75: {
        "main": "Snow",
        "description": "Heavy snowfall",
        "icon": "❄️"
    },

    77: {
        "main": "Snow",
        "description": "Snow grains",
        "icon": "❄️"
    },

    80: {
        "main": "Rain",
        "description": "Slight rain showers",
        "icon": "🌦️"
    },

    81: {
        "main": "Rain",
        "description": "Moderate rain showers",
        "icon": "🌧️"
    },

    82: {
        "main": "Heavy Rain",
        "description": "Violent rain showers",
        "icon": "⛈️"
    },

    85: {
        "main": "Snow",
        "description": "Slight snow showers",
        "icon": "🌨️"
    },

    86: {
        "main": "Snow",
        "description": "Heavy snow showers",
        "icon": "❄️"
    },

    95: {
        "main": "Thunderstorm",
        "description": "Thunderstorm",
        "icon": "⛈️"
    },

    96: {
        "main": "Thunderstorm",
        "description": "Thunderstorm with slight hail",
        "icon": "⛈️"
    },

    99: {
        "main": "Thunderstorm",
        "description": "Thunderstorm with heavy hail",
        "icon": "⛈️"
    }
}


# ============================================================
# WEATHER INFORMATION
# ============================================================

def get_weather_info(code):

    try:
        code = int(code)
    except (TypeError, ValueError):
        code = -1

    return WEATHER_CODES.get(
        code,
        {
            "main": "Unknown",
            "description": "Unknown weather",
            "icon": "🌍"
        }
    )


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0):

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


# ============================================================
# CITY GEOCODING
# ============================================================

def get_city_coordinates(city, country_code=None):

    try:

        params = {
            "name": city,
            "count": 10,
            "language": "en",
            "format": "json"
        }

        response = requests.get(
            GEOCODING_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        results = response.json().get("results", [])

        if country_code and country_code != "ALL":

            filtered = [
                result
                for result in results
                if str(
                    result.get("country_code", "")
                ).upper() == country_code.upper()
            ]

            if filtered:
                results = filtered

        if not results:
            return None

        location = results[0]

        return {
            "name": location.get("name", city),
            "country": location.get("country", ""),
            "country_code": location.get("country_code", ""),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "timezone": location.get(
                "timezone",
                "auto"
            ),
            "admin1": location.get(
                "admin1",
                ""
            )
        }

    except requests.exceptions.Timeout:

        return None

    except requests.exceptions.ConnectionError:

        return None

    except requests.RequestException as error:

        print("Geocoding error:", error)

        return None

    except Exception as error:

        print("Unexpected geocoding error:", error)

        return None


# ============================================================
# WEATHER CLASSIFICATION
# ============================================================

def classify_condition(
    weather_code,
    temperature,
    rain_probability
):

    code = int(weather_code or 0)

    # Thunderstorm
    if code in (95, 96, 99):

        return (
            "Thunderstorm",
            "⛈️",
            "danger"
        )

    # Heavy rain
    if (
        code in (65, 67, 82)
        or rain_probability >= 80
    ):

        return (
            "Heavy Rain",
            "🌧️",
            "danger"
        )

    # Normal rain
    if code in (
        51,
        53,
        55,
        56,
        57,
        61,
        63,
        66,
        80,
        81
    ):

        return (
            "Rain",
            "🌦️",
            "warning"
        )

    # Snow
    if code in (
        71,
        73,
        75,
        77,
        85,
        86
    ):

        return (
            "Winter / Snow",
            "❄️",
            "info"
        )

    # Fog
    if code in (45, 48):

        return (
            "Fog",
            "🌫️",
            "warning"
        )

    # Cloud
    if code in (2, 3):

        return (
            "Cloudy",
            "☁️",
            "info"
        )

    # Temperature classification
    if temperature >= 35:

        return (
            "Summer / Very Hot",
            "☀️",
            "danger"
        )

    if temperature >= 30:

        return (
            "Summer / Warm",
            "🌞",
            "warning"
        )

    if temperature <= 15:

        return (
            "Winter / Cold",
            "❄️",
            "info"
        )

    return (
        "Pleasant",
        "🌤️",
        "success"
    )


# ============================================================
# SAFETY PRECAUTIONS
# ============================================================

def get_precautions(
    condition,
    temperature,
    uv_index,
    wind_speed
):

    precautions = []

    if "Very Hot" in condition:

        precautions.extend([
            "🧢 Wear a cap or hat.",
            "💧 Drink plenty of water.",
            "🧴 Use sunscreen.",
            "🕶️ Wear sunglasses.",
            "🌳 Avoid prolonged direct sunlight."
        ])

    elif "Warm" in condition:

        precautions.extend([
            "🧢 Consider wearing a cap.",
            "💧 Stay hydrated.",
            "👕 Wear light and breathable clothing."
        ])

    elif condition == "Heavy Rain":

        precautions.extend([
            "☂️ Carry an umbrella or raincoat.",
            "🌊 Avoid flooded roads and underpasses.",
            "🚗 Drive slowly and carefully.",
            "🥾 Wear waterproof footwear.",
            "⚠️ Monitor local weather alerts."
        ])

    elif condition == "Rain":

        precautions.extend([
            "☂️ Carry an umbrella.",
            "🚗 Drive carefully on wet roads.",
            "👟 Use footwear with good grip."
        ])

    elif condition == "Winter / Cold":

        precautions.extend([
            "🧥 Wear woolen clothes.",
            "🧣 Use warm layers.",
            "🧤 Keep your hands warm.",
            "☕ Stay warm and hydrated."
        ])

    elif condition == "Winter / Snow":

        precautions.extend([
            "🧥 Wear insulated clothing.",
            "🧤 Protect your hands and feet.",
            "🚗 Drive carefully on icy roads."
        ])

    elif condition == "Thunderstorm":

        precautions.extend([
            "🏠 Stay indoors.",
            "⚡ Avoid exposed outdoor areas.",
            "🌳 Do not shelter under isolated trees.",
            "🚗 Avoid unnecessary travel."
        ])

    elif condition == "Fog":

        precautions.extend([
            "🚗 Drive slowly.",
            "💡 Use appropriate headlights.",
            "⚠️ Keep extra distance from vehicles."
        ])

    elif condition == "Cloudy":

        precautions.extend([
            "☁️ Weather may change quickly.",
            "☂️ Consider carrying an umbrella.",
            "🧥 Carry a light layer."
        ])

    else:

        precautions.extend([
            "🌤️ Enjoy the weather responsibly.",
            "💧 Stay hydrated."
        ])

    # UV
    if uv_index >= 8:

        precautions.append(
            "🧴 Very high UV: use sunscreen and seek shade."
        )

    elif uv_index >= 5:

        precautions.append(
            "🕶️ Consider sun protection outdoors."
        )

    # Wind
    if wind_speed >= 40:

        precautions.append(
            "💨 Strong winds: take extra care outdoors."
        )

    return precautions[:8]


# ============================================================
# WEATHER INSIGHTS
# ============================================================

def generate_insights(current, daily):

    insights = []

    temperature = current.get(
        "temperature",
        0
    )

    humidity = current.get(
        "humidity",
        0
    )

    wind_speed = current.get(
        "wind_speed",
        0
    )

    rain_probability = current.get(
        "rain_probability",
        0
    )

    uv_index = current.get(
        "uv_index",
        0
    )

    visibility = current.get(
        "visibility",
        0
    )

    weather_main = current.get(
        "weather_main",
        ""
    )

    # Temperature
    if temperature >= 35:

        insights.append({
            "type": "warning",
            "title": "Very hot",
            "message":
                "Stay hydrated and avoid prolonged direct sunlight."
        })

    elif temperature >= 30:

        insights.append({
            "type": "info",
            "title": "Warm weather",
            "message":
                "Light clothing and regular hydration are recommended."
        })

    elif temperature <= 10:

        insights.append({
            "type": "info",
            "title": "Cold weather",
            "message":
                "Warm clothing is recommended."
        })

    else:

        insights.append({
            "type": "success",
            "title": "Comfortable temperature",
            "message":
                "The current temperature is relatively comfortable."
        })

    # Rain
    if rain_probability >= 70:

        insights.append({
            "type": "warning",
            "title": "High rain chance",
            "message":
                f"There is a {rain_probability}% chance of precipitation."
        })

    elif rain_probability >= 40:

        insights.append({
            "type": "info",
            "title": "Possible rain",
            "message":
                f"Rain is possible with approximately {rain_probability}% probability."
        })

    # Humidity
    if humidity >= 80:

        insights.append({
            "type": "info",
            "title": "High humidity",
            "message":
                "High humidity may make the air feel warmer."
        })

    elif humidity <= 30:

        insights.append({
            "type": "info",
            "title": "Dry air",
            "message":
                "Humidity is low. Stay hydrated."
        })

    # Wind
    if wind_speed >= 40:

        insights.append({
            "type": "warning",
            "title": "Strong winds",
            "message":
                "Strong winds are present. Take care outdoors."
        })

    elif wind_speed >= 25:

        insights.append({
            "type": "info",
            "title": "Windy",
            "message":
                "Moderately strong winds are present."
        })

    # UV
    if uv_index >= 8:

        insights.append({
            "type": "warning",
            "title": "Very high UV",
            "message":
                "Use sunscreen, sunglasses and shade."
        })

    elif uv_index >= 5:

        insights.append({
            "type": "info",
            "title": "Moderate UV",
            "message":
                "Consider sun protection outdoors."
        })

    # Visibility
    if visibility < 2:

        insights.append({
            "type": "warning",
            "title": "Low visibility",
            "message":
                "Exercise extra caution while driving."
        })

    # Thunderstorm
    if weather_main == "Thunderstorm":

        insights.append({
            "type": "warning",
            "title": "Thunderstorm",
            "message":
                "Avoid exposed outdoor areas."
        })

    elif weather_main in (
        "Rain",
        "Heavy Rain"
    ):

        insights.append({
            "type": "info",
            "title": "Rain conditions",
            "message":
                "Wet conditions are present."
        })

    # Tomorrow trend
    if len(daily) >= 2:

        difference = (
            daily[1]["max_temp"]
            - daily[0]["max_temp"]
        )

        if difference >= 3:

            insights.append({
                "type": "info",
                "title": "Warming trend",
                "message":
                    "Tomorrow is expected to be warmer."
            })

        elif difference <= -3:

            insights.append({
                "type": "info",
                "title": "Cooling trend",
                "message":
                    "Tomorrow is expected to be cooler."
            })

    return insights


# ============================================================
# WEATHER BY COORDINATES
# ============================================================

def get_weather_by_coordinates(
    latitude,
    longitude,
    city_name="Your Location",
    country=""
):

    try:

        params = {

            "latitude": latitude,

            "longitude": longitude,

            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "rain",
                "showers",
                "snowfall",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "surface_pressure",
                "wind_speed_10m",
                "wind_direction_10m"
            ]),

            "hourly": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "precipitation_probability",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "visibility",
                "wind_speed_10m",
                "wind_direction_10m"
            ]),

            "daily": ",".join([
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "sunrise",
                "sunset",
                "uv_index_max",
                "precipitation_probability_max",
                "precipitation_sum"
            ]),

            "forecast_days": 7,

            "timezone": "auto"
        }

        response = requests.get(
            FORECAST_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        current = data.get(
            "current",
            {}
        )

        hourly_data = data.get(
            "hourly",
            {}
        )

        daily_data = data.get(
            "daily",
            {}
        )

        # ----------------------------------------------------
        # CURRENT WEATHER
        # ----------------------------------------------------

        weather_code = current.get(
            "weather_code",
            0
        )

        weather_info = get_weather_info(
            weather_code
        )

        temperature = round(
            safe_float(
                current.get(
                    "temperature_2m"
                )
            ),
            1
        )

        feels_like = round(
            safe_float(
                current.get(
                    "apparent_temperature"
                ),
                temperature
            ),
            1
        )

        humidity = int(
            safe_float(
                current.get(
                    "relative_humidity_2m"
                )
            )
        )

        wind_speed = round(
            safe_float(
                current.get(
                    "wind_speed_10m"
                )
            ),
            1
        )

        wind_direction = round(
            safe_float(
                current.get(
                    "wind_direction_10m"
                )
            ),
            0
        )

        clouds = int(
            safe_float(
                current.get(
                    "cloud_cover"
                )
            )
        )

        pressure = round(
            safe_float(
                current.get(
                    "pressure_msl"
                )
            ),
            1
        )

        # ----------------------------------------------------
        # CURRENT HOURLY INDEX
        # ----------------------------------------------------

        hourly_times = hourly_data.get(
            "time",
            []
        )

        current_time = current.get(
            "time",
            ""
        )

        if current_time in hourly_times:

            current_index = hourly_times.index(
                current_time
            )

        else:

            current_index = 0

        # ----------------------------------------------------
        # VISIBILITY
        # ----------------------------------------------------

        visibility_values = hourly_data.get(
            "visibility",
            []
        )

        if visibility_values:

            visibility_index = min(
                current_index,
                len(visibility_values) - 1
            )

            visibility = round(
                safe_float(
                    visibility_values[
                        visibility_index
                    ]
                ) / 1000,
                1
            )

        else:

            visibility = 10

        # ----------------------------------------------------
        # RAIN PROBABILITY
        # ----------------------------------------------------

        rain_values = hourly_data.get(
            "precipitation_probability",
            []
        )

        if rain_values:

            rain_index = min(
                current_index,
                len(rain_values) - 1
            )

            rain_probability = int(
                safe_float(
                    rain_values[
                        rain_index
                    ]
                )
            )

        else:

            rain_probability = 0

        # ----------------------------------------------------
        # DAILY FORECAST ARRAYS
        # ----------------------------------------------------

        daily_times = daily_data.get(
            "time",
            []
        )

        daily_codes = daily_data.get(
            "weather_code",
            []
        )

        daily_max = daily_data.get(
            "temperature_2m_max",
            []
        )

        daily_min = daily_data.get(
            "temperature_2m_min",
            []
        )

        daily_uv = daily_data.get(
            "uv_index_max",
            []
        )

        daily_rain_probability = daily_data.get(
            "precipitation_probability_max",
            []
        )

        daily_rain = daily_data.get(
            "precipitation_sum",
            []
        )

        daily_sunrise = daily_data.get(
            "sunrise",
            []
        )

        daily_sunset = daily_data.get(
            "sunset",
            []
        )

        # ----------------------------------------------------
        # 7 DAY FORECAST
        # ----------------------------------------------------

        forecast_days = []

        for i in range(
            min(7, len(daily_times))
        ):

            code = (
                daily_codes[i]
                if i < len(daily_codes)
                else 0
            )

            info = get_weather_info(
                code
            )

            date_object = datetime.strptime(
                daily_times[i],
                "%Y-%m-%d"
            )

            sunrise = ""

            sunset = ""

            if i < len(daily_sunrise):

                sunrise = datetime.fromisoformat(
                    daily_sunrise[i]
                ).strftime("%H:%M")

            if i < len(daily_sunset):

                sunset = datetime.fromisoformat(
                    daily_sunset[i]
                ).strftime("%H:%M")

            forecast_days.append({

                "date":
                    date_object.strftime(
                        "%a, %d %b"
                    ),

                "full_date":
                    daily_times[i],

                "min_temp":
                    round(
                        safe_float(
                            daily_min[i]
                        ),
                        1
                    )
                    if i < len(daily_min)
                    else temperature,

                "max_temp":
                    round(
                        safe_float(
                            daily_max[i]
                        ),
                        1
                    )
                    if i < len(daily_max)
                    else temperature,

                "description":
                    info["description"],

                "main":
                    info["main"],

                "icon":
                    info["icon"],

                "weather_code":
                    code,

                "rain_probability":
                    int(
                        safe_float(
                            daily_rain_probability[i]
                        )
                    )
                    if i < len(
                        daily_rain_probability
                    )
                    else 0,

                "precipitation":
                    round(
                        safe_float(
                            daily_rain[i]
                        ),
                        1
                    )
                    if i < len(daily_rain)
                    else 0,

                "uv_index":
                    round(
                        safe_float(
                            daily_uv[i]
                        ),
                        1
                    )
                    if i < len(daily_uv)
                    else 0,

                "sunrise":
                    sunrise,

                "sunset":
                    sunset
            })

        # ----------------------------------------------------
        # HOURLY FORECAST
        # ----------------------------------------------------

        hourly = []

        temperatures = hourly_data.get(
            "temperature_2m",
            []
        )

        feels = hourly_data.get(
            "apparent_temperature",
            []
        )

        humidities = hourly_data.get(
            "relative_humidity_2m",
            []
        )

        codes = hourly_data.get(
            "weather_code",
            []
        )

        winds = hourly_data.get(
            "wind_speed_10m",
            []
        )

        rains = hourly_data.get(
            "precipitation_probability",
            []
        )

        hourly_clouds = hourly_data.get(
            "cloud_cover",
            []
        )

        end = min(
            current_index + 24,
            len(hourly_times)
        )

        for i in range(
            current_index,
            end
        ):

            info = get_weather_info(
                codes[i]
            )

            hourly.append({

                "time":
                    datetime.fromisoformat(
                        hourly_times[i]
                    ).strftime("%H:%M"),

                "date":
                    hourly_times[i],

                "temperature":
                    round(
                        safe_float(
                            temperatures[i]
                        ),
                        1
                    ),

                "feels_like":
                    round(
                        safe_float(
                            feels[i]
                        ),
                        1
                    ),

                "humidity":
                    int(
                        safe_float(
                            humidities[i]
                        )
                    ),

                "wind":
                    round(
                        safe_float(
                            winds[i]
                        ),
                        1
                    ),

                "rain_probability":
                    int(
                        safe_float(
                            rains[i]
                        )
                    )
                    if i < len(rains)
                    else 0,

                "clouds":
                    int(
                        safe_float(
                            hourly_clouds[i]
                        )
                    )
                    if i < len(hourly_clouds)
                    else 0,

                "icon":
                    info["icon"],

                "description":
                    info["description"],

                "main":
                    info["main"],

                "weather_code":
                    codes[i]
            })

        # ----------------------------------------------------
        # SUN
        # ----------------------------------------------------

        sunrise = ""

        sunset = ""

        if daily_sunrise:

            sunrise = datetime.fromisoformat(
                daily_sunrise[0]
            ).strftime("%H:%M")

        if daily_sunset:

            sunset = datetime.fromisoformat(
                daily_sunset[0]
            ).strftime("%H:%M")

        # ----------------------------------------------------
        # UV
        # ----------------------------------------------------

        uv_index = (

            round(
                safe_float(
                    daily_uv[0]
                ),
                1
            )

            if daily_uv

            else 0
        )

        # ----------------------------------------------------
        # CONDITION
        # ----------------------------------------------------

        condition, condition_emoji, condition_level = (
            classify_condition(
                weather_code,
                temperature,
                rain_probability
            )
        )

        # ----------------------------------------------------
        # CURRENT OBJECT
        # ----------------------------------------------------

        current_object = {

            "temperature":
                temperature,

            "feels_like":
                feels_like,

            "humidity":
                humidity,

            "wind_speed":
                wind_speed,

            "visibility":
                visibility,

            "rain_probability":
                rain_probability,

            "uv_index":
                uv_index,

            "weather_main":
                weather_info["main"]
        }

        precautions = get_precautions(
            condition,
            temperature,
            uv_index,
            wind_speed
        )

        insights = generate_insights(
            current_object,
            forecast_days
        )

        # ----------------------------------------------------
        # FINAL JSON
        # ----------------------------------------------------

        return {

            "success": True,

            "city":
                city_name,

            "country":
                country,

            "coordinates": {

                "lat":
                    latitude,

                "lon":
                    longitude
            },

            "temperature":
                temperature,

            "feels_like":
                feels_like,

            "temp_min":
                forecast_days[0]["min_temp"]
                if forecast_days
                else temperature,

            "temp_max":
                forecast_days[0]["max_temp"]
                if forecast_days
                else temperature,

            "humidity":
                humidity,

            "pressure":
                pressure,

            "visibility":
                visibility,

            "wind_speed":
                wind_speed,

            "wind_direction":
                wind_direction,

            "clouds":
                clouds,

            "rain_probability":
                rain_probability,

            "uv_index":
                uv_index,

            "precipitation":
                forecast_days[0]["precipitation"]
                if forecast_days
                else 0,

            "description":
                weather_info["description"],

            "weather_main":
                weather_info["main"],

            "icon":
                weather_info["icon"],

            "weather_code":
                weather_code,

            "condition":
                condition,

            "condition_emoji":
                condition_emoji,

            "condition_level":
                condition_level,

            "precautions":
                precautions,

            "sunrise":
                sunrise,

            "sunset":
                sunset,

            "forecast":
                forecast_days,

            "hourly":
                hourly,

            "insights":
                insights,

            "timezone":
                data.get(
                    "timezone",
                    ""
                )
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "error":
                "Weather service timed out. Try again."
        }

    except requests.exceptions.ConnectionError:

        return {
            "success": False,
            "error":
                "Internet connection problem."
        }

    except requests.RequestException as error:

        print(
            "Open-Meteo error:",
            error
        )

        return {
            "success": False,
            "error":
                "Unable to load weather data."
        }

    except Exception as error:

        print(
            "Weather processing error:",
            error
        )

        return {
            "success": False,
            "error":
                "Something went wrong while loading weather."
        }


# ============================================================
# WEATHER BY CITY
# ============================================================

def get_weather(
    city,
    country_code=None
):

    location = get_city_coordinates(
        city,
        country_code
    )

    if not location:

        return {
            "success": False,
            "error":
                f"City '{city}' was not found."
        }

    return get_weather_by_coordinates(

        location["latitude"],

        location["longitude"],

        location["name"],

        location["country"]
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(

        "index.html",

        google_maps_api_key=
            GOOGLE_MAPS_API_KEY
    )


# ============================================================
# CITY WEATHER API
# ============================================================

@app.route(
    "/weather",
    methods=["POST"]
)
def weather():

    data = request.get_json(
        silent=True
    ) or {}

    city = str(
        data.get(
            "city",
            ""
        )
    ).strip()

    country_code = str(
        data.get(
            "country_code",
            "ALL"
        )
    ).strip()

    if not city:

        return jsonify({

            "success": False,

            "error":
                "Please enter a city name."
        }), 400

    result = get_weather(
        city,
        country_code
    )

    return jsonify(result)


# ============================================================
# COORDINATE WEATHER API
# ============================================================

@app.route(
    "/weather/location",
    methods=["POST"]
)
def weather_location():

    data = request.get_json(
        silent=True
    ) or {}

    latitude = data.get("lat")

    longitude = data.get("lon")

    if latitude is None or longitude is None:

        return jsonify({

            "success": False,

            "error":
                "Latitude and longitude are required."
        }), 400

    try:

        latitude = float(latitude)

        longitude = float(longitude)

    except (TypeError, ValueError):

        return jsonify({

            "success": False,

            "error":
                "Invalid coordinates."
        }), 400

    result = get_weather_by_coordinates(

        latitude,

        longitude
    )

    return jsonify(result)


# ============================================================
# OPEN BROWSER
# ============================================================

def open_browser():

    webbrowser.open_new(
        "http://127.0.0.1:5000/"
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("🌍 3D WEATHER EARTH")
    print("=" * 70)
    print("Weather API : Open-Meteo")
    print("3D Earth    : Google Maps Platform")
    print("URL         : http://127.0.0.1:5000/")
    print("=" * 70)
    print()

    Timer(
        1,
        open_browser
    ).start()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )