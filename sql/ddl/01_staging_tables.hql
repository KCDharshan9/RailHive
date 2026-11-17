-- Managed text staging tables. Every column is STRING so that the comma
-- separated CSV files load without conversion errors.
use railway_analytics;

drop table if exists stg_stations;
create table stg_stations (
  station_code string,
  station_name string,
  state string,
  zone string,
  latitude string,
  longitude string
)
row format delimited fields terminated by ','
stored as textfile
tblproperties ('skip.header.line.count'='1');

drop table if exists stg_trains;
create table stg_trains (
  train_number string,
  train_name string,
  train_type string,
  zone string,
  source_code string,
  destination_code string,
  distance_km string,
  duration_min string,
  has_sleeper string,
  has_3ac string,
  has_2ac string,
  has_1ac string,
  has_cc string
)
row format delimited fields terminated by ','
stored as textfile
tblproperties ('skip.header.line.count'='1');

drop table if exists stg_train_stops;
create table stg_train_stops (
  train_number string,
  stop_seq string,
  station_code string,
  station_name string,
  arrival_time string,
  departure_time string,
  day string
)
row format delimited fields terminated by ','
stored as textfile
tblproperties ('skip.header.line.count'='1');

drop table if exists stg_bookings;
create table stg_bookings (
  pnr string,
  passenger_seq string,
  train_number string,
  train_name string,
  train_type string,
  zone string,
  travel_date string,
  booking_date string,
  from_station_code string,
  from_station_name string,
  to_station_code string,
  to_station_name string,
  distance_km string,
  travel_class string,
  quota string,
  booking_status string,
  current_status string,
  waitlist_position string,
  fare string,
  refund_amount string,
  payment_mode string,
  channel string,
  passenger_age string,
  passenger_gender string,
  concession string,
  cancellation_flag string,
  cancellation_reason string,
  delay_minutes string,
  travel_month string
)
row format delimited fields terminated by ','
stored as textfile
tblproperties ('skip.header.line.count'='1');
