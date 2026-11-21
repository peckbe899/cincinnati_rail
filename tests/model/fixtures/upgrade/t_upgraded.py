"""Upgraders of the fixture kind t_upgraded: version 1 held feet as ``length_ft``; version 2 added ``label``."""


def up_1(data):
    out = dict(data)
    out["length_m"] = round(out.pop("length_ft") * 0.3048, 3)
    return out


def up_2(data):
    out = dict(data)
    out.setdefault("label", "")
    return out
