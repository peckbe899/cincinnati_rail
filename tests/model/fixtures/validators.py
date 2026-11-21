"""The fixture feature's validators: a stop must sit on its section (0 <= c_m <= length_m)."""


def stop_on_section(rec, ctx):
    section = ctx.get("t_section", rec["data"]["section"])
    if section is None:
        return []
    length = section["data"].get("length_m")
    c = rec["data"]["c_m"]
    if length is not None and not 0 <= c <= length:
        return [{"path": "/data/c_m", "message": f"{c} m is off the section (0 to {length} m)", "rule": None}]
    return []


VALIDATORS = {"t_stop": stop_on_section}
