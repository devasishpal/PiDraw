from __future__ import annotations

from pidraw.core.models import Position, ShapeType, Size
from pidraw.core.shapes import compute_shape_path, compute_shape_size


class TestComputeShapePath:
    def test_rectangle(self) -> None:
        path = compute_shape_path(ShapeType.RECTANGLE, Position(10, 20), Size(100, 50))
        assert path.startswith("M")
        assert "h100" in path
        assert "v50" in path

    def test_rounded_rectangle(self) -> None:
        path = compute_shape_path(
            ShapeType.ROUNDED_RECTANGLE, Position(0, 0), Size(100, 50), corner_radius=5
        )
        assert "a" in path

    def test_circle(self) -> None:
        path = compute_shape_path(ShapeType.CIRCLE, Position(0, 0), Size(50, 50))
        assert "a" in path

    def test_ellipse(self) -> None:
        path = compute_shape_path(ShapeType.ELLIPSE, Position(0, 0), Size(80, 40))
        assert "a" in path

    def test_diamond(self) -> None:
        path = compute_shape_path(ShapeType.DIAMOND, Position(10, 10), Size(80, 60))
        assert "L" in path
        assert "Z" in path or "z" in path

    def test_parallelogram(self) -> None:
        path = compute_shape_path(ShapeType.PARALLELOGRAM, Position(0, 0), Size(100, 50))
        assert path is not None

    def test_hexagon(self) -> None:
        path = compute_shape_path(ShapeType.HEXAGON, Position(0, 0), Size(100, 50))
        assert path is not None

    def test_cylinder(self) -> None:
        path = compute_shape_path(ShapeType.CYLINDER, Position(0, 0), Size(80, 60))
        assert "a" in path

    def test_database(self) -> None:
        path = compute_shape_path(ShapeType.DATABASE, Position(0, 0), Size(80, 60))
        assert "a" in path

    def test_stadium(self) -> None:
        path = compute_shape_path(ShapeType.STADIUM, Position(0, 0), Size(120, 50))
        assert "a" in path

    def test_double_circle(self) -> None:
        path = compute_shape_path(ShapeType.DOUBLE_CIRCLE, Position(0, 0), Size(60, 60))
        # Double circle should have a space (two paths)
        assert " " in path

    def test_cloud(self) -> None:
        path = compute_shape_path(ShapeType.CLOUD, Position(0, 0), Size(100, 80))
        assert "a" in path


class TestComputeShapeSize:
    def test_rectangle_size(self) -> None:
        size = compute_shape_size(ShapeType.RECTANGLE, "Hello", font_size=14)
        assert size.width > 40
        assert size.height > 30

    def test_circle_size(self) -> None:
        size = compute_shape_size(ShapeType.CIRCLE, "Test")
        assert size.width == size.height

    def test_diamond_size(self) -> None:
        size = compute_shape_size(ShapeType.DIAMOND, "Decision")
        assert size.width > size.height

    def test_empty_label(self) -> None:
        size = compute_shape_size(ShapeType.RECTANGLE, "")
        assert size.width >= 40
