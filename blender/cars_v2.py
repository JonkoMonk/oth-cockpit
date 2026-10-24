# v2: each car's cockpit CHARACTER (game style), used by build_car_v2.py / styles_v2.py.
# Keys are the exported body names (folders in %USERPROFILE%\dev\oth-cockpit-build\cars); game = Car_<game>.glb.
# side: -1 left-hand drive, +1 right-hand drive.  Colours are sRGB 0..1 (like a paint program).
#
#   dash     painted | painted_pad | plastic | wood | flat | shelf
#   cluster  binnacle | wide | tubes | pod | center | single | row | oval | box
#   wheel    droop | t | two | three | four | banjo | single | bus      (+ wheel_r, wheel_tilt, rim_thick)
#   seats    bucket | headrest | bench | deckchair   seat_pattern plain | stripes | tartan | ribs
#   dials    black | cream | olive | eighties        ring metal | dark
#   handbrake lever | pull | none    shifter floor | column    transfer True/False    extra_levers [(x, colour)]
#   features grab_bar, vent_flaps, toggles, cb_radio, pine_freshener, inclinometer, military_radio,
#            fire_extinguisher, roll_cage, engine_cover, canvas_roof, curtain, diff_switches, console,
#            overhead_console, dash_tray, winch_lever, wood_lining
# Layout overrides (optional): eye_y, eye_z, driver_x, dash_z, dash_below_eye, dash_height,
#                              wheel_drop, wheel_dist, wheel_r, wheel_tilt  (see styles.Layout)
CARS = {
    # Toyota FJ40. The approved v2 mock-up: painted steel, black pad, dials read through the wheel.
    "DingDing": dict(game="DingDing", side=-1, character="Painted steel and a padded brow: the classic 70s Land Cruiser",
                     dash="painted_pad", cluster="binnacle", wheel="droop", seats="bucket", handbrake="pull",
                     features=["grab_bar", "fj_bits"], eye_y=1.62, eye_z=-0.44, driver_x=0.42, dash_z=0.22, wheel_drop=0.50,
                     wheel_dist=0.42, wheel_tilt=25, wheel_r=0.212,
                     dial_r=0.064,   # 0.075 put the rim over the speedo/tacho edges (fit check, eye -2..+4 cm)
                     ws=dict(base_y=1.40, base_z=0.43, top_y=2.0, top_z=0.31, half_w=0.73),   # measured by hand (CLAUDE.md)
                     colors=dict(pad=(0.24, 0.23, 0.25))),
    # Toyota FJ45 pickup: the DingDing's work-boots brother. Bench seat, rubber tray on the dash, no radio.
    "Burro": dict(game="Burro", side=1, character="The DingDing's workhorse brother: bench seat, dash tray, no radio",
                  dash="painted_pad", cluster="binnacle", wheel="t", seats="bench", seat_pattern="stripes", radio=False,
                  handbrake="pull", features=[], horn="accent",
                  ws=dict(base_y=1.40, base_z=0.43, top_y=2.0, top_z=0.31, half_w=0.73),   # same front as the DingDing
                  colors=dict(seat=(0.42, 0.40, 0.36), seat2=(0.52, 0.50, 0.45), accent=(0.86, 0.52, 0.22),
                              rim=(0.86, 0.82, 0.70))),
    # Land Rover Defender 90: binnacle pod over a flat four-spoke wheel, vent flaps, levers forest, RHD.
    "Protector": dict(game="Protector", side=1, character="Defender: pod over a flat wheel, vent flaps, yellow diff-lock knob",
                      dash="plastic", cluster="pod", wheel="four", wheel_tilt=40, seats="headrest", seat_pattern="ribs",
                      handbrake="lever", features=["vent_flaps"], extra_levers=[(0.15, "knob3")], eye_y=1.64, eye_z=-0.30, wheel_drop=0.47, wheel_r=0.20,
                      colors=dict(dash=(0.20, 0.20, 0.22), seat=(0.30, 0.31, 0.33), seat2=(0.40, 0.41, 0.43),
                                  door=(0.26, 0.26, 0.28), spoke=(0.20, 0.20, 0.22))),
    # Land Rover Series IIA: bare painted steel, dials in the middle, canvas roof, no door cards, RHD.
    "Tinny": dict(game="Tinny", side=1, character="Series Land Rover: bare tin, dials in the middle, canvas over your head",
                  dash="flat", cluster="center", wheel="three", rim_thick=0.013, seats="bucket", handbrake="lever",
                  door_cards=False, radio=False, dials="olive", features=["vent_flaps", "canvas_roof"],
                  extra_levers=[(0.15, "knob3")],
                  colors=dict(liner=(0.66, 0.60, 0.44), seat=(0.22, 0.24, 0.20), seat2=(0.30, 0.32, 0.27),
                              spoke=(0.16, 0.16, 0.18), panel=(0.18, 0.19, 0.16))),
    # International Scout 800: 60s painted dash, a straight row of dials, chrome-free and cheerful.
    "TrailRat": dict(game="Trailrat", side=-1, character="60s Scout: painted dash, a row of dials, red vinyl",
                     dash="painted", cluster="row", wheel="three", seats="bucket", seat_pattern="stripes", handbrake="pull",
                     colors=dict(seat=(0.62, 0.20, 0.16), seat2=(0.72, 0.30, 0.24), accent=(0.95, 0.88, 0.75),
                                 door=(0.55, 0.18, 0.14), panel=(0.22, 0.22, 0.24))),
    # Ford Bronco (first generation): wide oval instrument band, grab bar, two-spoke wheel.
    "BullV1": dict(game="Bull", side=-1, character="Early Bronco: horizontal oval dial band, grab bar, saddle-tan vinyl",
                   dash="painted_pad", cluster="oval", wheel="two", seats="bucket", seat_pattern="ribs", handbrake="pull",
                   colors=dict(seat=(0.66, 0.44, 0.26), seat2=(0.74, 0.52, 0.32), door=(0.58, 0.38, 0.22),
                               pad=(0.30, 0.22, 0.17))),
    # Chevrolet K5 Blazer: big 70s plastic dash in charcoal with saddle-tan seats, wide cluster, CB radio, high-back buckets.
    # (Was all blue; JonkoMonk 2026-10-24: "really ugly", picked charcoal + tan.)
    "TrailBurner": dict(game="TrailBurner", side=-1, character="Square-body Blazer: charcoal plastic dash, saddle-tan seats, CB radio, pine tree",
                        dash="plastic", cluster="wide", wheel="two", hub="bar", seats="headrest", seat_pattern="ribs", handbrake="pull",
                        automatic=True, shifter="column", features=["pine_freshener"],
                        colors=dict(dash=(0.17, 0.16, 0.16), pad=(0.12, 0.115, 0.115), panel=(0.10, 0.10, 0.11),
                                    seat=(0.62, 0.46, 0.30), seat2=(0.70, 0.54, 0.36), door=(0.52, 0.38, 0.25),
                                    rim=(0.14, 0.13, 0.13), spoke=(0.14, 0.13, 0.13), carpet=(0.36, 0.27, 0.18)), carpet=True),
    # 80s American pickup: tan plastic, striped bench, column automatic, CB radio and an air freshener.
    "Cumbre": dict(game="Cumbre", side=-1, character="80s pickup: tan plastic, striped bench, CB radio, column shift",
                   dash="plastic", cluster="wide", wheel="four", hub="big", seats="bench", seat_pattern="stripes", handbrake="none",
                   automatic=True, shifter="column", features=[], dials="eighties",
                   colors=dict(dash=(0.62, 0.50, 0.38), pad=(0.52, 0.41, 0.30), panel=(0.16, 0.15, 0.15),
                               seat=(0.60, 0.48, 0.36), seat2=(0.68, 0.56, 0.42), accent=(0.86, 0.42, 0.20),
                               door=(0.56, 0.44, 0.33), rim=(0.52, 0.41, 0.30), spoke=(0.52, 0.41, 0.30))),
    # Jeep Wagoneer (SJ): painted dash with a woodgrain band, plaid bench, column automatic.
    "Woodman": dict(game="Woodman", side=-1, character="60s Wagoneer: woodgrain band, plaid bench, big thin wheel",
                    dash="wood", cluster="row", wheel="two", rim_thick=0.012, wheel_r=0.22, seats="bench", seat_pattern="tartan",
                    handbrake="none", automatic=True, shifter="column", carpet=True, door_insert="wood",
                    colors=dict(dash=(0.70, 0.66, 0.58), pad=(0.30, 0.24, 0.20), seat=(0.52, 0.22, 0.16),
                                seat2=(0.78, 0.66, 0.46), door=(0.46, 0.34, 0.24), carpet=(0.42, 0.24, 0.16))),
    # Jeep Grand Wagoneer: the luxury one. Big wood fascia, plush tan, overhead console with compass.
    "GrandWoodman": dict(game="GrandWoodman", side=-1, character="Grand Wagoneer: wood everywhere, plush tan, overhead compass",
                         dash="wood", cluster="wide", wheel="three", seats="headrest", seat_pattern="ribs", handbrake="none",
                         automatic=True, shifter="column", carpet=True, door_insert="wood", features=[],
                         colors=dict(dash=(0.60, 0.46, 0.32), pad=(0.50, 0.38, 0.26), seat=(0.70, 0.54, 0.38),
                                     seat2=(0.78, 0.62, 0.44), door=(0.62, 0.48, 0.34), rim=(0.50, 0.30, 0.16),
                                     carpet=(0.50, 0.38, 0.26), wood=(0.52, 0.30, 0.15))),
    # 1950s woodie wagon: painted dash, one big cream speedo, banjo wheel, push-button radio, wooden roof bows.
    "Timberbox": dict(game="Timberbox", side=-1, character="50s woodie: one big cream speedo, banjo wheel, push-button radio",
                      dash="painted", cluster="single", wheel="banjo", rim_thick=0.012, wheel_r=0.22, seats="bench",
                      handbrake="pull", dials="cream", radio="pushbutton", door_insert="wood", features=["wood_lining"],
                      colors=dict(rim=(0.92, 0.88, 0.76), spoke=(0.80, 0.80, 0.80), seat=(0.55, 0.30, 0.18),
                                  seat2=(0.68, 0.42, 0.26), door=(0.50, 0.30, 0.18), panel=(0.20, 0.18, 0.16))),
    # Dodge Power Wagon: flat steel truck dash, cream dials, big flat wheel, bench, winch PTO lever.
    "BlastWagon": dict(game="BlastWagon", side=-1, character="Power Wagon: flat steel, cream dials, winch lever on the floor",
                       dash="flat", cluster="row", wheel="four", wheel_r=0.23, wheel_tilt=35, seats="bench", handbrake="lever",
                       dials="cream", radio=False, features=["winch_lever"],
                       colors=dict(seat=(0.30, 0.26, 0.22), seat2=(0.40, 0.35, 0.30), panel=(0.20, 0.20, 0.20),
                                   rim=(0.14, 0.14, 0.15), spoke=(0.14, 0.14, 0.15))),
    # Volvo TP21 "Sugga" radio car: 50s Volvo dash, ivory two-spoke wheel, a military radio set for the passenger.
    "Boar": dict(game="Boar", side=-1, character="Swedish army radio car: ivory wheel, one big dial, radio set on the passenger side",
                 dash="painted", cluster="single", wheel="two", rim_thick=0.013, wheel_r=0.21, seats="bucket", handbrake="pull",
                 dials="cream", radio=False, glovebox=False, features=[],
                 colors=dict(rim=(0.90, 0.86, 0.74), spoke=(0.90, 0.86, 0.74), seat=(0.30, 0.31, 0.24),
                             seat2=(0.38, 0.39, 0.30), door=(0.30, 0.31, 0.24))),
    # VW Iltis: bare military. Instrument box on a black dash, roll bar, canvas roof, extinguisher.
    "Lynx": dict(game="Lynx", side=-1, character="Bundeswehr Iltis: bare black dash, instrument box, roll bar, canvas",
                 dash="plastic", cluster="box", wheel="two", seats="bucket", handbrake="lever", dials="olive", radio=False,
                 features=["roll_cage", "canvas_roof", "fire_extinguisher"],
                 colors=dict(dash=(0.17, 0.17, 0.18), pad=(0.17, 0.17, 0.18), seat=(0.33, 0.35, 0.24),
                             seat2=(0.40, 0.42, 0.30), liner=(0.40, 0.42, 0.30), door=(0.20, 0.20, 0.21),
                             cage=(0.20, 0.20, 0.21))),
    # Mercedes G-Class (W460): upright dash, three dials in a row, the famous grab handle, diff-lock buttons, checks.
    "Wombat": dict(game="Wombat", side=-1, character="Early G-Class: upright dash, passenger grab handle, diff-lock buttons, checked seats",
                   dash="plastic", cluster="binnacle", wheel="four", seats="headrest", seat_pattern="tartan", handbrake="lever",
                   features=[],
                   colors=dict(dash=(0.18, 0.18, 0.20), pad=(0.18, 0.18, 0.20), seat=(0.24, 0.24, 0.26),
                               seat2=(0.56, 0.52, 0.44), door=(0.22, 0.22, 0.24), rim=(0.14, 0.14, 0.15),
                               spoke=(0.14, 0.14, 0.15))),
    # Toyota Land Cruiser J70: chunky 80s grey plastic, cluster hood, grab bar, two levers. RHD.
    "Brick": dict(game="Brick", side=1, character="80s Land Cruiser: chunky grey plastic, grab bar, grey cloth",
                  dash="plastic", cluster="wide", wheel="four", seats="headrest", seat_pattern="stripes", handbrake="lever",
                  dials="eighties", features=["grab_bar", "grab_dark", "console"],
                  colors=dict(dash=(0.46, 0.46, 0.48), pad=(0.36, 0.36, 0.38), panel=(0.16, 0.16, 0.18),
                              seat=(0.40, 0.40, 0.42), seat2=(0.50, 0.50, 0.52), accent=(0.86, 0.36, 0.22),
                              door=(0.42, 0.42, 0.44), rim=(0.26, 0.26, 0.28), spoke=(0.26, 0.26, 0.28))),
    # Toyota 4Runner / Hilux Surf (around 1990): dark 90s plastic, the dash-top inclinometer, console. RHD.
    "Roamer": dict(game="Roamer", side=1, character="90s 4Runner: the dash-top tilt meter, sporty three-spoke, blue velour",
                   dash="plastic", cluster="wide", wheel="three", hub="big", rim_thick=0.022, seats="headrest", seat_pattern="ribs",
                   handbrake="lever", dials="eighties", features=["console"], carpet=True,
                   colors=dict(dash=(0.30, 0.31, 0.35), pad=(0.24, 0.25, 0.29), seat=(0.30, 0.36, 0.50),
                               seat2=(0.38, 0.44, 0.58), door=(0.26, 0.28, 0.33), carpet=(0.22, 0.24, 0.28),
                               rim=(0.16, 0.16, 0.18), spoke=(0.16, 0.16, 0.18))),
    # Lada Niva: Soviet 70s. Three dials in deep tubes, two transfer levers, roll cage, brown patterned seats.
    "Polyana": dict(game="Polyana", side=-1, character="Lada Niva: three dials in deep tubes, two transfer levers, roll cage",
                    dash="plastic", cluster="tubes", wheel="two", rim_thick=0.013, seats="headrest", seat_pattern="tartan",
                    handbrake="lever", features=["roll_cage"], extra_levers=[(0.15, "knob")],
                    nudge_reach=0.06,   # lets the speedo drop from the rim line into the wheel's opening
                    colors=dict(dash=(0.15, 0.15, 0.16), pad=(0.15, 0.15, 0.16), seat=(0.42, 0.28, 0.20),
                                seat2=(0.62, 0.44, 0.30), door=(0.36, 0.25, 0.18), cage=(0.80, 0.22, 0.16))),
    # Fiat Panda 4x4: no dash, a full-width fabric shelf, a tiny instrument box, deckchair seats.
    "Grizzly": dict(game="Grizzly", side=-1, character="Panda 4x4: fabric shelf instead of a dash, deckchair seats",
                    dash="shelf", cluster="box", wheel="two", seats="deckchair", handbrake="lever", transfer=True, radio=False,
                    colors=dict(dash=(0.20, 0.20, 0.22), pad=(0.20, 0.20, 0.22), seat=(0.52, 0.40, 0.30),
                                seat2=(0.62, 0.48, 0.34), door=(0.24, 0.24, 0.26), metal=(0.30, 0.30, 0.32))),
    # Small French 4x4 of the 70s/80s: tan plastic, a single-spoke wheel, orange corduroy, umbrella handbrake.
    "Baguette": dict(game="Baguette", side=-1, character="French 70s: single-spoke wheel, tan plastic, orange corduroy",
                     dash="plastic", cluster="wide", wheel="single", seats="bucket", seat_pattern="ribs", handbrake="pull",
                     transfer=False,
                     colors=dict(dash=(0.64, 0.56, 0.44), pad=(0.54, 0.46, 0.36), panel=(0.18, 0.17, 0.16),
                                 seat=(0.80, 0.44, 0.18), seat2=(0.88, 0.54, 0.24), door=(0.60, 0.52, 0.40),
                                 rim=(0.20, 0.19, 0.18), spoke=(0.20, 0.19, 0.18))),
    # Unimog 406 double cab: flat dash, dials in the middle, a near-flat big wheel and a forest of levers.
    "Mammoth": dict(game="Mammoth", side=-1, character="Unimog: big flat wheel, dials in the middle, a forest of levers",
                    dash="flat", cluster="center", wheel="bus", wheel_r=0.23, wheel_tilt=55, seats="headrest", handbrake="lever",
                    dials="olive", radio=False, features=["fire_extinguisher"],
                    extra_levers=[(0.15, "knob3"), (0.20, "knob2"), (0.25, "knob")],
                    colors=dict(seat=(0.24, 0.24, 0.26), seat2=(0.32, 0.32, 0.34), panel=(0.20, 0.20, 0.20),
                                rim=(0.14, 0.14, 0.15), spoke=(0.14, 0.14, 0.15))),
    # Land Rover 101 Forward Control: cab-over, engine box between the seats, flat wheel, dials in the middle. RHD.
    "Marshal": dict(game="Marshal", side=1, character="Forward Control: engine box between the seats, flat wheel, sand paint",
                    dash="flat", cluster="center", wheel="three", wheel_r=0.22, wheel_tilt=55, seats="bucket", handbrake="lever",
                    dials="olive", radio=False, features=["vent_flaps"], tunnel=False,
                    colors=dict(dash=(0.66, 0.58, 0.40), seat=(0.30, 0.31, 0.24), seat2=(0.38, 0.39, 0.30),
                                rim=(0.16, 0.16, 0.18), spoke=(0.16, 0.16, 0.18))),
    # Mercedes T2 "Düdo" camper: bus wheel, tall dash, engine cover, a checked curtain behind the seats.
    "RustOx": dict(game="RustOx", side=-1, character="Mercedes camper van: bus wheel, engine box, checked curtain behind you",
                   dash="plastic", cluster="binnacle", wheel="bus", wheel_r=0.22, wheel_tilt=50, seats="headrest",
                   handbrake="lever", features=["engine_cover", "curtain"], tunnel=False, transfer=False,
                   colors=dict(dash=(0.86, 0.84, 0.78), pad=(0.30, 0.30, 0.32), seat=(0.24, 0.40, 0.48),
                               seat2=(0.30, 0.48, 0.56), accent=(0.92, 0.50, 0.22), door=(0.80, 0.78, 0.72),
                               rim=(0.16, 0.16, 0.18), spoke=(0.16, 0.16, 0.18))),
}
