"""Perceptual palette check: min pairwise OKLab distance, overall and for every prefix.

Early screens, levels or chart series use the FIRST N colours, so order matters: every
prefix should be as well separated as possible. Run after every palette edit:
    python scripts/palette-check.py "#e6194b" "#3cb44b" "#4363d8" ...

Credits:
  OKLab conversion matrices: Bjorn Ottosson, "A perceptual color space for image processing",
  https://bottosson.github.io/posts/oklab/
  Example colours above: red, green and blue from Alexandr (Sasha) Trubetskoy's
  "List of 20 Simple, Distinct Colors", https://sashamaps.net/docs/resources/20-colors/
"""
import itertools
import math
import sys


def oklab(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = lin(r), lin(g), lin(b)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def closest_pair(colors):
    labs = {c: oklab(c) for c in colors}
    return min(((math.dist(labs[a], labs[b]), a, b) for a, b in itertools.combinations(colors, 2)))


def main(colors):
    if len(colors) < 2:
        sys.exit("give at least two hex colours")
    for n in range(2, len(colors) + 1):
        d, a, b = closest_pair(colors[:n])
        print(f"first {n:2d}: closest pair {a} / {b}  distance {d:.3f}")
    lightness = [round(oklab(c)[0], 2) for c in colors]
    print("lightness L per colour:", lightness)


if __name__ == "__main__":
    main(sys.argv[1:])
