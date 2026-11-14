# Native call map and evidence scope

Pinned OpenROAD: 0b54bb3203e0895f87940ff982358a6e4d406e28.
Source: src/rcx/src/extRCmodel.cpp. The instrumented copy and build commands
are saved under results/layout_offgrid_20261115/build; original source,
archives and installed executable are not modified.

- extDistRCTable::interpolate records the original measurement knots before
  creating the internal compute table (distance unit 4 in internal units).
- extDistWidthRCTable::getRC(mou,w,s) records requested and mapped width,
  requested distance, returned separation, coupling and fringe values.
  The same pointer and return value are passed back to the caller.
- extDistWidthRCTable::getFringeRC records index-based/infinite-distance
  requests separately. These are not finite off-grid interpolation queries.
- getWidthIndex maps widths to tabulated indices; getComputeRC applies
  first/last clamps, integer division into the compute grid, and special
  99/100 distance behavior. The returned separation is logged, not inferred.
- readRC scales rule distances by 1000*dbFactor and rule capacitance by
  1/dbFactor; dbFactor follows the pinned extractor's DBU convention.

The denominator covers these two instrumented capacitance getters. It does
not cover all extraction operations: five-argument diagonal, getRC_99,
last-width fringe, resistance, coupling assembly, or STA are outside the
call census. Net/segment IDs and lengths are not attached to these lower
level calls. Counts are call occurrence weights, not wire-length weights.
Source rules are matched by exact integer knot positions and scaled values;
ambiguous matches remain UNSUPPORTED. Rule-key resolution does not establish
material/physical equivalence with the CTF solver.

For each of the eight unchanged databases, run_native.py runs original and
instrumented executables and compares all SPEF electrical text after D_NET.
This establishes passive logging only when the recorded receipt passes.
