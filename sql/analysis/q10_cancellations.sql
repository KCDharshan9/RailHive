-- Cancellations and refunds per travel month.
select
  substr(travel_date, 1, 7) as month,
  sum(case when current_status = 'CAN' then 1 else 0 end) as cancellations,
  round(100.0 * sum(case when current_status = 'CAN' then 1 else 0 end) / count(*), 2) as cancellation_rate,
  round(sum(cast(refund_amount as double)), 2) as refund_amount
from bookings
group by substr(travel_date, 1, 7)
order by month
