import json
from distance import haversine  #Returns distance in meters
from mastT import Mast
from typing import List, Tuple

def get_closest_masts(p: Tuple[float, float] = (10.573138, 55.369671), r: float = 4000, n: int = 3) -> List[Tuple[Mast, float]]:
    with open('mast_data.json', 'r') as f:
        data: List[Mast] = json.loads(f.read())
    candidates = []
    for mast in data:
        d = haversine(p, (float(mast["wgs84koordinat"]["laengde"]), float(mast["wgs84koordinat"]["bredde"])))
        if d < r:
            candidates.append((mast, d))
    
    candidates = sorted(candidates, key=lambda cand: cand[1], reverse=False)
    return candidates[:n]


if __name__ == "__main__":
    print(get_closest_masts())