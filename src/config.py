from pathlib import Path

# Study area — you can later swap for a bbox/polygon
PLACE = "Tashkent, Uzbekistan"

# Corridor name aliases for Shota Rustavelli (add more spellings as needed)
CORRIDOR_NAME_ALIASES = {
    "shota rustavelli street",
    "shota rustaveli ko'chasi",
    "shota rustavelli ko'chasi",
    "ул. шота руставели",  # if present
}

# Angle thresholds (degrees)
THROUGH_MAX = 30           # |delta| <= 30° -> through
UTURN_MIN = 150            # |delta| > 150° -> uturn
RIGHT_LEFT_MIN = 30        # otherwise -> left/right by sign

# Perpendicular crossing tolerance (for ~90° rule at corridor)
PERP_TOL = 20              # | |delta| - 90 | <= PERP_TOL

# Turn delay (seconds) — replace with HCM/field values as needed
TURN_DELAY_S = 5

# I/O
DATA_DIR = Path("data")
INPUTS = DATA_DIR / "inputs"
OUTPUTS = DATA_DIR / "outputs"
ROUTES_DIR = OUTPUTS / "routes"
SUMMARIES_DIR = OUTPUTS / "summaries"
MAPS_DIR = OUTPUTS / "maps"
