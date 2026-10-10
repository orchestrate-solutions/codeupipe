import { existsSync, realpathSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";

/**
 * The path with each symbolic link followed, also for a path that is not
 * there yet: the part that exists is followed, and the rest is added.
 *
 * A relative import is correct only between two such paths, because the
 * module loader follows the links before it reads the import.
 */
export function realPath(path: string): string {
  const absolute = resolve(path);
  if (existsSync(absolute)) return realpathSync(absolute);
  const parent = dirname(absolute);
  return parent === absolute ? absolute : join(realPath(parent), basename(absolute));
}
