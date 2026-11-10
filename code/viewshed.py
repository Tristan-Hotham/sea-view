"""The line-of-sight kernel (numba). Rays are marched in the Web Mercator pixel grid of the terrain mosaic, with the local
pixel size cos(latitude) * PIX0 recomputed at every step, so distances are true ground distances.

For an observer at height H (ground + eye) a sample at ground distance d and height h has apparent elevation
    a = (h - H) / d - d / (2 R'),   R' = R / (1 - k)
A sea sample (height 0) is visible when its a is at least the highest a of every sample nearer along the ray. A ray stops
at its first visible sea, at dmax, at the edge of the mosaic, or when the running maximum exceeds the highest angle that
any farther sea surface could reach (-sqrt(2H/R') before the sea horizon distance sqrt(2HR'), the sea's own angle after it).
"""
import math
import numpy as np
from numba import njit, prange

PIX0_Z9 = 2 * math.pi * 6378137.0 / (256 * 2 ** 9)


@njit(cache=False, fastmath=False)
def _bil(dem, x, y):
    i = int(math.floor(x)); j = int(math.floor(y))
    fx = x - i; fy = y - j
    return ((dem[j, i] * (1 - fx) + dem[j, i + 1] * fx) * (1 - fy) +
            (dem[j + 1, i] * (1 - fx) + dem[j + 1, i + 1] * fx) * fy)


@njit(parallel=True, cache=False)
def viewshed(dem, sea, ox, oy, gy0, ntot, pix0, eye, dmax, naz, k, step, az0, rays_out):
    """dem float32 (sea = 0), sea bool, observers at local pixel coords (ox, oy) with pixel centres on integers;
    global pixel y = oy + gy0 (gy0 includes the half-pixel shift); ntot = 256 * 2**z; pix0 = pixel size at the equator (m).
    Returns nearest visible sea (m, inf if none), number of rays with sea, number of rays leaving the mosaic, ground height.
    If rays_out has shape (n, naz) the first visible sea distance of every ray is written to it."""
    n = ox.shape[0]
    NY, NX = dem.shape
    Re = 6371000.0 / (1.0 - k)
    nearest = np.full(n, np.inf, np.float32)
    nsea = np.zeros(n, np.int16)
    noob = np.zeros(n, np.int16)
    ground = np.zeros(n, np.float32)
    keep_rays = rays_out.shape[0] == n
    for o in prange(n):
        x0 = ox[o]; y0 = oy[o]
        if x0 < 1 or y0 < 1 or x0 > NX - 3 or y0 > NY - 3:
            noob[o] = naz
            continue
        g = _bil(dem, x0, y0)
        ground[o] = g
        H = g + eye
        dstar = math.sqrt(2 * H * Re) if H > 0 else 0.0
        bmax = -math.sqrt(2 * H / Re) if H > 0 else 0.0
        best = np.inf
        cnt = 0; oob = 0
        for a in range(naz):
            az = math.radians(az0 + a * 360.0 / naz)
            sx = math.sin(az) * step; sy = -math.cos(az) * step
            x = x0; y = y0; d = 0.0
            mx = -1e9
            hit = np.inf
            while True:
                x += sx; y += sy
                yy = (y + gy0) / ntot
                mpp = pix0 / math.cosh(math.pi * (1 - 2 * yy))
                d += step * mpp
                if d > dmax:
                    break
                if x < 0 or y < 0 or x > NX - 2 or y > NY - 2:
                    oob += 1
                    break
                ix = int(x + 0.5); iy = int(y + 0.5)
                if sea[iy, ix]:
                    ang = -H / d - d / (2 * Re)
                    if ang >= mx:
                        hit = d
                        break
                else:
                    ang = (_bil(dem, x, y) - H) / d - d / (2 * Re)
                if ang > mx:
                    mx = ang
                if H > 0 and d < dstar:
                    bound = bmax
                else:
                    bound = -H / d - d / (2 * Re)
                if mx > bound:
                    break
            if keep_rays:
                rays_out[o, a] = hit
            if hit < np.inf:
                cnt += 1
                if hit < best:
                    best = hit
        nearest[o] = best
        nsea[o] = cnt
        noob[o] = oob
    return nearest, nsea, noob, ground


