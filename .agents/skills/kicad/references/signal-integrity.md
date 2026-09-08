# High-speed signal integrity and differential pairs

Deriving an enforceable skew and impedance number instead of copying one from another project. The everyday layout
rules live in [SKILL.md](../SKILL.md).

---

### What a differential pair actually is

Two tracks carrying one signal as the voltage difference between them, rather than each track carrying its own
signal referenced to ground. USB, Ethernet, LVDS, CAN, and RS-485 all use this because a matched pair rejects
common-mode noise, interference picked up equally by both tracks, far better than a single ground-referenced track.

---

### There is no universal length-matching figure

The tolerable length mismatch between the two tracks of a pair, called skew, is set by the signalling rate of the
interface and by how much of that interface's own timing budget the board may spend. A skew that is irrelevant on
RS-485 at a few megabits per second breaks a multi-gigabit link outright, because what matters is skew as a fraction
of the unit interval, the time one bit occupies at the link's data rate. Never skew in millimetres copied from
somewhere else.

Derive the number in three steps.

1. Read the interface's own specification for its data rate and, where it states one, its own maximum intra-pair
   skew. Some interface specifications publish an explicit limit in their electrical chapter. Where one does not,
   fall back on the general relationship that timing skew between the two lines converts part of the intended
   differential signal into unwanted common-mode noise, roughly in proportion to skew divided by rise time.
2. Convert that time budget into a physical length using the propagation velocity of the actual stackup and layer
   the pair runs on, not a generic PCB propagation figure. Propagation velocity depends on the effective dielectric
   constant the trace actually sees, v = c / sqrt(eps_eff), a single number blending how much of the trace's electric
   field sits inside the board material versus in the air above it for a surface trace over a pour (microstrip), or
   sits entirely inside the board material for a trace buried between two reference planes (stripline). IPC-2141A,
   Design Guide for High-Speed Controlled Impedance Circuit Boards, gives the standard delay approximations:
   roughly 1.017 x sqrt(0.475 er + 0.67) nanoseconds per inch for microstrip, and roughly 1.017 x sqrt(er)
   nanoseconds per inch for stripline, where er is the substrate's own dielectric constant read off the laminate
   datasheet.
3. Apply a derating factor before the number becomes the one a check enforces. No IPC or IEEE standard publishes one
   universal derating percentage: it is settled engineering convention, and the convention varies by how much risk
   the project carries. Keeping skew inside roughly 10 percent of the available timing budget is the commonly used
   conservative choice. A looser budget of up to roughly 25 percent shows up when board area is genuinely
   constrained and the interface's own timing margin can absorb it. Neither figure is mandated anywhere. The
   underlying physical justification, that skew converts to common-mode noise in rough proportion to the
   skew-to-rise-time ratio, is discussed in Johnson and Graham, High-Speed Digital Design: A Handbook of Black Magic
   (Prentice Hall, 1993).

Whichever factor is chosen belongs inside the enforced number itself, the netclass rule or the design-rule
constraint, never only in a comment or a paragraph of prose next to the tool. A margin that nothing enforces gets
silently consumed the first time a router pass or a hand edit nudges a track.

---

### Routed by hand and locked, or autorouted and measured

Neither path is inherently correct. General-purpose autorouters do not implement dedicated differential-pair length
matching: natural skew after autorouting depends entirely on how symmetric the placement is and on whichever path
the router happened to find. An autorouted pair's as-built length has to be measured on the real routed copper and
checked against the derived tolerance before the board is finished, never assumed to match because the router
"should" have kept it close.

KiCad's interactive router includes a dedicated length-tuning mode built for exactly this problem, because a general
path-finding algorithm does not solve for skew on its own. Use it for the hand-routed path, then lock the pair.

---

### Target impedance

Specify a target impedance for every high-speed pair or single-ended trace in the board stackup, and configure the
trace-width calculator to hit it:

| Interface | Target |
|---|---|
| USB 2.0 full-speed and high-speed | 90 ohm differential |
| RF and SMA traces | 50 ohm single-ended |
| LVDS | 100 ohm differential |

Keep return paths short: every high-speed signal trace needs an unbroken ground reference plane immediately below
it, with no slot or cut interrupting the return current. Add series termination resistors of 33 to 47 ohm at the
source end of high-speed single-ended traces to damp reflections.
