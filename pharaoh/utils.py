def secs_to_duration(secs):
    hours, secs = divmod(secs, 60 * 60)
    minutes, secs = divmod(secs, 60)
    if hours:
        t = (hours, minutes, secs)
    else:
        t = (minutes, secs)

    return ':'.join(format(v, '02') for v in t)
