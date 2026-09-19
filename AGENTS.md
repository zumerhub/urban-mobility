# Urban Mobility AI Project

## Project Objective

This is a research-grade urban mobility simulation and machine-learning
project focused on Ikeja, Lagos, Nigeria.

The system combines:

- OpenStreetMap road-network data
- SUMO microscopic traffic simulation
- computer-vision traffic monitoring
- machine-learning ETA prediction
- dynamic routing

The project supports research on sustainable urban logistics and
intelligent transportation systems.

## Current Architecture

Primary source code is under:

src/

SUMO assets are under:

data/sumo/

Generated reports are under:

outputs/reports/

## SUMO Network

Primary network:

data/sumo/ikeja.net.xml

The network was generated from OpenStreetMap data for the Ikeja study area.

Current network statistics:

- 37,209 SUMO edges
- 16,777 SUMO junctions

## Travel Demand

Travel demand:

outputs/reports/travel_demand.csv

Current demand contains 500 vehicles.

Normalized internal schema:

- vehicle_id
- type
- depart
- origin_node
- destination_node
- priority
- trip_status

Do not change the normalized `type` and `depart` fields back to
`vehicle_type` and `departure_time` inside the routing pipeline.

## Route Generation

Route generation is implemented in:

src/sumo/route_generator.py

Current verified state:

- 500 travel-demand records loaded
- 500/500 trips mapped to SUMO edges
- 0 missing nodes
- 0 missing origin edges
- 0 missing destination edges
- 500 SUMO trips generated
- duarouter completes successfully
- 500 SUMO vehicles generated
- 500 routes generated
- 500 routes verified as valid

Do not rewrite or refactor the working route-generation pipeline unless
a downstream test demonstrates a concrete defect.

## Current Development Priority

The next milestone is SUMO simulation execution and output collection.

The simulation stage should:

1. consume data/sumo/ikeja.net.xml
2. consume data/sumo/routes.rou.xml
3. create or validate the SUMO configuration
4. run SUMO successfully
5. collect simulation outputs
6. validate that all expected vehicles are processed
7. produce data suitable for traffic analysis and ETA modelling

## Engineering Rules

- Inspect existing code before creating new modules.
- Do not duplicate existing functionality.
- Preserve the current project structure.
- Prefer simple production-quality Python.
- Use type hints.
- Avoid unnecessary abstractions.
- Do not silently change CSV schemas.
- Do not replace working code merely for stylistic reasons.
- Validate inputs and outputs.
- Use pathlib.Path for filesystem paths where practical.
- Use logging instead of print for production modules.
- Raise meaningful exceptions.
- Run relevant tests or commands after changes.
- Show exactly which files were changed.

## Research Integrity

Do not fabricate simulation results, performance metrics, traffic data,
or model accuracy.

Generated results must come from actual execution of the pipeline.

## Deadline

The current project milestone must be completed by September 23, 2026.

Prioritize functionality, validation, reproducibility, and research
outputs over unnecessary architectural complexity.