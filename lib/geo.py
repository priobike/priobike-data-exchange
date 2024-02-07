import math

def snap(pos_lng, pos_lat, p1_lng, p1_lat, p2_lng, p2_lat):
    """
    Calculate the nearest point on the line between p1 and p2,
    with respect to the reference point pos.
    """
    x = pos_lat
    y = pos_lng
    x1 = p1_lat
    y1 = p1_lng
    x2 = p2_lat
    y2 = p2_lng

    A = x - x1
    B = y - y1
    C = x2 - x1
    D = y2 - y1

    dot = A * C + B * D
    lenSq = C * C + D * D
    param = -1.0
    if lenSq != 0:
        param = dot / lenSq

    if param < 0:
        # Snap to point 1.
        xx = x1
        yy = y1
    elif param > 1:
        # Snap to point 2.
        xx = x2
        yy = y2
    else:
        # Snap to shortest point inbetween.
        xx = x1 + param * C
        yy = y1 + param * D
    return yy, xx

def haversine_distance(lng1, lat1, lng2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees) in meters.
    """
    # convert decimal degrees to radians
    lng1, lat1, lng2, lat2 = map(math.radians, [lng1, lat1, lng2, lat2])

    # haversine formula
    dlng = lng2 - lng1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000 
    return c * r