import geopandas as gpd
from shapely.geometry import LineString
import gpxpy, gpxpy.gpx
import pyproj

def movement_path_to_linestring(G_proj, path):
    """
    Convert a movement path (list of (u, v, k)) into a WGS84 LineString.
    G_proj must be a projected graph with a valid CRS in G_proj.graph['crs'].
    """
    # Build a transformer from the graph's CRS to WGS84
    transformer = pyproj.Transformer.from_crs(
        G_proj.graph["crs"],
        "EPSG:4326",
        always_xy=True
    )

    coords = []
    for (u, v, k) in path:
        data = G_proj[u][v][k]
        geom = data.get("geometry")
        if geom is not None:
            # Transform each vertex of the edge geometry
            for x, y in geom.coords:
                lon, lat = transformer.transform(x, y)
                coords.append((lon, lat))
        else:
            # Fall back to node coordinates
            x1, y1 = G_proj.nodes[u]["x"], G_proj.nodes[u]["y"]
            x2, y2 = G_proj.nodes[v]["x"], G_proj.nodes[v]["y"]
            lon1, lat1 = transformer.transform(x1, y1)
            lon2, lat2 = transformer.transform(x2, y2)
            coords.append((lon1, lat1))
            coords.append((lon2, lat2))

    # Remove consecutive duplicates
    dedup = [coords[0]]
    for c in coords[1:]:
        if c != dedup[-1]:
            dedup.append(c)

    return LineString(dedup)

def write_geojson(lines, outfile):
    """
    lines: list of (LineString, properties).
    Write a GeoJSON with WGS84 coordinates.
    """
    gdf = gpd.GeoDataFrame(
        [{"geometry": ln, **props} for ln, props in lines],
        crs="EPSG:4326"
    )
    gdf.to_file(outfile, driver="GeoJSON")

def write_gpx(lines, outfile):
    """
    Write GPX with lat/lon coordinates.
    """
    gpx = gpxpy.gpx.GPX()
    for ln, props in lines:
        trk = gpxpy.gpx.GPXTrack(name=props.get("name", "route"))
        seg = gpxpy.gpx.GPXTrackSegment()
        for lon, lat in ln.coords:
            seg.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon))
        trk.segments.append(seg)
        gpx.tracks.append(trk)
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
