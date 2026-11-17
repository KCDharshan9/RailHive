-- Load the generated CSV inputs into the staging tables.
-- The CSV files have a header row, so the staging tables skip the first line.
use railway_analytics;

load data local inpath '/data/raw/stations.csv' overwrite into table stg_stations;
load data local inpath '/data/raw/trains.csv' overwrite into table stg_trains;
load data local inpath '/data/raw/train_stops.csv' overwrite into table stg_train_stops;
load data local inpath '/data/raw/bookings.csv' overwrite into table stg_bookings;
