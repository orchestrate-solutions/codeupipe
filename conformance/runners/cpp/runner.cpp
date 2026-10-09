// C++ conformance runner: executes cases, reports what happened.
//
//   c++ -std=c++20 -O2 -I runtimes/cpp/include runner.cpp -o runner
//   ./runner < cases.json > results.json
//
// Mirrors conformance/runners/python/runner.py; conformance/run.py judges.
// Dependency-free on purpose (the runtime is header-only), so it carries a
// small JSON reader/writer for cup::Value.
//
// Uses only the API contract's operations (conformance/API.md).
#include <map>
#include <codeupipe/codeupipe.hpp>

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using cup::Payload;
using cup::Value;
using cup::ValueList;
using cup::ValueMap;

// --------------------------------------------------------------------------
// JSON <-> cup::Value
// --------------------------------------------------------------------------

struct Reader {
    const std::string& s;
    std::size_t i = 0;

    void ws() { while (i < s.size() && std::isspace(static_cast<unsigned char>(s[i]))) ++i; }
    char peek() { ws(); return i < s.size() ? s[i] : '\0'; }
    void expect(char c) {
        if (peek() != c) throw std::runtime_error(std::string("json: expected ") + c);
        ++i;
    }

    Value value() {
        char c = peek();
        if (c == '{') return object();
        if (c == '[') return array();
        if (c == '"') return Value(string());
        if (c == 't') { i += 4; return Value(true); }
        if (c == 'f') { i += 5; return Value(false); }
        if (c == 'n') { i += 4; return Value(nullptr); }
        return number();
    }

    ValueMap object() {
        ValueMap m;
        expect('{');
        if (peek() == '}') { ++i; return m; }
        while (true) {
            std::string k = string();
            expect(':');
            m.insert_or_assign(k, value());
            if (peek() == ',') { ++i; continue; }
            expect('}');
            return m;
        }
    }

    ValueList array() {
        ValueList l;
        expect('[');
        if (peek() == ']') { ++i; return l; }
        while (true) {
            l.push_back(value());
            if (peek() == ',') { ++i; continue; }
            expect(']');
            return l;
        }
    }

    std::string string() {
        expect('"');
        std::string out;
        while (s[i] != '"') {
            char c = s[i++];
            if (c != '\\') { out += c; continue; }
            char e = s[i++];
            switch (e) {
                case 'n': out += '\n'; break;
                case 't': out += '\t'; break;
                case 'r': out += '\r'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'u': {
                    unsigned cp = std::stoul(s.substr(i, 4), nullptr, 16);
                    i += 4;
                    if (cp < 0x80) out += static_cast<char>(cp);
                    else if (cp < 0x800) { out += static_cast<char>(0xC0 | (cp >> 6)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
                    else { out += static_cast<char>(0xE0 | (cp >> 12)); out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F)); out += static_cast<char>(0x80 | (cp & 0x3F)); }
                    break;
                }
                default: out += e;
            }
        }
        ++i;
        return out;
    }

    Value number() {
        ws();
        std::size_t start = i;
        bool integral = true;
        while (i < s.size() && (std::isdigit(static_cast<unsigned char>(s[i])) || s[i] == '-' || s[i] == '+'
                                || s[i] == '.' || s[i] == 'e' || s[i] == 'E')) {
            if (s[i] == '.' || s[i] == 'e' || s[i] == 'E') integral = false;
            ++i;
        }
        std::string text = s.substr(start, i - start);
        if (integral) return Value(static_cast<std::int64_t>(std::stoll(text)));
        return Value(std::stod(text));
    }
};

void write(std::ostream& o, const Value& v);

void write_string(std::ostream& o, const std::string& s) {
    o << '"';
    for (char c : s) {
        switch (c) {
            case '"': o << "\\\""; break;
            case '\\': o << "\\\\"; break;
            case '\n': o << "\\n"; break;
            case '\t': o << "\\t"; break;
            case '\r': o << "\\r"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); o << b; }
                else o << c;
        }
    }
    o << '"';
}

