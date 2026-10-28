import type { Finding } from "./finding.ts";
import { position } from "./source.ts";
import type { Source } from "./source.ts";
import type ts from "typescript";

export const PARSE_ERROR = "CUP-I000";
export const FUNCTION_STEP = "CUP-A001";
export const NAMED_FUNCTION_STEP = "CUP-A002";
export const LOCAL_TYPE_STEP = "CUP-A003";
export const UNNAMED_PIPELINE = "CUP-A005";
export const FUNCTION_PREDICATE = "CUP-A008";
export const OBJECT_LITERAL_STEP = "CUP-A009";
export const STATE_READ = "CUP-I003";
export const WRITE_OUTSIDE_FILTER = "CUP-I004";
export const ONE_PRIMITIVE_PER_FILE = "CUP-I005";
export const PRIMITIVE_FILE_NAME = "CUP-I006";
export const PRIMITIVE_ROLE_SUFFIX = "CUP-I007";
export const LOGIC_OUTSIDE_PRIMITIVE = "CUP-I008";
export const MARKER_ALLOWS_NOTHING = "CUP-I009";

/** The rules whose findings are warnings. */
export const WARNINGS = new Set([LOGIC_OUTSIDE_PRIMITIVE, MARKER_ALLOWS_NOTHING]);

/** Rule id to its short name. The ids and names are those of the Python linter, where it has the rule. */
export const RULES: Record<string, string> = {
  [PARSE_ERROR]: "parse-error",
  [FUNCTION_STEP]: "lambda-step",
  [NAMED_FUNCTION_STEP]: "local-function-step",
  [LOCAL_TYPE_STEP]: "local-type-step",
  [UNNAMED_PIPELINE]: "unnamed-pipeline-step",
  [FUNCTION_PREDICATE]: "function-predicate",
  [OBJECT_LITERAL_STEP]: "object-literal-step",
  [STATE_READ]: "state-read-in-step",
  [WRITE_OUTSIDE_FILTER]: "write-outside-filter",
  [ONE_PRIMITIVE_PER_FILE]: "one-primitive-per-file",
  [PRIMITIVE_FILE_NAME]: "primitive-file-name",
  [PRIMITIVE_ROLE_SUFFIX]: "primitive-role-suffix",
  [LOGIC_OUTSIDE_PRIMITIVE]: "logic-outside-primitive",
  [MARKER_ALLOWS_NOTHING]: "marker-allows-nothing",
};

const NAMED_CLASS = "Define it at module level as a named class (a Valve predicate: a class with test(payload)) "
  + "so it has a name in State and can be tested on its own.";

const FIX: Record<string, string> = {
  [PARSE_ERROR]: "Fix the syntax error so the file can be checked.",
  [FUNCTION_STEP]: NAMED_CLASS,
  [NAMED_FUNCTION_STEP]: NAMED_CLASS,
  [LOCAL_TYPE_STEP]: NAMED_CLASS,
  [OBJECT_LITERAL_STEP]: NAMED_CLASS,
  [UNNAMED_PIPELINE]: "A nested pipeline must be a named pipeline type (class UserOnboarding extends Pipeline), "
    + "named like a filter. A plain Pipeline can only run at the top level.",
  [FUNCTION_PREDICATE]: "Valve predicates are objects (conformance/API.md, \"Valve\"): wrap the condition in a "
    + "named class with test(payload), configuration on the instance, and pass an instance.",
  [STATE_READ]: "A Filter's result and a Valve's decision must depend only on the Payload. Put what the step "
    + "needs into the Payload, or observe State from a Tap or a Hook.",
  [WRITE_OUTSIDE_FILTER]: "Only a Filter writes to the Payload, and nothing at run time stops this write. "
    + "Put the write in a Filter, or write to payload.copy().",
  [ONE_PRIMITIVE_PER_FILE]: "Give each Filter, Predicate, Tap, Hook and named Pipeline its own file, so it can "
    + "be tested alone and used again. The pipeline file is where they come together.",
  [PRIMITIVE_FILE_NAME]: "The file name of a primitive is its class name in kebab-case, so one name gives the other.",
  [PRIMITIVE_ROLE_SUFFIX]: "A primitive's class name ends with its role (Filter, Tap, Hook, Predicate, "
    + "Pipeline), so the name tells what the class is.",
  [LOGIC_OUTSIDE_PRIMITIVE]: "Write it as a primitive, so that the pipeline has the logic and it can be tested as a step. "
    + "For logic that must be plain code, say why: // cup: allow-plain <reason>",
  [MARKER_ALLOWS_NOTHING]: "Remove it, or put it on the line of the finding that it is for. A comment that allows nothing "
    + "says that the code has an exception that it does not have.",
};

/** What to do about a finding of `rule`. */
export function fixOf(rule: string): string {
  return FIX[rule] ?? "";
}

/** A Finding at `node`. Its message reads `<what>. <fix>`. */
export function makeFinding(source: Source, node: ts.Node, rule: string, what: string, callNode?: ts.Node): Finding {
  const { line, col } = position(source, node);
  const finding: Finding = { path: source.path, line, col, rule, slug: RULES[rule] ?? "", message: `${what}. ${FIX[rule]}` };
  if (WARNINGS.has(rule)) finding.severity = "warning";
  if (callNode !== undefined) {
    const callLine = position(source, callNode).line;
    if (callLine !== line) finding.callLine = callLine;
  }
  return finding;
}
