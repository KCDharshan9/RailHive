-- Typed ORC fact table, dynamically partitioned by travel_month.
-- travel_month is the last column of the insert select because it is the
-- partition column. 150000 rows should load well inside the runner timeout.
use railway_analytics;

set hive.execution.engine=mr;
set hive.exec.mode.local.auto=true;
set hive.exec.mode.local.auto.inputbytes.max=268435456;
set hive.exec.mode.local.auto.input.files.max=16;
set hive.stats.autogather=false;
set hive.exec.dynamic.partition=true;
set hive.exec.dynamic.partition.mode=nonstrict;
set hive.exec.max.dynamic.partitions=500;
set hive.exec.max.dynamic.partitions.pernode=500;

drop table if exists bookings;
create table bookings (
  pnr string,
  passenger_seq int,
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
  distance_km int,
  travel_class string,
  quota string,
  booking_status string,
  current_status string,
  waitlist_position int,
  fare double,
  refund_amount double,
  payment_mode string,
  channel string,
  passenger_age int,
  passenger_gender string,
  concession int,
  cancellation_flag int,
  cancellation_reason string,
  delay_minutes int
)
partitioned by (travel_month string)
stored as orc;

insert overwrite table bookings partition (travel_month)
select
  pnr,
  cast(passenger_seq as int) as passenger_seq,
  train_number,
  train_name,
  train_type,
  zone,
  travel_date,
  booking_date,
  from_station_code,
  from_station_name,
  to_station_code,
  to_station_name,
  cast(distance_km as int) as distance_km,
  travel_class,
  quota,
  booking_status,
  current_status,
  cast(waitlist_position as int) as waitlist_position,
  cast(fare as double) as fare,
  cast(refund_amount as double) as refund_amount,
  payment_mode,
  channel,
  cast(passenger_age as int) as passenger_age,
  passenger_gender,
  cast(concession as int) as concession,
  cast(cancellation_flag as int) as cancellation_flag,
  cancellation_reason,
  cast(delay_minutes as int) as delay_minutes,
  travel_month
from stg_bookings;
