-- Delay profile by railway zone. late_pct is the percentage of rows with
-- delay_minutes greater than 15.
select
  zone,
  bookings,
  avg_delay,
  late_pct
from (
  select
    zone,
    count(*) as bookings,
    round(avg(cast(delay_minutes as int)), 2) as avg_delay,
    round(100.0 * sum(case when cast(delay_minutes as int) > 15 then 1 else 0 end) / count(*), 2) as late_pct
  from bookings
  group by zone
) d
order by bookings desc
