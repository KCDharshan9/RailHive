-- Revenue by booking channel.
select
  channel,
  count(distinct pnr) as bookings,
  round(sum(cast(fare as double)), 2) as revenue
from bookings
group by channel
order by revenue desc
