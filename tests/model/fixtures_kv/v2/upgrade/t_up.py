"""Upgrader of the test kind t_up: version 1 to 2 adds an empty label."""


def up_1(data):
    out = dict(data)
    out.setdefault("label", "")
    return out
