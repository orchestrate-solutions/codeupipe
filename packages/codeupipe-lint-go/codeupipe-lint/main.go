// Command codeupipe-lint checks Go code that uses codeupipe.
//
//	codeupipe-lint [--exclude GLOB] [--disable RULE] [--strict] [--config FILE] [--rules] [paths...]
//
// With no paths, they come from the lint section of cup.config.json. Exit
// code: 0 no findings, 1 findings, 2 a path could not be read or the
// arguments cannot be used. A warning does not make the exit code 1, unless
// --strict is given.
package main

import (
	"fmt"
	"os"
	"strings"

	codeupipelint "github.com/orchestrate-solutions/codeupipe/packages/codeupipe-lint-go"
)

// arguments are the options and the paths of the command.
type arguments struct {
	paths   []string
	exclude []string
	disable []string
	config  string
	rules   bool
	strict  bool
}

// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
func main() {
	code, err := run(os.Args[1:])
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(2)
	}
	os.Exit(code)
}

// run does the command. It gives the exit code, or an error for the
// arguments, the config file, or a path that cannot be used.
//
// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
func run(argv []string) (int, error) {
	args, err := parseArguments(argv)
	if err != nil {
		return 0, err
	}
	if args.rules {
		for _, rule := range codeupipelint.Rules {
			fmt.Printf("%s  %s\n", rule.ID, rule.Slug)
		}
		return 0, nil
	}
	if len(args.paths) == 0 {
		// The config file stands in for the arguments only when no paths are
		// given: a path that someone names is checked, whatever the file says.
		file := args.config
		if file == "" {
			file = codeupipelint.ConfigName
		}
		lint, err := codeupipelint.ReadLintConfig(file)
		if err != nil {
			return 0, err
		}
		if lint == nil {
			if args.config != "" {
				return 0, fmt.Errorf("%s: no such file", args.config)
			}
			lint = &codeupipelint.LintConfig{}
		}
		args.paths = lint.Paths
		if args.exclude == nil {
			args.exclude = lint.Exclude
		}
		if args.disable == nil {
			args.disable = lint.Disable
		}
	}
	if len(args.paths) == 0 {
		return 0, fmt.Errorf("give at least one path, or list them under lint.paths in %s", codeupipelint.ConfigName)
	}
	var unknown []string
	for _, id := range args.disable {
		if _, ok := codeupipelint.RuleOf(id); !ok {
			unknown = append(unknown, id)
		}
	}
	if len(unknown) > 0 {
		return 0, fmt.Errorf("no such rule: %s (the rules are listed by --rules)", strings.Join(unknown, ", "))
	}
	out, err := codeupipelint.LintPaths(args.paths, codeupipelint.LintOptions{
		Exclude: args.exclude,
		Disable: args.disable,
		Strict:  args.strict,
	})
	if err != nil {
		return 0, err
	}
	fmt.Println(out.Report)
	if out.ErrorReport != "" {
		fmt.Fprintln(os.Stderr, out.ErrorReport)
	}
	return out.ExitCode, nil
}

// parseArguments reads the options and the paths. An option takes its value
// from the same argument after "=", or from the next argument.
//
// cup: allow-plain the entry of the program: it reads the arguments, runs the pipeline and prints the result
func parseArguments(argv []string) (arguments, error) {
	var args arguments
	for at := 0; at < len(argv); at++ {
		arg := argv[at]
		name, inline, hasInline := strings.Cut(arg, "=")
		if !hasInline || !strings.HasPrefix(name, "--") {
			name, hasInline = arg, false
		}
		value := func() (string, error) {
			if hasInline {
				return inline, nil
			}
			at++
			if at >= len(argv) {
				return "", fmt.Errorf("option '%s' needs a value", name)
			}
			return argv[at], nil
		}
		switch name {
		case "--exclude":
			v, err := value()
			if err != nil {
				return args, err
			}
			args.exclude = append(args.exclude, v)
		case "--disable":
			v, err := value()
			if err != nil {
				return args, err
			}
			args.disable = append(args.disable, v)
		case "--config":
			v, err := value()
			if err != nil {
				return args, err
			}
			args.config = v
		case "--rules":
			args.rules = true
		case "--strict":
			args.strict = true
		default:
			if strings.HasPrefix(name, "--") {
				return args, fmt.Errorf("unknown option '%s'", name)
			}
			args.paths = append(args.paths, arg)
		}
	}
	return args, nil
}