void write(std::ostream& o, const Value& v) {
    if (v.is_null()) o << "null";
    else if (auto b = v.as_bool()) o << (*b ? "true" : "false");
    else if (auto n = v.as_int()) o << *n;
    else if (auto d = v.as_float()) { char buf[32]; std::snprintf(buf, sizeof buf, "%.17g", *d); o << buf; }
    else if (auto s = v.as_string()) write_string(o, *s);
    else if (auto l = v.as_list()) {
        o << '[';
        for (std::size_t k = 0; k < l->size(); ++k) { if (k) o << ','; write(o, (*l)[k]); }
        o << ']';
    } else if (auto m = v.as_map()) {
        o << '{';
        bool first = true;
        for (const auto& [key, val] : *m) { if (!first) o << ','; first = false; write_string(o, key); o << ':'; write(o, val); }
        o << '}';
    }
}

// --------------------------------------------------------------------------
// reference vocabulary
// --------------------------------------------------------------------------

struct Unsupported : std::runtime_error { using std::runtime_error::runtime_error; };

std::string str(const ValueMap& m, const char* key) {
    auto it = m.find(key);
    return (it != m.end() && it->second.as_string()) ? *it->second.as_string() : std::string{};
}
Value field(const ValueMap& m, const char* key) {
    auto it = m.find(key);
    return it != m.end() ? it->second : Value{};
}

Value plus(const Value& a, const Value& b) {
    if (a.as_int() && b.as_int()) return Value(*a.as_int() + *b.as_int());
    auto num = [](const Value& v) { return v.as_int() ? static_cast<double>(*v.as_int()) : v.as_float().value_or(0.0); };
    return Value(num(a) + num(b));
}

bool truthy(const Value& v) {
    if (v.is_null()) return false;
    if (auto b = v.as_bool()) return *b;
    if (auto n = v.as_int()) return *n != 0;
    if (auto d = v.as_float()) return *d != 0.0;
    if (auto s = v.as_string()) return !s->empty();
    if (auto l = v.as_list()) return !l->empty();
    if (auto m = v.as_map()) return !m->empty();
    return true;
}

ValueList taps;
std::vector<std::string> hooks;

// One named type per operation, in a named namespace: a step is identified by
// its type (conformance/API.md, "Step identity"); lambdas have none. add_* are
// templates over the concrete type, so the JSON op is dispatched to a type by
// the with_* helpers below.
namespace conf {
struct SetOp final : cup::IFilter {
    std::string key; Value value;
    SetOp(std::string k, Value v) : key(std::move(k)), value(std::move(v)) {}
    Payload call(const Payload& p) override { return p.insert(key, value); }
};
struct CopyOp final : cup::IFilter {
    std::string from, to;
    CopyOp(std::string f, std::string t) : from(std::move(f)), to(std::move(t)) {}
    Payload call(const Payload& p) override { return p.insert(to, p.get(from)); }
};
struct AddOp final : cup::IFilter {
    std::string key; Value by;
    AddOp(std::string k, Value b) : key(std::move(k)), by(std::move(b)) {}
    Payload call(const Payload& p) override { return p.insert(key, plus(p.get(key, Value(0)), by)); }
};
struct RemoveOp final : cup::IFilter {
    std::string key;
    RemoveOp(std::string k) : key(std::move(k)) {}
    Payload call(const Payload& p) override { return p.remove(key); }
};
struct MergeOp final : cup::IFilter {
    ValueMap other;
    MergeOp(ValueMap o) : other(std::move(o)) {}
    Payload call(const Payload& p) override { return p.merge(Payload(other)); }
};
struct HasOp final : cup::IFilter {
    std::string key, to;
    HasOp(std::string k, std::string t) : key(std::move(k)), to(std::move(t)) {}
    Payload call(const Payload& p) override { return p.insert(to, Value(p.has(key))); }
};
struct MutateOp final : cup::IFilter {
    std::string key; Value value;
    MutateOp(std::string k, Value v) : key(std::move(k)), value(std::move(v)) {}
    Payload call(const Payload& p) override {
        auto m = p.with_mutation();
        m.set(key, value);
        return m.to_immutable();
    }
};
struct AppendOp final : cup::IFilter {
    std::string key; Value value;
    AppendOp(std::string k, Value v) : key(std::move(k)), value(std::move(v)) {}
    Payload call(const Payload& p) override {
        Value cur = p.get(key);
        ValueList next = cur.as_list() ? *cur.as_list() : ValueList{};
        next.push_back(value);
        return p.insert(key, Value(std::move(next)));
    }
};
struct FailOp final : cup::IFilter {
    std::string message;
    FailOp(std::string m) : message(std::move(m)) {}
    Payload call(const Payload&) override { throw std::runtime_error(message); }
};
struct RecordTap final : cup::ITap {
    std::string key;
    RecordTap(std::string k) : key(std::move(k)) {}
    void observe(const Payload& p) override { taps.push_back(p.get(key)); }
};
struct FailTap final : cup::ITap {
    std::string message;
    FailTap(std::string m) : message(std::move(m)) {}
    void observe(const Payload&) override { throw std::runtime_error(message); }
};
struct NoopTap final : cup::ITap {
    void observe(const Payload&) override {}
};
/// Predicate objects (conformance/API.md, "Valve"): test(), the case's
/// condition in members.
struct EqualsWhen {
    std::string key; Value want;
    bool test(const Payload& p) const { return p.get(key) == want; }
};
struct TruthyWhen {
    std::string key;
    bool test(const Payload& p) const { return truthy(p.get(key)); }
};
/// The runner's named pipeline type: only Pipeline subclasses can be nested.
struct Nested : cup::Pipeline {};
}  // namespace conf

