-- Route pair performance. The outer select exists so that ORDER BY can use
-- the plain alias bookings without colliding with the table name.
select
  route,
  from_station,
  to_station,
  bookings,
  passengers,
  revenue,
  avg_fare,
  avg_delay
from (
  select
    concat(from_station_code, '-', to_station_code) as route,
    max(from_station_name) as from_station,
    max(to_station_name) as to_station,
    count(distinct pnr) as bookings,
    count(*) as passengers,
    round(sum(cast(fare as double)), 2) as revenue,
    round(avg(cast(fare as double)), 2) as avg_fare,
    round(avg(cast(delay_minutes as int)), 2) as avg_delay
  from bookings
  group by concat(from_station_code, '-', to_station_code)
) r
order by bookings desc
