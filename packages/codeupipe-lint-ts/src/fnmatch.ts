/**
 * Whether `path` matches `pattern`, with the rules of a shell glob as
 * Python's fnmatch has them: `*` is any text (a `/` too), `?` is one
 * character, `[abc]` is one of the characters.
 */
export function fnmatch(path: string, pattern: string): boolean {
  let expression = "";
  for (let index = 0; index < pattern.length; index++) {
    const char = pattern[index] ?? "";
    if (char === "*") {
      expression += ".*";
    } else if (char === "?") {
      expression += ".";
    } else if (char === "[") {
      const end = pattern.indexOf("]", index + 1);
      if (end === -1) {
        expression += "\\[";
      } else {
        const body = pattern.slice(index + 1, end).replaceAll("\\", "\\\\");
        expression += "[" + (body.startsWith("!") ? "^" + body.slice(1) : body) + "]";
        index = end;
      }
    } else {
      expression += char.replace(/[.+^${}()|\\\]]/g, "\\$&");
    }
  }
  return new RegExp(`^${expression}$`, "s").test(path);
}
