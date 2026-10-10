"""Constants for the Omada Traffic integration."""

DOMAIN = "omada_traffic"
SIGNAL_UPDATED = f"{DOMAIN}_updated"

DEFAULT_ENV_FILE = "/run/secrets/omada.env"
DEFAULT_POLL_SECONDS = 30
DATA_DIRNAME = "omada_traffic"          # inside the HA config dir
DB_FILENAME = "traffic.db"

CONF_OMADAC_ID = "omadac_id"
CONF_SITE_ID = "site_id"
CONF_SITE_NAME = "site_name"

PANEL_URL_PATH = "traffic"
STATIC_URL_PATH = "/omada_traffic_static"

HOME_BUCKET = "Home/Shared"

# Retention (seconds)
RETAIN_MINUTES = 48 * 3600
RETAIN_FIVEMIN = 35 * 86400
SAMPLES_IN_MEMORY = 6 * 3600

# Device type mapping from Omada deviceCategory / deviceType to our type names.
TYPE_BY_CATEGORY = {
    "Mobile": "Phone",
    "Office": "PC",
    "Audio & Video": "Streaming",
    "Smart Home": "Smart home",
    "Network": "Network",
    "Others": "Other",
}
TYPE_BY_DEVICE_TYPE = {
    "Tablet": "Tablet",
    "Laptop": "Laptop",
    "Printer": "Printer",
    "Game Console": "Game console",
    "Streaming Media": "Streaming",
    "Media Player": "Streaming",
    "Voice Control": "Speaker",
    "Doorbell": "Camera",
    "Camera": "Camera",
    "TV": "TV",
    "Computer": "PC",
    "Mobile": "Phone",
}
TYPE_ORDER = [
    "Phone", "PC", "Laptop", "Tablet", "TV", "Streaming", "Speaker",
    "Game console", "Camera", "Smart home", "Printer", "Network", "Other",
]
