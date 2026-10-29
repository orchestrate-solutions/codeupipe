// Package codeupipe writes a program as a pipeline of small steps.
//
// A Payload carries the data. A Filter changes it, a Predicate asks a
// yes-or-no question about it, a Valve joins a Predicate to a Filter, a Tap
// reads it as it goes by, a Hook sees the lifecycle of a run, and State
// records what happened. A Pipeline runs the steps in order.
//
// The contract of these eight primitives is conformance/API.md in the
// repository. The Python, TypeScript and Rust runtimes have the same one,
// and the same conformance cases judge each of them.
//
// Each step method and Run take a context.Context first. The Pipeline gives
// it to each step and does nothing else with it: a cancelled context does
// not stop a run between steps.
package codeupipe
