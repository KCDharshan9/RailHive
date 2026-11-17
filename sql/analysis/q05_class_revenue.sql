-- Revenue share by class. The cross join brings the grand total revenue in
-- without a window function, which is not portable to Hive here.
-- revenue_raw is kept inside the derived table so share_pct is not computed
-- from rounded values; it is not part of the output columns.
select
  c.travel_class,
  c.bookings,
  c.passengers,
  c.revenue,
  c.avg_fare,
  round(100.0 * c.revenue_raw / t.total_revenue, 2) as share_pct
from (
  select
    travel_class,
    count(distinct pnr) as bookings,
    count(*) as passengers,
    sum(cast(fare as double)) as revenue_raw,
    round(sum(cast(fare as double)), 2) as revenue,
    round(avg(cast(fare as double)), 2) as avg_fare
  from bookings
  group by travel_class
) c
cross join (
  select sum(cast(fare as double)) as total_revenue
  from bookings
) t
order by c.revenue desc
