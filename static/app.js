let lastPosition = null;

function setStatus(message, type) {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = message || "";
  el.className = "status " + (type || "");
}

function fetchLocation() {
  if (!navigator.geolocation) {
    setStatus("Geolocation not supported.", "error");
    return;
  }

  setStatus("Getting your location…");

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      lastPosition = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
      };
      setStatus("Location ready ✔️", "ok");
    },
    () => {
      lastPosition = null;
      setStatus("Could not get location.", "error");
    },
    {
      enableHighAccuracy: true,
      timeout: 8000,
      maximumAge: 60000,
    }
  );
}

async function sendLog() {
  const button = document.getElementById("logButton");
  button.disabled = true;

  const payload = {
    latitude: lastPosition ? lastPosition.latitude : null,
    longitude: lastPosition ? lastPosition.longitude : null,
  };

  try {
    const resp = await fetch("/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await resp.json();
    if (data.success) {
      setStatus("Logged! 🎧", "ok");
    } else {
      setStatus("Error logging.", "error");
    }
  } catch (err) {
    setStatus("Server unreachable.", "error");
  } finally {
    button.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const logButton = document.getElementById("logButton");
  const viewLogButton = document.getElementById("viewLogButton");
  const retryLocationButton = document.getElementById("retryLocationButton");

  if (logButton) logButton.addEventListener("click", sendLog);
  if (viewLogButton) viewLogButton.addEventListener("click", () => (window.location = "/logs"));
  if (retryLocationButton) retryLocationButton.addEventListener("click", fetchLocation);

  fetchLocation();
});
