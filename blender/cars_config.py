# Each car's cockpit character for build_car.py (styles.py). Keys are the exported body names
# (folder names in %USERPROFILE%\dev\oth-cockpit-build\cars); "game" = the in-game car (Car_<game>.glb).
# side: -1 left-hand drive, +1 right-hand drive. Positions are worked out from the real body; the
# optional eye_y / eye_z / wheel_* / dash_* values fine-tune them.
#
# Styles: dash = painted | painted_pad | plastic | grey | wood | shelf
#         cluster = hood | wide | pod | center | single | row
#         wheel = t | three | two | four | banjo; rim = black | ivory | wood | plastic; spoke_mat = chrome | black | ivory
#         seats = bucket | headrest | bench; handbrake = lever | pull | none; shifter = floor | dash | column
CARS = {
    # Small French 4x4: painted dash with a fabric shelf, push-pull gear lever, umbrella handbrake.
    "Baguette": dict(game="Baguette", side=-1, dash="shelf", cluster="hood", wheel="two", rim="plastic",
                     spoke_mat="black", horn="plastic", seats="bucket", shifter="dash", handbrake="pull", transfer=False,
                     colors=dict(seat=(0.10, 0.05, 0.02), seat2=(0.16, 0.09, 0.04))),
    # 1940s flatbed truck: painted steel dash, one big speedometer, big thin wheel, bench seat.
    "BlastWagon": dict(game="BlastWagon", side=-1, dash="painted", cluster="single", wheel="banjo", rim="ivory",
                       spoke_mat="chrome", wheel_r=0.23, wheel_tilt=35, seats="bench", handbrake="pull", bezel="chrome",
                       colors=dict(seat=(0.12, 0.06, 0.03), seat2=(0.18, 0.10, 0.05))),
    # Old military car: flat steel dash with a row of small gauges and toggle switches.
    "Boar": dict(game="Boar", side=-1, dash="painted", cluster="row", wheel="three", rim="black", spoke_mat="black",
                 horn="plastic", seats="bucket", handbrake="lever", bezel="black",
                 colors=dict(seat=(0.05, 0.06, 0.03), seat2=(0.07, 0.08, 0.04))),
    # Boxy 80s Japanese off-roader: grey plastic, cluster under a hood, right-hand drive.
    "Brick": dict(game="Brick", side=1, dash="grey", cluster="hood", wheel="four", rim="plastic", spoke_mat="black",
                  horn="plastic", seats="headrest", handbrake="lever", difflock=True,
                  colors=dict(plastic2=(0.09, 0.09, 0.092), seat=(0.08, 0.08, 0.085), seat2=(0.13, 0.13, 0.14))),
    # 60s American: painted dash, chrome-ringed single speedo, bench seat.
    # Painted pod with chrome trim on top of the dash (read over the wheel), chrome grab bar, two-spoke wheel.
    "BullV1": dict(game="Bull", side=-1, dash="painted_pad", cluster="pod", pod_mat="paint", pod_trim="chrome", bezel="chrome",
                   grab_bar=True, glovebox=False, wheel="two", rim="black", spoke_mat="chrome", seats="bench", handbrake="pull",
                   colors=dict(seat=(0.20, 0.04, 0.03), seat2=(0.28, 0.07, 0.05))),
    # FJ45-type pickup: like the DingDing family, bench seat.
    "Burro": dict(game="Burro", side=1, dash="painted_pad", cluster="hood", wheel="t", rim="black", spoke_mat="chrome",
                  seats="bench", handbrake="pull", colors=dict(seat=(0.05, 0.045, 0.04))),
    # 80s American pickup: plastic dash, wide cluster, bench seat, column automatic.
    "Cumbre": dict(game="Cumbre", side=-1, dash="plastic", cluster="wide", wheel="four", rim="plastic", spoke_mat="black",
                   horn="plastic", seats="bench", shifter="column", automatic=True, handbrake="none", transfer=True,
                   colors=dict(plastic=(0.05, 0.04, 0.035), seat=(0.10, 0.07, 0.05), seat2=(0.14, 0.10, 0.07))),
    # 80s luxury wagon: wood trim, wide cluster, plush seats with headrests, automatic.
    "GrandWoodman": dict(game="GrandWoodman", side=-1, dash="wood", cluster="wide", wheel="three", rim="wood",
                         spoke_mat="chrome", seats="headrest", automatic=True, shifter="column", handbrake="none", carpet=True,
                         colors=dict(seat=(0.16, 0.09, 0.05), seat2=(0.22, 0.13, 0.07), carpet=(0.08, 0.05, 0.03))),
    # Small 80s Italian hatch: fabric shelf dash, small cluster box.
    "Grizzly": dict(game="Grizzly", side=-1, dash="shelf", cluster="hood", wheel="two", rim="plastic", spoke_mat="black",
                    horn="plastic", seats="bucket", handbrake="lever", transfer=False, dial_r=0.06,
                    colors=dict(seat=(0.06, 0.06, 0.07), seat2=(0.12, 0.10, 0.08))),
    # Small Japanese 4x4: simple painted dash, right-hand drive.
    "Lynx": dict(game="Lynx", side=1, dash="painted_pad", cluster="hood", wheel="three", rim="black", spoke_mat="black",
                 horn="plastic", seats="bucket", handbrake="lever", dial_r=0.065),
    # Unimog-type crew-cab truck: high seat, big flat wheel, flat steel dash with a row of gauges.
    "Mammoth": dict(game="Mammoth", side=-1, dash="painted", cluster="row", wheel="two", rim="black", spoke_mat="black",
                    horn="plastic", wheel_r=0.23, wheel_tilt=55, seats="headrest", handbrake="lever", difflock=True, bezel="black"),
    # Camper truck (cab-over): flat dash, flat wheel, high seat.
    "Marshal": dict(game="Marshal", side=-1, dash="plastic", cluster="wide", wheel="two", rim="plastic", spoke_mat="black",
                    horn="plastic", wheel_r=0.22, wheel_tilt=55, seats="headrest", handbrake="lever"),
    # Lada Niva-type with a roll cage: Soviet dash with a cluster hood.
    "Polyana": dict(game="Polyana", side=-1, dash="plastic", cluster="hood", wheel="three", rim="plastic", spoke_mat="black",
                    horn="plastic", seats="headrest", handbrake="lever", difflock=True,
                    colors=dict(seat=(0.06, 0.04, 0.03), seat2=(0.10, 0.07, 0.05))),
    # 80s Japanese SUV: plastic dash with a wide cluster, right-hand drive.
    "Roamer": dict(game="Roamer", side=1, dash="plastic", cluster="wide", wheel="four", rim="plastic", spoke_mat="black",
                   horn="plastic", seats="headrest", handbrake="lever", carpet=True,
                   colors=dict(plastic=(0.07, 0.065, 0.06), seat=(0.10, 0.09, 0.08), seat2=(0.15, 0.14, 0.12))),
    # Van: flat wheel, high seat, plastic dash, huge windscreen.
    "RustOx": dict(game="RustOx", side=-1, dash="plastic", cluster="hood", wheel="two", rim="plastic", spoke_mat="black",
                   horn="plastic", wheel_r=0.21, wheel_tilt=50, seats="headrest", handbrake="lever",
                   colors=dict(seat=(0.05, 0.06, 0.09), seat2=(0.09, 0.11, 0.16))),
    # 1950s woodie wagon: painted dash, centre speedo, banjo wheel, bench seat.
    "Timberbox": dict(game="Timberbox", side=-1, dash="painted", cluster="single", wheel="banjo", rim="ivory",
                      spoke_mat="chrome", wheel_r=0.22, seats="bench", handbrake="pull",
                      colors=dict(seat=(0.18, 0.12, 0.06), seat2=(0.24, 0.17, 0.09))),
    # Land Rover Series type: instruments in the middle of the dash, very bare, right-hand drive.
    "Tinny": dict(game="Tinny", side=1, dash="painted", cluster="center", wheel="four", rim="black", spoke_mat="black",
                  horn="plastic", seats="bucket", handbrake="lever", difflock=True, door_cards=False, bezel="black",
                  colors=dict(seat=(0.03, 0.035, 0.03))),
    # 70s American SUV: big plastic dash, wide cluster.
    "TrailBurner": dict(game="TrailBurner", side=-1, dash="plastic", cluster="wide", wheel="four", rim="plastic",
                        spoke_mat="black", horn="plastic", seats="headrest", handbrake="pull",
                        colors=dict(plastic=(0.04, 0.05, 0.07), seat=(0.05, 0.07, 0.11), seat2=(0.08, 0.10, 0.15))),
    # International Scout type: 60s painted dash.
    "TrailRat": dict(game="Trailrat", side=-1, dash="painted_pad", cluster="hood", wheel="three", rim="black",
                     spoke_mat="chrome", seats="bucket", handbrake="pull"),
    # Small Japanese 4x4: right-hand drive, plastic hood cluster.
    "Wombat": dict(game="Wombat", side=1, dash="plastic", cluster="hood", wheel="three", rim="plastic", spoke_mat="black",
                   horn="plastic", seats="headrest", handbrake="lever", dial_r=0.068),
    # 70s Wagoneer: wood strip, wide cluster, bench seat, column automatic.
    "Woodman": dict(game="Woodman", side=-1, dash="wood", cluster="wide", wheel="three", rim="black", spoke_mat="chrome",
                    seats="bench", automatic=True, shifter="column", handbrake="none", carpet=True,
                    colors=dict(seat=(0.12, 0.08, 0.05), seat2=(0.18, 0.12, 0.07))),
}
