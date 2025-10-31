import geopandas as gpd
from shapely.geometry import LineString
import gpxpy, gpxpy.gpx
import osmnx as ox

def movement_path_to_linestring(G_proj, path):
    """
    Convert a movement path (list of (u,v,k)) into a LineString in geographic coordinates.
    G_proj should be the projected graph. We unproject coordinates before exporting.
    """
    # Unproject the graph to lat/lon (this returns a copy)
    G_unproj = ox.unproject_graph(G_proj)
    coords = []
    for (u, v, k) in path:
        # Use 'geometry' if present; otherwise, take node lon/lat
        geom = G_unproj[u][v][k].get("geometry")
        if geom is not None:
            # geometry is already in lon/lat because we unprojected
            coords.extend(list(geom.coords))
        else:
            lon1 = G_unproj.nodes[u]["x"]  # lon
            lat1 = G_unproj.nodes[u]["y"]  # lat
            lon2 = G_unproj.nodes[v]["x"]
            lat2 = G_unproj.nodes[v]["y"]
            coords.append((lon1, lat1))
            coords.append((lon2, lat2))
    # remove duplicate consecutive coords
    dedup = [coords[0]]
    for c in coords[1:]:
        if c != dedup[-1]:
            dedup.append(c)
    return LineString(dedup)

def write_geojson(lines, outfile):
    """
    lines: list of (LineString, properties)
    Write a GeoJSON with the proper WGS84 CRS.
    """
    gdf = gpd.GeoDataFrame(
        [{"geometry": ln, **props} for ln, props in lines],
        crs="EPSG:4326"
    )
    gdf.to_file(outfile, driver="GeoJSON")

def write_gpx(lines, outfile):
    """
    Write GPX with lat/lon. Assumes each LineString has lon/lat coords.
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

