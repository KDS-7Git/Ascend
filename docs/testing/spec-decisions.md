# Specification decisions

The three specs describe one evolving product. The build milestones follow v3 §10.
The owner's latest instruction authorizes all phases sequentially, superseding the
older pauses between phases. This does not authorize publishing to an external registry.

- v1 §11's `11-03, 11-05` row says 3, but the retained v1 §8 algorithm returns 2.
  Tests use **2**: only logged days count; the bridged day adds zero.
- S/M/L use the reference bounds of 30/120/240 minutes. A 20-minute query can
  legitimately return no candidate and suggest splitting a node. An optional
  `minutes` field supplies a more precise estimate within its size bound.
- Main gates use milestones when present and all nodes otherwise. Proficiency
  packs require milestones; project packs support the original fallback.
- Pack review and executable-code trust are separate, content-bound decisions.
  Neither a draft's metadata nor a successful install grants execution trust.
- Runtime dependencies remain empty for the standalone CLI. Optional server,
  browser testing, and Web Push dependencies are installed only in their extras.

Tests were written before the Phase 1 implementation. The initial failing run is
retained in `phase-1-red.txt`; each milestone retains its complete test output.
