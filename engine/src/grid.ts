// The chainage grid every output array lives on: point i is at min(i * step, length), from chainage 0, for i in
// 0 .. floor(length / step) (as railsim's rail_grid, railsim/metro_profile.py 1010). A length within GRID_SLACK of
// a whole number of steps gets that last point, so floating division never drops it.

import { GRID_SLACK } from "./tol.ts";

/** The number of grid points over a section of this length. */
export function gridSize(length: number, step: number): number {
  return Math.floor(length / step + GRID_SLACK) + 1;
}

/** The chainage of grid point i. */
export function gridChainage(i: number, step: number, length: number): number {
  return Math.min(i * step, length);
}

/** The nearest grid index at or below chainage c, held to the grid. */
export function gridIndex(c: number, step: number, n: number): number {
  return Math.max(0, Math.min(n - 1, Math.floor(c / step + GRID_SLACK)));
}
