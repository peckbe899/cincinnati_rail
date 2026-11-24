// The sheet's static layer (speed): the bands at the bottom of the band order that no edit of the draft changes (the
// plot's grid, the water, the ground, the ground works, the other systems, the crossings, the locks) drawn once into
// a bitmap and copied under the moving bands on each frame. Before, every frame of a whole-line drag on a
// deviceScaleFactor 2 screen drew them again, 15 of its 40 ms of raster. The bitmap is drawn again when anything
// they read changes: the canvas size, the view, the solve, the section input, the units or the Show choice.

/** The band ids that read only the view, the section input's ground, the solve and its input. */
export const STATIC_BANDS: ReadonlySet<string> = new Set([
  "axes",
  "water",
  "ground",
  "ground-works",
  "context",
  "crossings",
  "locks",
]);

/** How many bands at the head of the order are static: only a leading run, so the copy under the rest draws the
 * same picture as every band in order. */
export function staticPrefix(list: readonly { id: string; axis?: string }[]): number {
  let n = 0;
  while (n < list.length && STATIC_BANDS.has((list[n] as { id: string }).id) && list[n]?.axis !== "strip") n++;
  return n;
}

/** Two keys equal member by member (numbers and strings by value, objects by identity). */
export function sameKey(a: readonly unknown[] | null, b: readonly unknown[]): boolean {
  if (!a || a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (!Object.is(a[i], b[i])) return false;
  return true;
}

export interface LayerCanvas {
  width: number;
  height: number;
  getContext(kind: "2d"): CanvasRenderingContext2D | null;
}

/** A bitmap of the static bands with what they reported (texts and marks), drawn again when its key changes. */
export class StaticLayer<T> {
  private canvas: LayerCanvas | null = null;
  private key: readonly unknown[] | null = null;
  private kept: T | null = null;
  /** How many times the bitmap was drawn (the tests read it). */
  draws = 0;

  private readonly make: () => LayerCanvas;

  constructor(make: () => LayerCanvas) {
    this.make = make;
  }

  /**
   * Copy the bitmap for key into g (device pixels, wPx by hPx), drawing it first with draw(bg) when the key changed;
   * returns what draw returned when it last ran.
   */
  paint(
    g: CanvasRenderingContext2D,
    key: readonly unknown[],
    wPx: number,
    hPx: number,
    draw: (bg: CanvasRenderingContext2D) => T,
  ): T {
    this.canvas ??= this.make();
    const c = this.canvas;
    if (!sameKey(this.key, key) || c.width !== wPx || c.height !== hPx || this.kept === null) {
      if (c.width !== wPx || c.height !== hPx) {
        c.width = wPx;
        c.height = hPx;
      }
      const bg = c.getContext("2d");
      if (!bg) throw new Error("no 2D context for the static layer");
      bg.setTransform(1, 0, 0, 1, 0, 0);
      bg.clearRect(0, 0, wPx, hPx);
      this.kept = draw(bg);
      this.key = key;
      this.draws++;
    }
    g.save();
    g.setTransform(1, 0, 0, 1, 0, 0);
    // the canvas was cleared for this frame: a copy, not a blend, is the cheapest way to lay the bitmap down
    g.globalCompositeOperation = "copy";
    g.drawImage(c as unknown as CanvasImageSource, 0, 0);
    g.restore();
    return this.kept as T;
  }

  /** Forget the bitmap (the next paint draws it). */
  reset(): void {
    this.key = null;
    this.kept = null;
  }
}
