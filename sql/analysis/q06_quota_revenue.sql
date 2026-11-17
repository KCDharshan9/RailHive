-- Revenue by booking quota.
select
  quota,
  count(distinct pnr) as bookings,
  count(*) as passengers,
  round(sum(cast(fare as double)), 2) as revenue,
  round(avg(cast(fare as double)), 2) as avg_fare
from bookings
group by quota
order by revenue desc
