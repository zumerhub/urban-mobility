[out:xml][timeout:180];

// 1. Geocode and define the area of Ikeja
{{geocodeArea:Ikeja}}->.searchArea;

// 2. Gather all nodes, ways, and relations within that area
(
  node(area.searchArea);
  way(area.searchArea);
  relation(area.searchArea);
);

// 3. Output the geometries and structure
out body;
>;
out skel qt;




================================
Use Geofabrik instead of Overpass.

Go to:

https://download.geofabrik.de/africa/nigeria.html

Download:



==========================
Option 2 (Recommended)

Use BBBike Extract Service.

Go to:

https://extract.bbbike.org/

Search

Ikeja, Lagos, Nigeria

Choose

OpenStreetMap XML (.osm)