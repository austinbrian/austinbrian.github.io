SELECT start_date,
    name,
    ROUND(moving_time / 60, 2) AS minutes,
    ROUND(distance * 0.000621371, 3) AS miles,
    ROUND(minutes / miles, 4) AS min_per_mi_calculated,
    ROUND(min_per_mi_calculated, 0) AS minutes_per_mi,
    FLOOR(min_per_mi_calculated)::int AS min_part,
    LPAD(
        ROUND(
            (
                min_per_mi_calculated - FLOOR(min_per_mi_calculated)
            ) * 60
        )::text,
        2,
        '0'
    ) AS sec_part,
    FLOOR(min_per_mi_calculated)::int::text || ':' || LPAD(
        ROUND(
            (
                min_per_mi_calculated - FLOOR(min_per_mi_calculated)
            ) * 60
        )::text,
        2,
        '0'
    ) AS pace_mm_ss
FROM activities
where type = 'Run'
    and start_date > '2000-01-01'::date
order by start_date asc
limit 17;