-- Train performance. cancel_rate is a percentage of all rows for the train.
select
  train_number,
  train_name,
  train_type,
  bookings,
  passengers,
  revenue,
  avg_delay,
  cancel_rate
from (
  select
    train_number,
    train_name,
    train_type,
    count(distinct pnr) as bookings,
    count(*) as passengers,
    round(sum(cast(fare as double)), 2) as revenue,
    round(avg(cast(delay_minutes as int)), 2) as avg_delay,
    round(100.0 * sum(case when current_status = 'CAN' then 1 else 0 end) / count(*), 2) as cancel_rate
  from bookings
  group by train_number, train_name, train_type
) t
order by revenue desc
