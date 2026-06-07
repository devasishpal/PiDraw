from __future__ import annotations

from pidraw.core.models import Point, Position, Shape, ShapeType, Size


def compute_shape_path(
    shape_type: ShapeType,
    position: Position,
    size: Size,
    corner_radius: float = 4.0,
) -> str:
    x, y = position.x, position.y
    w, h = size.width, size.height
    r = min(corner_radius, w / 2, h / 2)
    cx, cy = x + w / 2, y + h / 2

    if shape_type == ShapeType.RECTANGLE:
        return f"M{x},{y}h{w}v{h}h{-w}z"

    if shape_type == ShapeType.ROUNDED_RECTANGLE:
        if r <= 0:
            return f"M{x},{y}h{w}v{h}h{-w}z"
        return (
            f"M{x + r},{y}"
            f"h{w - 2 * r}"
            f"a{r},{r} 0 0 1 {r},{r}"
            f"v{h - 2 * r}"
            f"a{r},{r} 0 0 1 -{r},{r}"
            f"h{-w + 2 * r}"
            f"a{r},{r} 0 0 1 -{r},-{r}"
            f"v{-h + 2 * r}"
            f"a{r},{r} 0 0 1 {r},-{r}z"
        )

    if shape_type == ShapeType.STADIUM:
        ry = h / 2
        return (
            f"M{x + ry},{y}"
            f"h{w - 2 * ry}"
            f"a{ry},{ry} 0 0 1 0,{h}"
            f"h{-w + 2 * ry}"
            f"a{ry},{ry} 0 0 1 0,-{h}z"
        )

    if shape_type == ShapeType.CIRCLE:
        r = min(w, h) / 2
        return (
            f"M{cx},{cy - r}"
            f"a{r},{r} 0 1 1 0,{2 * r}"
            f"a{r},{r} 0 1 1 0,-{2 * r}z"
        )

    if shape_type == ShapeType.DOUBLE_CIRCLE:
        r = min(w, h) / 2
        outer = (
            f"M{cx},{cy - r}"
            f"a{r},{r} 0 1 1 0,{2 * r}"
            f"a{r},{r} 0 1 1 0,-{2 * r}z"
        )
        inner_r = r * 0.75
        inner = (
            f"M{cx},{cy - inner_r}"
            f"a{inner_r},{inner_r} 0 1 1 0,{2 * inner_r}"
            f"a{inner_r},{inner_r} 0 1 1 0,-{2 * inner_r}z"
        )
        return f"{outer} {inner}"

    if shape_type == ShapeType.ELLIPSE:
        rx, ry = w / 2, h / 2
        return (
            f"M{cx},{cy - ry}"
            f"a{rx},{ry} 0 1 1 0,{2 * ry}"
            f"a{rx},{ry} 0 1 1 0,-{2 * ry}z"
        )

    if shape_type == ShapeType.DIAMOND:
        return (
            f"M{cx},{y}"
            f"L{x + w},{cy}"
            f"L{cx},{y + h}"
            f"L{x},{cy}z"
        )

    if shape_type == ShapeType.PARALLELOGRAM:
        skew = w * 0.2
        return (
            f"M{x + skew},{y}"
            f"L{x + w},{y}"
            f"L{x + w - skew},{y + h}"
            f"L{x},{y + h}z"
        )

    if shape_type == ShapeType.HEXAGON:
        sx = w * 0.25
        return (
            f"M{x + sx},{y}"
            f"L{x + w - sx},{y}"
            f"L{x + w},{cy}"
            f"L{x + w - sx},{y + h}"
            f"L{x + sx},{y + h}"
            f"L{x},{cy}z"
        )

    if shape_type == ShapeType.CYLINDER:
        ry = min(h * 0.15, w * 0.3)
        body = f"M{x},{y + ry}a{w / 2},{ry} 0 0 0 {w},0v{h - 2 * ry}a{w / 2},{ry} 0 0 1 -{w},0z"
        top = f"M{x},{y + ry}a{w / 2},{ry} 0 0 0 {w},0a{w / 2},{ry} 0 0 1 -{w},0"
        return f"{top} {body}"

    if shape_type == ShapeType.DATABASE:
        ry = min(h * 0.15, w * 0.3)
        return (
            f"M{x},{y + ry}"
            f"a{w / 2},{ry} 0 0 0 {w},0"
            f"v{h - 2 * ry}"
            f"a{w / 2},{ry} 0 0 1 -{w},0"
            f"v{-h + 2 * ry}z"
        )

    if shape_type == ShapeType.CLOUD:
        d = w * 0.2
        return (
            f"M{x + d},{y + h * 0.3}"
            f"a{d * 0.8},{d * 0.8} 0 0 1 {d * 1.6},-{d * 0.2}"
            f"a{d * 0.6},{d * 0.6} 0 0 1 {d * 1.2},{d * 0.4}"
            f"a{d * 0.7},{d * 0.7} 0 0 1 -{d * 0.3},{d * 1.2}"
            f"a{d * 0.5},{d * 0.5} 0 0 1 -{d * 1.5},{d * 0.1}"
            f"a{d * 0.6},{d * 0.6} 0 0 1 -{d * 1.0},-{d * 0.5}z"
        )

    return f"M{x},{y}h{w}v{h}h{-w}z"


def compute_shape_size(shape_type: ShapeType, label_text: str, font_size: float = 14.0) -> Size:
    if shape_type in (ShapeType.CIRCLE, ShapeType.DOUBLE_CIRCLE):
        text_len = max(len(label_text) * font_size * 0.6, 40)
        d = text_len + 40
        return Size(d, d)
    if shape_type == ShapeType.DIAMOND:
        text_len = max(len(label_text) * font_size * 0.6, 40)
        return Size(text_len + 60, text_len * 0.6 + 40)
    if shape_type == ShapeType.ACTOR:
        return Size(60, 100)
    text_width = max(len(label_text) * font_size * 0.6, 40)
    return Size(text_width + 40, font_size * 2.4 + 16)


def default_position() -> Position:
    return Position(0, 0)


def default_size() -> Size:
    return Size(120, 60)
