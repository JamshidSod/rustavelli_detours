import geopandas as gpd
from shapely.geometry import LineString
import gpxpy, gpxpy.gpx


def movement_path_to_linestring(G, path):
    coords = []
    for (u, v, k) in path:
        geom = G[u][v][k].get("geometry")
        if geom is not None:
            coords.extend(list(geom.coords))
        else:
            coords.append((G.nodes[u]["x"], G.nodes[u]["y"]))
            coords.append((G.nodes[v]["x"], G.nodes[v]["y"]))
    # collapse consecutive duplicates
    _c = [coords[0]]
    for c in coords[1:]:
        if c != _c[-1]:
            _c.append(c)
    return LineString(_c)


def write_geojson(lines, outfile, crs="EPSG:4326"):
    gdf = gpd.GeoDataFrame([{"geometry": ln, **props} for ln, props in lines], geometry="geometry", crs=crs)
    gdf.to_file(outfile, driver="GeoJSON")


def write_gpx(lines, outfile):
    gpx = gpxpy.gpx.GPX()
    for ln, props in lines:
        trk = gpxpy.gpx.GPXTrack(name=props.get("name", "route"))
        seg = gpxpy.gpx.GPXTrackSegment()
        for x, y in ln.coords:
            seg.points.append(gpxpy.gpx.GPXTrackPoint(y, x))
        trk.segments.append(seg)
        gpx.tracks.append(trk)
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