/// Hand the op described by `spec`, as its concrete type, to `sink`.
template <typename Sink>
void with_op(const ValueMap& spec, Sink&& sink) {
    std::string op = str(spec, "op");
    if (op == "set") return sink(conf::SetOp(str(spec, "key"), field(spec, "value")));
    if (op == "copy") return sink(conf::CopyOp(str(spec, "from"), str(spec, "to")));
    if (op == "add") return sink(conf::AddOp(str(spec, "key"), field(spec, "by")));
    if (op == "remove") return sink(conf::RemoveOp(str(spec, "key")));
    if (op == "merge") return sink(conf::MergeOp(*field(spec, "value").as_map()));
    if (op == "has") return sink(conf::HasOp(str(spec, "key"), str(spec, "to")));
    if (op == "mutate") return sink(conf::MutateOp(str(spec, "key"), field(spec, "value")));
    if (op == "append") return sink(conf::AppendOp(str(spec, "key"), field(spec, "value")));
    if (op == "fail") return sink(conf::FailOp(str(spec, "message")));
    throw Unsupported("unknown filter op " + op);
}

template <typename Sink>
void with_predicate(const ValueMap& when, Sink&& sink) {
    std::string op = str(when, "op"), key = str(when, "key");
    if (op == "equals") return sink(conf::EqualsWhen{key, field(when, "value")});
    if (op == "truthy") return sink(conf::TruthyWhen{key});
    throw Unsupported("unknown valve op " + op);
}


struct RecordHook : cup::IHook {
    void before(const std::string& step, const Payload&) override { hooks.push_back("before:" + step); }
    void after(const std::string& step, const Payload&) override { hooks.push_back("after:" + step); }
    void on_error(const std::string& step, const std::exception&, const Payload&) override { hooks.push_back("error:" + step); }
};

void build(cup::Pipeline& p, const ValueList& steps) {
    for (const auto& step_value : steps) {
        const ValueMap& s = *step_value.as_map();
        std::string kind = str(s, "kind");
        if (kind == "filter") with_op(s, [&](auto op) { p.add_filter(std::move(op)); });
        else if (kind == "valve")
            with_op(*field(s, "filter").as_map(), [&](auto op) {
                with_predicate(*field(s, "when").as_map(), [&](auto when) {
                    p.add_filter(cup::Valve(std::move(op), std::move(when)));
                });
            });
        else if (kind == "tap") {
            if (str(s, "op") == "noop") p.add_tap(conf::NoopTap{});
            else if (str(s, "op") == "fail") p.add_tap(conf::FailTap(str(s, "message")));
            else p.add_tap(conf::RecordTap(str(s, "key")));
        } else if (kind == "pipeline") {
            conf::Nested child;
            build(child, *field(s, "steps").as_list());
            p.add_pipeline(std::move(child));
        } else throw Unsupported("unknown step kind " + kind);
    }
}

// Steps are identified by their type (conformance/API.md); the cases name
// them. Each case step adds one pipeline step, in order, so identities map
// back to case names; one this map does not know stays and fails the check.
std::map<std::string, std::string> label;

std::string named(const std::string& identity) {
    auto it = label.find(identity);
    return it == label.end() ? identity : it->second;
}

