"""Small planar polygon helpers. Coordinates are (latitude, longitude)."""

def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def on_segment(a, b, p):
    return (abs(cross(a, b, p)) < 1e-10
            and min(a[0], b[0])-1e-10 <= p[0] <= max(a[0], b[0])+1e-10
            and min(a[1], b[1])-1e-10 <= p[1] <= max(a[1], b[1])+1e-10)


def intersects(a, b, c, d):
    return ((cross(a,b,c)*cross(a,b,d) < 0 and cross(c,d,a)*cross(c,d,b) < 0)
            or any((on_segment(a,b,c), on_segment(a,b,d),
                    on_segment(c,d,a), on_segment(c,d,b))))


def contains(points, latitude, longitude):
    inside = False
    for a, b in zip(points, points[1:] + points[:1]):
        if on_segment(a, b, (latitude, longitude)):
            return True
        if (a[0] > latitude) != (b[0] > latitude):
            x = a[1] + (latitude-a[0])*(b[1]-a[1])/(b[0]-a[0])
            if longitude < x:
                inside = not inside
    return inside


def interior_point(points):
    # A scanline between vertex latitudes avoids tangencies. The midpoint of
    # its widest inside interval also works for concave shapes.
    levels = sorted({p[0] for p in points})
    low, high = max(zip(levels, levels[1:]), key=lambda pair: pair[1]-pair[0])
    latitude = (low + high) / 2
    crossings = sorted(a[1] + (latitude-a[0])*(b[1]-a[1])/(b[0]-a[0])
                       for a, b in zip(points, points[1:]+points[:1])
                       if (a[0] > latitude) != (b[0] > latitude))
    left, right = max(zip(crossings[::2], crossings[1::2]), key=lambda pair: pair[1]-pair[0])
    return latitude, (left + right) / 2
