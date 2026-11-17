-- One row of headline KPIs. net_revenue = gross_revenue - refunds.
select
  count(distinct pnr) as total_bookings,
  count(*) as total_passengers,
  round(sum(cast(fare as double)), 2) as gross_revenue,
  round(sum(cast(refund_amount as double)), 2) as refunds,
  round(sum(cast(fare as double)) - sum(cast(refund_amount as double)), 2) as net_revenue,
  round(avg(cast(fare as double)), 2) as avg_fare,
  round(100.0 * sum(case when current_status = 'CAN' then 1 else 0 end) / count(*), 2) as cancellation_rate,
  round(100.0 * sum(case when booking_status = 'WL' then 1 else 0 end) / count(*), 2) as waitlist_share,
  round(avg(cast(delay_minutes as int)), 2) as avg_delay_minutes,
  round(avg(cast(distance_km as int)), 2) as avg_distance_km,
  round(100.0 * sum(case when current_status = 'CNF' then 1 else 0 end) / count(*), 2) as confirmed_share
from bookings
