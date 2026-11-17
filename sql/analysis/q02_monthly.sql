-- Monthly volume and revenue. month is the travel month, not the booking month.
select
  substr(travel_date, 1, 7) as month,
  count(distinct pnr) as bookings,
  count(*) as passengers,
  round(sum(cast(fare as double)), 2) as revenue,
  sum(case when current_status = 'CAN' then 1 else 0 end) as cancellations,
  sum(case when booking_status = 'WL' then 1 else 0 end) as waitlist,
  round(avg(cast(delay_minutes as int)), 2) as avg_delay
from bookings
group by substr(travel_date, 1, 7)
order by month
