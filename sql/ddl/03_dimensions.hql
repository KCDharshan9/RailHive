-- Typed dimension tables used by the analysis layer.
-- MapReduce in local mode keeps the small jobs fast on a laptop.
use railway_analytics;

set hive.execution.engine=mr;
set hive.exec.mode.local.auto=true;
set hive.exec.mode.local.auto.inputbytes.max=268435456;
set hive.exec.mode.local.auto.input.files.max=16;
set hive.stats.autogather=false;

drop table if exists stations;
create table stations (
  station_code string,
  station_name string,
  state string,
  zone string,
  latitude double,
  longitude double
)
stored as orc;

insert overwrite table stations
select
  station_code,
  station_name,
  state,
  zone,
  cast(latitude as double) as latitude,
  cast(longitude as double) as longitude
from stg_stations;

drop table if exists trains;
create table trains (
  train_number string,
  train_name string,
  train_type string,
  zone string,
  source_code string,
  destination_code string,
  distance_km int,
  duration_min int,
  has_sleeper int,
  has_3ac int,
  has_2ac int,
  has_1ac int,
  has_cc int
)
stored as orc;

insert overwrite table trains
select
  train_number,
  train_name,
  train_type,
  zone,
  source_code,
  destination_code,
  cast(distance_km as int) as distance_km,
  cast(duration_min as int) as duration_min,
  cast(has_sleeper as int) as has_sleeper,
  cast(has_3ac as int) as has_3ac,
  cast(has_2ac as int) as has_2ac,
  cast(has_1ac as int) as has_1ac,
  cast(has_cc as int) as has_cc
from stg_trains;

drop table if exists train_stops;
create table train_stops (
  train_number string,
  stop_seq int,
  station_code string,
  station_name string,
  arrival_time string,
  departure_time string,
  day int
)
stored as orc;

insert overwrite table train_stops
select
  train_number,
  cast(stop_seq as int) as stop_seq,
  station_code,
  station_name,
  arrival_time,
  departure_time,
  cast(day as int) as day
from stg_train_stops;