void write_names(std::ostream& o, const std::vector<std::string>& names) {
    o << '[';
    for (std::size_t k = 0; k < names.size(); ++k) { if (k) o << ','; write_string(o, named(names[k])); }
    o << ']';
}

void run_case(std::ostream& o, const ValueMap& c) {
    taps.clear();
    hooks.clear();
    std::string id = str(c, "id");
    const ValueMap input = field(c, "input").as_map() ? *field(c, "input").as_map() : ValueMap{};
    cup::Pipeline p;
    o << "{\"id\":"; write_string(o, id);
    try {
        build(p, *field(c, "steps").as_list());
    } catch (const Unsupported& e) {
        o << ",\"unsupported\":"; write_string(o, e.what()); o << '}';
        return;
    }
    label.clear();
    {
        const auto ids = p.identities();
        const Value steps_value = field(c, "steps");  // keep it alive: as_list() points into it
        const auto& case_steps = *steps_value.as_list();
        for (std::size_t k = 0; k < ids.size(); ++k) label[ids[k]] = str(*case_steps[k].as_map(), "name");
    }
    bool with_hooks = field(c, "hooks").as_bool().value_or(false);  // true = record; "noop" is bench-only
    if (with_hooks) p.use_hook(std::make_unique<RecordHook>());
    try {
        Payload out = p.run(Payload(input));
        o << ",\"output\":"; write(o, Value(out.to_dict()));
    } catch (const std::exception& e) {
        o << ",\"error\":"; write_string(o, std::string("runtime_error: ") + e.what());
    }
    const auto& st = p.state();
    std::vector<std::string> error_names;
    for (const auto& e : st.errors) error_names.push_back(e.name);
    o << ",\"state\":{\"executed\":"; write_names(o, st.executed);
    o << ",\"skipped\":"; write_names(o, st.skipped);
    o << ",\"errors\":"; write_names(o, error_names); o << '}';
    o << ",\"taps\":"; write(o, Value(taps));
    if (with_hooks) {
        o << ",\"hooks\":[";
        for (std::size_t k = 0; k < hooks.size(); ++k) {
            if (k) o << ',';
            const auto at = hooks[k].find(':');
            write_string(o, hooks[k].substr(0, at + 1) + named(hooks[k].substr(at + 1)));
        }
        o << ']';
    }
    o << ",\"input_after\":"; write(o, Value(input));
    o << '}';
}

// Best of 5 x 20,000 runs after 20,000 warmup runs, in µs per run.
void bench_case(std::ostream& o, const ValueMap& c) {
    constexpr int warmup = 20000, runs = 20000, repeats = 5;
    cup::Pipeline p;
    build(p, *field(c, "steps").as_list());
    const auto* hooks_s = field(c, "hooks").as_string();
    if (hooks_s && *hooks_s == "noop") p.use_hook(std::make_unique<cup::IHook>());
    const ValueMap input = field(c, "input").as_map() ? *field(c, "input").as_map() : ValueMap{};
    Payload out = p.run(Payload(input));
    for (int i = 0; i < warmup; ++i) (void)p.run(Payload(input));
    auto best = std::chrono::steady_clock::duration::max();
    for (int r = 0; r < repeats; ++r) {
        auto t0 = std::chrono::steady_clock::now();
        for (int i = 0; i < runs; ++i) (void)p.run(Payload(input));
        best = std::min(best, std::chrono::steady_clock::now() - t0);
    }
    double us = std::chrono::duration<double, std::micro>(best).count() / runs;
    o << "{\"id\":"; write_string(o, str(c, "id"));
    o << ",\"us_per_run\":" << us;
    o << ",\"output\":"; write(o, Value(out.to_dict()));
    o << '}';
}

int main(int argc, char** argv) {
    const bool bench = argc > 1 && std::string(argv[1]) == "bench";
    std::string text((std::istreambuf_iterator<char>(std::cin)), std::istreambuf_iterator<char>());
    Reader r{text};
    ValueList cases = r.array();
    std::cout << '[';
    for (std::size_t k = 0; k < cases.size(); ++k) {
        if (k) std::cout << ',';
        if (bench) bench_case(std::cout, *cases[k].as_map());
        else run_case(std::cout, *cases[k].as_map());
    }
    std::cout << ']';
    return 0;
}
