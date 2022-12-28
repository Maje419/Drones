import requests
import json

TECH_TYPES = {"UMTS": 7, "LTE": 29, "GSM": 39, "TK": 41, "5G-NR": 42}

BASE_URL = "https://mastedatabasen.dk/Master/antenner.json?tjeneste=2&maxantal=9999999"


if __name__ == "__main__":
    r = requests.get(
        f"{BASE_URL}&teknologier={','.join(map(str, TECH_TYPES.values()))}"
    )
    data = r.json()
    with open("mast_data.json", "w") as f:
        f.write(json.dumps(data, indent=2))
