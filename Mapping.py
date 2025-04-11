import osmnx as ox
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import contextily as ctx
from geopy.geocoders import Nominatim
from scipy.spatial.distance import euclidean
from shapely.geometry import Point, LineString

def getHouseholdNetwork(postcode, country="UK"):
    geolocator = Nominatim(user_agent="geo_locator")
    
    # Get coordinates of postcode
    location = geolocator.geocode(f"{postcode}, {country}", exactly_one=True)
    if not location:
        print("Postcode not found")
        return None

    lat, lon = location.latitude, location.longitude

    # Fetch buildings within a 500m radius which is a standard LDP leaflet drop
    buildings = ox.features_from_point((lat, lon), tags={'building': True}, dist=500)
    
    if buildings.empty:
        print("No buildings found in the area")
        return None

    # Extract centroids (representing households)
    buildings['centroid'] = buildings.geometry.centroid
    centroids = [(p.x, p.y) for p in buildings['centroid']]

    # Create a graph
    G = nx.Graph()
    for i, (x, y) in enumerate(centroids):
        G.add_node(i, pos=(x, y))

    # Connect nodes with all possible edges using geographic distances
    for i in range(len(centroids)):
        for j in range(i+1, len(centroids)):
            dist = euclidean(centroids[i], centroids[j])  # Euclidean distance in degrees
            G.add_edge(i, j, weight=dist)

    # Compute Minimum Spanning Tree (MST) for shortest connectivity
    mst = nx.minimum_spanning_tree(G)

    # Convert nodes to GeoDataFrame
    node_gdf = gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in centroids], crs="EPSG:4326")
    
    # Convert edges to LineStrings **Fixed**
    edge_gdf = gpd.GeoDataFrame(
        geometry=[LineString([centroids[u], centroids[v]]) for u, v in mst.edges],
        crs="EPSG:4326"
    )

    # Convert to Web Mercator projection for better plotting
    node_gdf = node_gdf.to_crs(epsg=3857)
    edge_gdf = edge_gdf.to_crs(epsg=3857)
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 10))
    buildings.to_crs(epsg=3857).plot(ax=ax, color='gray', alpha=0.4, edgecolor='black')  # Buildings
    edge_gdf.plot(ax=ax, color="blue", linewidth=1.5)  # Network
    node_gdf.plot(ax=ax, color="red", markersize=10)  # Households

    # Add basemap
    ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)

    plt.title(f"Household Network for {postcode}")

    # Save the figure
    plt.savefig(f"./Maps/{postcode}.png")

    plt.close(fig)  # Close the figure to free up memory

    print(f"Number of households in {postcode}: {len(centroids)}")
    return len(centroids)

# Example Usage
getHouseholdNetwork("CF3 1RY") 
