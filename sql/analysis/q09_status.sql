-- Status mix per class.
-- Chosen definition: waitlist counts rows whose booking_status is WL (state
-- when booked); confirmed, rac and cancelled use current_status. bookings is
-- every row for the class and avg_waitlist_position averages only rows whose
-- waitlist_position is greater than zero.
select
  travel_class,
  count(*) as bookings,
  sum(case when current_status = 'CNF' then 1 else 0 end) as confirmed,
  sum(case when current_status = 'RAC' then 1 else 0 end) as rac,
  sum(case when booking_status = 'WL' then 1 else 0 end) as waitlist,
  sum(case when current_status = 'CAN' then 1 else 0 end) as cancelled,
  round(100.0 * sum(case when current_status = 'CNF' then 1 else 0 end) / count(*), 2) as confirmation_rate,
  round(avg(case when cast(waitlist_position as int) > 0 then cast(waitlist_position as int) else null end), 2) as avg_waitlist_position
from bookings
group by travel_class
order by travel_class
