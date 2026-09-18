const $ = (id) => document.getElementById(id);

// ============================================================
// ELEMENTS
// ============================================================

const earth = $("earth");

const cityInput = $("city");

const countrySelect = $("country");

const searchBtn = $("searchBtn");

const errorBox = $("error");

const loading = $("loading");

// ============================================================
// ERROR
// ============================================================

function showError(message) {
  errorBox.textContent = message;

  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.textContent = "";

  errorBox.classList.add("hidden");
}

// ============================================================
// LOADING
// ============================================================

function setLoading(isLoading) {
  searchBtn.disabled = isLoading;

  searchBtn.textContent = isLoading ? "⏳ Loading..." : "🌍 Explore";
}

// ============================================================
// SET TEXT
// ============================================================

function setText(id, value) {
  $(id).textContent = value ?? "--";
}

// ============================================================
// MOVE 3D EARTH
// ============================================================

function moveEarth(lat, lon) {
  if (!earth) {
    return;
  }

  earth.center = {
    lat: Number(lat),

    lng: Number(lon),

    altitude: 500,
  };

  earth.range = 2500;

  earth.tilt = 65;

  earth.heading = 25;

  const marker = $("mapMarker");

  marker.classList.remove("hidden");

  setTimeout(() => {
    marker.classList.add("hidden");
  }, 4000);
}

// ============================================================
// PRECAUTIONS
// ============================================================

function renderPrecautions(items) {
  const container = $("precautions");

  if (!items || items.length === 0) {
    container.innerHTML = `<div class="empty">
                No specific precautions.
            </div>`;

    return;
  }

  container.innerHTML = items
    .map(
      (item) =>
        `<div class="precaution">
                        ${escapeHtml(item)}
                    </div>`,
    )
    .join("");
}

// ============================================================
// INSIGHTS
// ============================================================

function renderInsights(items) {
  const container = $("insights");

  if (!items || items.length === 0) {
    container.innerHTML = `<div class="empty">
                No special insights.
            </div>`;

    return;
  }

  container.innerHTML = items
    .map(
      (item) => `

                    <div class="insight ${escapeHtml(item.type || "")}">

                        <strong>
                            ${escapeHtml(item.title || "")}
                        </strong>

                        <span>
                            ${escapeHtml(item.message || "")}
                        </span>

                    </div>
                `,
    )
    .join("");
}

// ============================================================
// FORECAST
// ============================================================

function renderForecast(items) {
  const container = $("forecast");

  container.innerHTML = (items || [])
    .map(
      (day) => `

                    <div class="forecast-day">

                        <div class="date">
                            ${escapeHtml(day.date)}
                        </div>

                        <div class="icon">
                            ${escapeHtml(day.icon)}
                        </div>

                        <div class="main">
                            ${escapeHtml(day.main)}
                            ·
                            ${day.rain_probability}%
                            rain
                        </div>

                        <div class="temp">
                            ${day.min_temp}°
                            /
                            ${day.max_temp}°
                        </div>

                    </div>
                `,
    )
    .join("");
}

// ============================================================
// HOURLY
// ============================================================

function renderHourly(items) {
  const container = $("hourly");

  container.innerHTML = (items || [])
    .map(
      (hour) => `

                    <div class="hour">

                        <div class="time">
                            ${escapeHtml(hour.time)}
                        </div>

                        <div class="icon">
                            ${escapeHtml(hour.icon)}
                        </div>

                        <div class="temp">
                            ${hour.temperature}°
                        </div>

                        <div class="rain">
                            🌧️
                            ${hour.rain_probability}%
                        </div>

                    </div>
                `,
    )
    .join("");
}

// ============================================================
// RENDER WEATHER
// ============================================================

function renderWeather(data) {
  setText("locationName", data.city);

  setText("locationCountry", `${data.country || ""} · ${data.timezone || ""}`);

  setText("temperature", data.temperature);

  setText("feelsLike", data.feels_like);

  setText("humidity", `${data.humidity}%`);

  setText("wind", data.wind_speed);

  setText("clouds", `${data.clouds}%`);

  setText("rainChance", `${data.rain_probability}%`);

  setText("uv", data.uv_index);

  setText("visibility", data.visibility);

  $("conditionEmoji").textContent = data.condition_emoji || data.icon || "🌍";

  $("description").textContent = `${data.description} · Sunrise ${
    data.sunrise || "--"
  } · Sunset ${data.sunset || "--"}`;

  const pill = $("conditionPill");

  pill.textContent = `${data.condition_emoji || "🌎"}
         ${data.condition || data.weather_main}`;

  pill.className = `condition-pill ${data.condition_level || "neutral"}`;

  renderPrecautions(data.precautions);

  renderInsights(data.insights);

  renderForecast(data.forecast);

  renderHourly(data.hourly);

  moveEarth(data.coordinates.lat, data.coordinates.lon);
}

// ============================================================
// SEARCH WEATHER
// ============================================================

async function searchWeather(
  city = cityInput.value.trim(),
  country = countrySelect.value,
) {
  if (!city) {
    showError("Please enter a city name.");

    cityInput.focus();

    return;
  }

  clearError();

  setLoading(true);

  try {
    const response = await fetch("/weather", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        city: city,

        country_code: country,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Unable to load weather.");
    }

    renderWeather(data);
  } catch (error) {
    console.error(error);

    showError(error.message || "Unable to load weather.");
  } finally {
    setLoading(false);
  }
}

// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// ============================================================
// SEARCH BUTTON
// ============================================================

searchBtn.addEventListener("click", () => {
  searchWeather();
});

// ============================================================
// ENTER KEY
// ============================================================

cityInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    searchWeather();
  }
});

// ============================================================
// QUICK CITIES
// ============================================================

document.querySelectorAll(".quick-city").forEach((button) => {
  button.addEventListener("click", () => {
    cityInput.value = button.dataset.city;

    countrySelect.value = button.dataset.country;

    searchWeather(button.dataset.city, button.dataset.country);
  });
});

// ============================================================
// GLOBE BUTTON
// ============================================================

$("globeBtn").addEventListener("click", () => {
  if (!earth) {
    return;
  }

  earth.center = {
    lat: 20,

    lng: 0,

    altitude: 25000000,
  };

  earth.range = 25000000;

  earth.tilt = 0;

  earth.heading = 0;
});

// ============================================================
// SATELLITE
// ============================================================

$("satelliteBtn").addEventListener("click", () => {
  if (earth) {
    earth.mode = "SATELLITE";
  }
});

// ============================================================
// HYBRID
// ============================================================

$("hybridBtn").addEventListener("click", () => {
  if (earth) {
    earth.mode = "HYBRID";
  }
});

// ============================================================
// PAGE LOAD
// ============================================================

window.addEventListener("load", () => {
  setTimeout(() => {
    loading.classList.add("hide");
  }, 1000);

  setTimeout(() => {
    if (earth) {
      earth.mode = "SATELLITE";
    }
  }, 1200);

  // Initial location
  setTimeout(() => {
    searchWeather("Pune", "IN");
  }, 1500);
});
