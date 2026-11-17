-- Delay profile per travel month. late_pct is the percentage of rows with
-- delay_minutes greater than 15.
select
  month,
  bookings,
  avg_delay,
  late_pct
from (
  select
    substr(travel_date, 1, 7) as month,
    count(*) as bookings,
    round(avg(cast(delay_minutes as int)), 2) as avg_delay,
    round(100.0 * sum(case when cast(delay_minutes as int) > 15 then 1 else 0 end) / count(*), 2) as late_pct
  from bookings
  group by substr(travel_date, 1, 7)
) d
order by month
