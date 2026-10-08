"""railsim: shared core for the metro and commuter/RER running-time programs.

Programs:
    python -m railsim.metro     ...   heavy/light metro (door-cycle dwell, ATO-style driving)
    python -m railsim.commuter  ...   commuter / RER / regional (platform-type dwell, push-pull, EMU, DMU)

All internal quantities are SI (m, s, kg, N, W). Conversions happen only at I/O.
"""

__version__ = "10.0.0"
