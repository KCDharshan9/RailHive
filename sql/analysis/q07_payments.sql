-- Revenue by payment mode.
select
  payment_mode,
  count(distinct pnr) as bookings,
  round(sum(cast(fare as double)), 2) as revenue
from bookings
group by payment_mode
order by revenue desc
