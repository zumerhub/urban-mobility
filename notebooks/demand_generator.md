General form:

    Importance = w1D+w2C+w3B

    where:
        D=degree
        C=closeness
        B=betweenness

Why 0.20, 0.30, 0.50?

Those were example weights, not the only correct values.

I chose them because, for an urban logistics problem:

Betweenness is often the strongest indicator of critical freight corridors.

So

50%

Betweenness

30%

Closeness

20%

Degree

This reflects a reasonable engineering assumption.

Could we use equal weights?

Absolutely.

importance =
(
degree
+
closeness
+
betweenness
)/3

This is simple and easy to explain.

Could we learn the weights?

Even better.

Suppose later your YOLO model estimates

traffic_density

and your XGBoost predicts

travel_time

Then you could use a model such as:

Importance =
0.15 Degree
+
0.20 Closeness
+
0.35 Betweenness
+
0.30 Traffic Density

or even train a regression model to determine the weights from data.

That would make the weighting data-driven instead of manually selected.

Why normalize?

Suppose the computed scores are

Node	Score
A	    15
B	    25
C	    60

These don't form probabilities.

The sum is

15 + 25 + 60 = 100

Normalize by dividing each value by the total:

Node	Probability
A	    0.15
B	    0.25
C	    0.60

Now they sum to exactly 1.0, which allows you to use them directly with probability-based sampling methods (such as selecting origins and destinations according to node importance).
For your ATRC paper

Since this is research, I would avoid presenting the weights as arbitrary constants. Instead, state something like:

Node importance is computed as a weighted combination of degree, closeness, and betweenness centrality. Greater emphasis is assigned to betweenness centrality because it better captures critical intersections that serve as major transit corridors for urban freight movement. The weights are selected based on graph-theoretic principles and transportation network characteristics.


============= generating departure times ==============
What is the purpose of generate_departure_times()?

It is to assign a departure time (in seconds) to every vehicle you will generate.

For example, if you generate 5,000 vehicles, each vehicle needs a departure time:

Vehicle	Departure Time (seconds)	Time
1	28,500	07:55
2	29,230	08:07
3	47,800	13:16
4	63,500	17:38

This departure time will later be written into your SUMO trip file.

Where do these times come from?

You already defined in config.py:

MORNING_PEAK_START
MORNING_PEAK_END

EVENING_PEAK_START
EVENING_PEAK_END

NUMBER_OF_VEHICLES

Those constants are exactly what this function should use.

The algorithm

Instead of every vehicle departing at 8:00 AM, we want a realistic distribution.

For example:

5000 vehicles

60% Morning Peak

20% Midday

20% Evening Peak

You can randomly generate departure times inside each interval.

Example:

Morning:

07:00
07:04
07:06
07:22
07:35
08:18
08:51

Evening:

16:05
16:12
16:43
17:15
18:10
18:42

This is much closer to real traffic than everyone leaving at once.

What should the function produce?

At the end of the method, you should have something like:

self.departure_times

which is a NumPy array or Python list containing one departure time per vehicle.

For example:

[25345,
25520,
25780,
...
64882]

Its length should equal:

NUMBER_OF_VEHICLES
Structure of the method

Your method should look like this:

def generate_departure_times(self) -> None:

Inside it:

Log the start.
Generate departure times.
Sort them in ascending order (vehicles leave chronologically).
Store them in:
self.departure_times
Log how many were generated.
Don't worry about origins yet

Many people make this mistake.

This method should only answer:

When does each vehicle leave?

It should not decide:

origin
destination
vehicle type

Those are handled by later methods.

My recommendation

I recommend using NumPy for this method because it is much faster and cleaner than Python's random module when generating thousands of values.

Then, in the next method:

generate_vehicle_types()

you'll assign each departure a vehicle class (passenger, delivery van, truck, or bus), keeping each responsibility separate and making the code easier to test and maintain.