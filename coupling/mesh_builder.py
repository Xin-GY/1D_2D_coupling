from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import LineString, Point, Polygon

from .config import MeshRefinementConfig


@dataclass(slots=True)
class MeshBuildResult:
    bounding_polygon: list[list[float]]
    boundary_tags: dict[str, list[int]]
    breaklines: list[list[list[float]]] = field(default_factory=list)
    interior_regions: list[tuple[list[list[float]], float]] = field(default_factory=list)
    interior_holes: list[list[list[float]]] = field(default_factory=list)
    region_pt_area: list[tuple[list[float], str, float]] = field(default_factory=list)
    lateral_exchange_regions: dict[str, list[list[float]]] = field(default_factory=dict)
    frontal_boundary_tags: dict[str, str] = field(default_factory=dict)


class RiverAwareMeshBuilder:
    def __init__(self, config: MeshRefinementConfig):
        self.config = config

    @staticmethod
    def _clip_polygon_inside(poly: Polygon, floodplain: Polygon, inset: float = 1.0e-6) -> Polygon | None:
        clipped = poly.intersection(floodplain.buffer(-inset))
        if clipped.is_empty:
            return None
        if clipped.geom_type == 'Polygon':
            return clipped
        polygons = [geom for geom in getattr(clipped, 'geoms', []) if geom.geom_type == 'Polygon']
        if not polygons:
            return None
        return max(polygons, key=lambda geom: geom.area)

    @staticmethod
    def _polygon_to_coords(poly: Polygon) -> list[list[float]]:
        coords = list(poly.exterior.coords)
        return [[float(x), float(y)] for x, y in coords[:-1]]

    @staticmethod
    def _line_to_coords(line: LineString) -> list[list[float]]:
        return [[float(x), float(y)] for x, y in line.coords]

    def _buffer_line(self, coords: list[list[float]], half_width: float) -> Polygon:
        return LineString(coords).buffer(half_width, cap_style=2, join_style=2)

    def build(
        self,
        floodplain_polygon: list[list[float]],
        centerline: list[list[float]],
        bank_lines: list[list[list[float]]] | None = None,
        levee_lines: list[list[list[float]]] | None = None,
        direct_connection_lines: dict[str, list[list[float]]] | None = None,
        lateral_links: dict[str, list[list[float]]] | None = None,
    ) -> MeshBuildResult:
        bank_lines = bank_lines or []
        levee_lines = levee_lines or []
        direct_connection_lines = direct_connection_lines or {}
        lateral_links = lateral_links or {}

        floodplain = Polygon(floodplain_polygon)
        if not floodplain.is_valid:
            raise ValueError('floodplain_polygon 不是有效多边形')
        centerline_ls = LineString(centerline)

        result = MeshBuildResult(
            bounding_polygon=self._polygon_to_coords(floodplain),
            boundary_tags={
                'bottom': [0],
                'right': [1],
                'top': [2],
                'left': [3],
            },
        )

        result.breaklines.append(self._line_to_coords(centerline_ls))
        for line in bank_lines:
            result.breaklines.append(self._line_to_coords(LineString(line)))
        for line in levee_lines:
            ls = LineString(line)
            result.breaklines.append(self._line_to_coords(ls))
            levee_poly = ls.buffer(self.config.levee_refinement_half_width, cap_style=2, join_style=2)
            result.interior_regions.append((self._polygon_to_coords(levee_poly), self.config.levee_refinement_area))

        river_corridor = self._clip_polygon_inside(
            self._buffer_line(centerline, self.config.river_refinement_half_width),
            floodplain,
        )
        if river_corridor is not None:
            result.interior_regions.append((self._polygon_to_coords(river_corridor), self.config.river_refinement_area))

        if self.config.prefer_channel_hole:
            channel_hole = self._clip_polygon_inside(
                self._buffer_line(centerline, self.config.channel_exclusion_half_width),
                floodplain,
            )
            if channel_hole is not None and floodplain.contains(Point(channel_hole.representative_point())):
                result.interior_holes.append(self._polygon_to_coords(channel_hole))

        for link_id, line in lateral_links.items():
            region_poly = self._clip_polygon_inside(self._buffer_line(line, self.config.lateral_region_half_width), floodplain)
            result.breaklines.append(self._line_to_coords(LineString(line)))
            if region_poly is None:
                raise ValueError(f'lateral link {link_id!r} 的 exchange region 不在 floodplain 内')
            region_coords = self._polygon_to_coords(region_poly)
            result.interior_regions.append((region_coords, self.config.lateral_region_area))
            result.lateral_exchange_regions[link_id] = region_coords

        for link_id, line in direct_connection_lines.items():
            ls = LineString(line)
            result.breaklines.append(self._line_to_coords(ls))
            frontal_poly = self._clip_polygon_inside(
                ls.buffer(self.config.frontal_refinement_half_width, cap_style=2, join_style=2),
                floodplain,
            )
            if frontal_poly is not None:
                result.interior_regions.append(
                    (
                        self._polygon_to_coords(frontal_poly),
                        self.config.frontal_refinement_area,
                    )
                )
            result.frontal_boundary_tags[link_id] = f'{link_id}_boundary'

        for polygon, area in result.interior_regions:
            centroid = Polygon(polygon).representative_point()
            result.region_pt_area.append(([float(centroid.x), float(centroid.y)], 'refinement', float(area)))

        return result
