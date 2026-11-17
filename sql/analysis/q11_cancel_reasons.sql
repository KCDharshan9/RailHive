-- Why passengers cancelled, highest count first.
select
  cancellation_reason as reason,
  count(*) as reason_count
from bookings
where current_status = 'CAN'
group by cancellation_reason
order by reason_count desc
