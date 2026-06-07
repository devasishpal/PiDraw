from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ShapeType(str, Enum):
    NONE = "none"
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    DIAMOND = "diamond"
    PARALLELOGRAM = "parallelogram"
    HEXAGON = "hexagon"
    CYLINDER = "cylinder"
    DATABASE = "database"
    DOCUMENT = "document"
    DOUBLE_CIRCLE = "double_circle"
    STADIUM = "stadium"
    CLOUD = "cloud"
    ACTOR = "actor"


class EdgeStyle(str, Enum):
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    BOLD = "bold"
    INVISIBLE = "invisible"


class ArrowStyle(str, Enum):
    NONE = "none"
    TRIANGLE = "triangle"
    TRIANGLE_FILLED = "triangle_filled"
    DIAMOND = "diamond"
    DIAMOND_FILLED = "diamond_filled"
    CIRCLE = "circle"
    CIRCLE_FILLED = "circle_filled"
    OPEN = "open"
    CROW = "crow"
    BOX = "box"


class TextAlign(str, Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class FontWeight(str, Enum):
    NORMAL = "normal"
    BOLD = "bold"
    LIGHT = "light"


@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Position) -> Position:
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Position) -> Position:
        return Position(self.x - other.x, self.y - other.y)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Size:
    width: float = 0.0
    height: float = 0.0

    def as_tuple(self) -> tuple[float, float]:
        return (self.width, self.height)


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0


@dataclass
class Viewport:
    width: float = 800.0
    height: float = 600.0
    scale: float = 1.0
    x: float = 0.0
    y: float = 0.0


@dataclass
class Style:
    stroke_color: str = "#333333"
    stroke_width: float = 2.0
    stroke_style: EdgeStyle = EdgeStyle.SOLID
    fill_color: str = "#ffffff"
    fill_opacity: float = 1.0
    padding: float = 12.0
    margin: float = 0.0
    spacing: float = 20.0
    corner_radius: float = 4.0
    shadow: bool = False
    shadow_offset: float = 3.0
    shadow_color: str = "rgba(0,0,0,0.15)"
    gradient: bool = False
    gradient_start: str = ""
    gradient_end: str = ""
    font_family: str = "sans-serif"
    font_size: float = 14.0
    font_weight: FontWeight = FontWeight.NORMAL
    text_align: TextAlign = TextAlign.CENTER
    text_color: str = "#333333"
    line_height: float = 1.2
    opacity: float = 1.0
    border_style: EdgeStyle = EdgeStyle.SOLID
    arrow_start: ArrowStyle | str = ArrowStyle.NONE
    arrow_end: ArrowStyle | str = ArrowStyle.TRIANGLE_FILLED
    arrow_size: float = 10.0

    @staticmethod
    def merge(base: Optional[Style], override: Optional[Style]) -> Style:
        _defaults = Style().__dict__
        if base is None and override is None:
            return Style()
        if base is None:
            kv = {k: v for k, v in override.__dict__.items() if v != _defaults.get(k)}
            return Style(**kv) if kv else Style()
        if override is None:
            return Style(**{k: v for k, v in base.__dict__.items()})
        merged = Style(**{k: v for k, v in base.__dict__.items()})
        for k, v in override.__dict__.items():
            if v != _defaults.get(k):
                setattr(merged, k, v)
        return merged


@dataclass
class Label:
    text: str
    position: Position | None = None
    style: Style | None = None
    width: float = 0.0
    height: float = 0.0


@dataclass
class Shape:
    shape_type: ShapeType = ShapeType.RECTANGLE
    position: Position | None = None
    size: Size | None = None
    style: Style | None = None


@dataclass
class Node:
    id: str
    label: Label | None = None
    shape: Shape | None = None
    style: Style | None = None
    children: list[Node] = field(default_factory=list)
    position: Position | None = None
    size: Size | None = None
    port: str | None = None


@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: Label | None = None
    style: Style | None = None
    waypoints: list[Point] = field(default_factory=list)
    source_port: str | None = None
    target_port: str | None = None
    weight: float = 1.0


@dataclass
class Group:
    id: str
    label: Label | None = None
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    style: Style | None = None
    position: Position | None = None
    size: Size | None = None
    collapsed: bool = False


class LayoutType(str, Enum):
    TREE = "tree"
    FLOW = "flow"
    GRID = "grid"
    LAYERED = "layered"
    NONE = "none"


@dataclass
class Layout:
    layout_type: LayoutType = LayoutType.FLOW
    direction: str = "TB"
    node_spacing: float = 40.0
    layer_spacing: float = 60.0
    padding: float = 20.0


@dataclass
class Diagram:
    id: str = ""
    title: str | None = None
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    layout: Layout | None = None
    viewport: Viewport | None = None
    style: Style | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def add_group(self, group: Group) -> None:
        self.groups.append(group)

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def all_edges(self) -> list[Edge]:
        return self.edges

    def all_nodes(self) -> list[Node]:
        return list(self.nodes.values())
