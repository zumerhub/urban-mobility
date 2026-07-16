3. SUMO Documentation ⭐⭐⭐⭐⭐

Everything after travel demand generation follows SUMO's workflow.

Typical pipeline:

Network
      ↓
Demand
      ↓
Trips
      ↓
Routes
      ↓
Simulation

Documentation:

https://sumo.dlr.de/docs/

Especially:

Demand Generation
Random Trips
duarouter
Simulation

These are derived from the Official SUMO Documentation and established best practices for "Real-world Network Import."

When you move from a basic "import this map" project to a "research-grade" model, you have to force the software to clean up the messy, unstructured nature of OpenStreetMap (OSM) data. Here is the "Why" behind the "Magic" flags I used in your NetworkBuilder:

--roundabouts.guess: OSM data is often inconsistent in how it marks roundabouts. This flag tells SUMO, "Look for circular patterns in the geometry and automatically treat them as roundabouts." Without this, you get traffic jams at simple roundabouts because the intersections aren't linked correctly.

--tls.guess: In Nigeria, many intersections don't have properly defined traffic lights in OSM. This flag tells SUMO, "If you see traffic light indicators near an intersection, treat it as a signalized junction." It creates a realistic, albeit static, baseline to start your research from.

--geometry.remove: This is for performance. OSM data has thousands of "shape points" that aren't actually needed for traffic movement. This removes those points, keeping your simulation fast and preventing the "zig-zag" driving behavior you see in poorly imported networks.

--junctions.join: OSM data often has "fuzzy" nodes where roads meet. This flag forces SUMO to merge those nodes into a single, clean intersection. It’s essential for Ikeja’s busy, often irregular, junction designs.


