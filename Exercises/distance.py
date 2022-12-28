from math import sin, sqrt, asin, cos, radians


def distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def haversine(p1, p2):
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees)
    https://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    """
    lon1 = p1[1]
    lat1 = p1[0]
    lon2 = p2[1]
    lat2 = p2[0]
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = (
        6371 * 1000
    )  # Radius of earth in meters. Use 3956 for miles. Determines return value units.
    return c * r
