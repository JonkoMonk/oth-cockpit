# OTH Cockpit: changes

Version numbers: `0.MINOR.PATCH-alpha` while it's an alpha.
MINOR goes up for a new feature or a bigger rework (all cockpits rebuilt, mirrors, customisation),
PATCH for fixes only. 1.0.0 when every car is finished and it leaves alpha.

## Planned

- 0.5.0: customise the interior
- 1.0.0: out of alpha

## 0.4.0-alpha (2026-11-06; includes 0.3.1)

- Known: the rear-view mirror looks too far down.
- Works again with the game's 26.10.30 update (the cockpit view would not switch on at all, because the game
  replaced its headlight switch with Off/Low/High beams). The headlight lamp follows the new beams.
- Working mirrors: the rear-view mirror and the car's own side mirrors show what's behind you, and the
  picture moves like a real mirror when you move or turn your head. `[Mirrors] Quality`: Low (only the
  rear-view mirror, for slow PCs), Medium (default), High, Ultra, or Custom. The rear-view mirror shows the
  road behind the car (`[Mirrors] RearView = Car` shows the cabin and out through the rear window instead).
- Solid A pillars: a trim piece with some depth over each windscreen pillar, shaped along the car's own
  pillar from the dash to the roof (the pillars looked like a thin flat line on many cars). Smooth shading,
  so it no longer shows light and dark stripes.
- Pillar trims reach the roof on cars where they stopped halfway (TrailRat, Brick, Marshal, Protector...),
  run a little further into the dash, and sit 3 cm further out on the DingDing and Burro (the dash corner
  showed under them).
- Side mirror glass follows the mirror's own shape (cut corners) instead of a rectangle.
- Brick: wider instrument panel; fuel and temperature gauges beside the big dials (they hung below the
  panel behind the wheel rim), warning lamps inside the panel.

## 0.3.1-alpha (released as part of 0.4.0)

- Windscreen pillars, window frames and roof edges: the game draws the car body from the outside only,
  so from the seat the car's own pillars were see-through and our stand-in pillar beside them looked like
  a second pillar with glass in between ("pillars not connected"), with see-through corners and gaps
  around the windscreen and in some roofs. Every car now gets inside copies of exactly those body parts
  (in the car's own colours), so from inside they look like they do from outside, and the stand-in
  pillar beams are gone. This also covers the TrailBurner's thin rod and the Protector's black strip by
  the A pillar.
- Burro: the clipboard and gloves sank half into the dashboard. The dash top is now level where the tray
  is, and a logbook that fits the tray lies there with the gloves.
- Loose props on every car (maps, mugs, gloves, the thermos, compass, toolbox, picnic basket, the
  Baguette's loaf) are now dropped onto whatever is under them when the cockpit is built, so none sink
  into the dash or float above it.

## 0.3.0-alpha (2026-10-24), first public release

- Pedals: the pads were tilted around the top of the pedal and ended up inside the firewall (only
  the arms showed). They now hang in the footwell, clear of the firewall even fully pressed, with a
  metal plate so they show against dark floor mats.
- Wipers: the car's own wipers are drawn from the outside only; every car (except the DingDing,
  which has its own) now gets copies facing inwards, so you no longer look through them. All of
  each wiper is copied: blade, arm, end caps and pivot.
- Door tops: the black rubber along the bottom and top of the side windows stuck out past the door
  lining as a black strip; it is now covered in the door's colour. The side windows also reach a
  centimetre or two down into the door and up into the roof edge, and stood in front of the lining
  there as a thin dark line along the door top; the lining now steps in past the glass.
- Sound: in the cockpit the car's own sound came almost only from one side (the right in left-hand
  drive cars). You now hear from closer to the middle of the car, so it's in both ears, still a
  little from the side. `[Sound] EarsToCentre` in the settings file sets how far (0 to 1).
- Side walls, door cards and roof edges follow the shape of the body (they lean in where the body
  leans in) instead of standing straight at one width. Things mounted on the outside, like side
  jerrycans, no longer show inside the cabin.

## 0.2.1 (2026-10-24, not released)

- Every car's dials, warning lights and gear display cleared of the steering wheel (nothing hidden
  at the standard seat height and 2 cm above or below it), keeping each car's own layout.
- TrailBurner (Blazer): charcoal dash with saddle-tan seats instead of all blue.

## 0.2.0 (2026-10-20, not released)

- New cockpits for all 23 cars in the game's own style, each with the character of the real
  vehicle it is based on.

## 0.1.0 (2026-10-18, not released)

- First cockpits, link with the wheel mod (the cockpit's steering wheel turns like yours).
