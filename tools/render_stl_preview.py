#!/usr/bin/env python3

from __future__ import annotations

import math
import os
import struct
import sys
from typing import Iterable, List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter


Vec3 = Tuple[float, float, float]
Triangle = Tuple[Vec3, Vec3, Vec3]


VIEW_PRESETS = {
    "front": {"rotation": (-28.0, 18.0, -18.0), "distance": 340.0},
    "rear": {"rotation": (-24.0, -160.0, 12.0), "distance": 340.0},
}


def v_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def v_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_len(v: Vec3) -> float:
    return math.sqrt(v_dot(v, v))


def v_norm(v: Vec3) -> Vec3:
    length = v_len(v)
    if length == 0:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def rotate_x(v: Vec3, degrees: float) -> Vec3:
    radians = math.radians(degrees)
    c = math.cos(radians)
    s = math.sin(radians)
    return (v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c)


def rotate_y(v: Vec3, degrees: float) -> Vec3:
    radians = math.radians(degrees)
    c = math.cos(radians)
    s = math.sin(radians)
    return (v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c)


def rotate_z(v: Vec3, degrees: float) -> Vec3:
    radians = math.radians(degrees)
    c = math.cos(radians)
    s = math.sin(radians)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


def apply_rotation(v: Vec3, rotation: Sequence[float]) -> Vec3:
    out = rotate_x(v, rotation[0])
    out = rotate_y(out, rotation[1])
    out = rotate_z(out, rotation[2])
    return out


def remap_axes(vertex: Vec3) -> Vec3:
    # Convert model coordinates so +Y is vertical in the rendered image.
    return (vertex[0], vertex[2], vertex[1])


def load_binary_stl(path: str) -> List[Triangle]:
    triangles: List[Triangle] = []
    with open(path, "rb") as handle:
        handle.read(80)
        count = struct.unpack("<I", handle.read(4))[0]
        for _ in range(count):
            data = handle.read(50)
            if len(data) != 50:
                raise ValueError("Unexpected end of binary STL data")
            unpacked = struct.unpack("<12fH", data)
            v1 = remap_axes((unpacked[3], unpacked[4], unpacked[5]))
            v2 = remap_axes((unpacked[6], unpacked[7], unpacked[8]))
            v3 = remap_axes((unpacked[9], unpacked[10], unpacked[11]))
            triangles.append((v1, v2, v3))
    return triangles


def load_ascii_stl(path: str) -> List[Triangle]:
    triangles: List[Triangle] = []
    current: List[Vec3] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("vertex "):
                continue
            _, x_str, y_str, z_str = line.split()
            current.append(remap_axes((float(x_str), float(y_str), float(z_str))))
            if len(current) == 3:
                triangles.append((current[0], current[1], current[2]))
                current = []
    if not triangles:
        raise ValueError("No triangles found in ASCII STL")
    return triangles


def load_stl(path: str) -> List[Triangle]:
    size = os.path.getsize(path)
    with open(path, "rb") as handle:
        header = handle.read(84)
    if len(header) >= 84:
        count = struct.unpack("<I", header[80:84])[0]
        if 84 + count * 50 == size:
            return load_binary_stl(path)
    return load_ascii_stl(path)


def triangle_normal(triangle: Triangle) -> Vec3:
    a, b, c = triangle
    return v_norm(v_cross(v_sub(b, a), v_sub(c, a)))


def centered_triangles(triangles: Iterable[Triangle]) -> List[Triangle]:
    all_points = [point for triangle in triangles for point in triangle]
    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)
    min_z = min(point[2] for point in all_points)
    max_z = max(point[2] for point in all_points)
    center = (
        (min_x + max_x) / 2.0,
        (min_y + max_y) / 2.0,
        (min_z + max_z) / 2.0,
    )
    return [tuple(v_sub(point, center) for point in triangle) for triangle in triangles]


def render(
    triangles: Sequence[Triangle],
    output_path: str,
    rotation: Sequence[float],
    camera_distance: float,
    width: int = 1600,
    height: int = 1000,
) -> None:
    rotated: List[Tuple[Triangle, Vec3, float]] = []
    for triangle in triangles:
        rt = tuple(apply_rotation(point, rotation) for point in triangle)
        normal = triangle_normal(rt)
        avg_depth = sum(point[2] for point in rt) / 3.0
        rotated.append((rt, normal, avg_depth))

    all_points = [point for triangle, _, _ in rotated for point in triangle]
    max_x = max(abs(point[0]) for point in all_points)
    max_y = max(abs(point[1]) for point in all_points)
    max_extent = max(max_x, max_y)
    scale = min(width * 0.34, height * 0.42) / max_extent

    image = Image.new("RGBA", (width, height), "#f5f1eb")
    background = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(245 + (255 - 245) * t)
        g = int(241 + (255 - 241) * t)
        b = int(235 + (255 - 235) * t)
        background.line((0, y, width, y), fill=(r, g, b, 255))

    shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_bounds = (
        int(width * 0.23),
        int(height * 0.70),
        int(width * 0.77),
        int(height * 0.87),
    )
    shadow_draw.ellipse(shadow_bounds, fill=(125, 104, 85, 52))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    image.alpha_composite(shadow)

    draw = ImageDraw.Draw(image)
    light = v_norm((-0.55, 0.8, 0.65))
    base = (222, 214, 203)
    edge = (118, 104, 91, 150)

    for triangle, normal, avg_depth in sorted(rotated, key=lambda item: item[2]):
        shade = max(0.22, min(1.0, 0.42 + 0.58 * v_dot(normal, light)))
        color = tuple(int(channel * shade) for channel in base) + (255,)
        points_2d = []
        for point in triangle:
            factor = camera_distance / (camera_distance + point[2] + 60.0)
            sx = width / 2 + point[0] * scale * factor
            sy = height / 2 - point[1] * scale * factor
            points_2d.append((sx, sy))
        draw.polygon(points_2d, fill=color, outline=edge)

    image = image.filter(ImageFilter.UnsharpMask(radius=1.8, percent=130, threshold=3))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path)


def main(argv: Sequence[str]) -> int:
    if len(argv) != 4:
        sys.stderr.write(
            "Usage: render_stl_preview.py input.stl output.png <front|rear>\n"
        )
        return 1

    input_path, output_path, preset_name = argv[1], argv[2], argv[3]
    preset = VIEW_PRESETS.get(preset_name)
    if preset is None:
        sys.stderr.write("Unknown preset: %s\n" % preset_name)
        return 1

    triangles = centered_triangles(load_stl(input_path))
    render(
        triangles=triangles,
        output_path=output_path,
        rotation=preset["rotation"],
        camera_distance=preset["distance"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
