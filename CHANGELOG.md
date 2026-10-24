# OTH Cockpit: changes

Version numbers: `0.MINOR.PATCH-alpha` while it's an alpha.
MINOR goes up for a new feature or a bigger rework (all cockpits rebuilt, mirrors, customisation),
PATCH for fixes only. 1.0.0 when every car is finished and it leaves alpha.

## Planned

- 0.4.0: working mirrors
- 0.5.0: customise the interior
- 1.0.0: out of alpha

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
