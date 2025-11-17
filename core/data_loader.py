import json

def load_car_specs(path="data/car_specs.json"):
    with open(path, "r") as f:
        return json.load(f)
