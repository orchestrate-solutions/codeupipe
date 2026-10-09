// codeupipe/step_identity.hpp — Step identity (conformance/API.md, "Step identity")
//
// A step is identified by its type's qualified name, taken at compile time
// from the compiler's function signature (__PRETTY_FUNCTION__ on Clang/GCC,
// __FUNCSIG__ on MSVC): no RTTI needed, and nothing a minifier or stripper
// can touch. `add_*` are templates over the concrete step type.
//
// Refused at COMPILE time (static_assert), with a message naming the fix:
//   - lambdas and closures (a lambda is not an IFilter/ITap; as a Valve
//     predicate its type name says "lambda");
//   - function pointers as predicates (a function pointer's type is only its
//     signature: C++ free functions have no derivable name), so predicates,
//     like filters, are types: objects with test() (configuration in members);
//   - types in an anonymous namespace (the name is not unique across
//     translation units, and no other file can test them);
//   - a plain Pipeline nested as a step (nest a named subclass).
// A struct declared inside a function has an unqualified name on Clang that
// looks like a global type: the linter catches that one.

#pragma once

#include <string>
#include <string_view>
#include <type_traits>

namespace cup::detail {

template <typename T>
constexpr std::string_view raw_type_name() {
#if defined(__clang__)
    std::string_view p = __PRETTY_FUNCTION__;  // "... raw_type_name() [T = ns::Name]"
    const auto start = p.find("[T = ") + 5;
    return p.substr(start, p.rfind(']') - start);
#elif defined(__GNUC__)
    std::string_view p = __PRETTY_FUNCTION__;  // "... [with T = ns::Name; std::string_view = ...]"
    const auto start = p.find("[with T = ") + 10;
    const auto end = p.find_first_of(";]", start);
    return p.substr(start, end - start);
#elif defined(_MSC_VER)
    std::string_view p = __FUNCSIG__;  // "... raw_type_name<class ns::Name>(void)"
    auto start = p.find("raw_type_name<") + 14;
    const auto end = p.rfind(">(void)");
    for (std::string_view tag : {"class ", "struct ", "enum ", "union "}) {
        if (p.substr(start, tag.size()) == tag) { start += tag.size(); break; }
    }
    return p.substr(start, end - start);
#else
#error "codeupipe: step identity needs __PRETTY_FUNCTION__ or __FUNCSIG__"
#endif
}

constexpr bool contains(std::string_view s, std::string_view needle) {
    return s.find(needle) != std::string_view::npos;
}

template <typename T>
constexpr bool is_lambda() {
    constexpr auto n = raw_type_name<T>();
    return contains(n, "lambda") || contains(n, "$_");  // Clang "(lambda at ...)", GCC "<lambda(...)>", Clang "$_0"
}

template <typename T>
constexpr bool in_anonymous_namespace() {
    constexpr auto n = raw_type_name<T>();
    return contains(n, "(anonymous namespace)") || contains(n, "{anonymous}") || contains(n, "`anonymous namespace'");
}

// The step's identity: the type's qualified name.
template <typename T>
std::string identity_of() {
    static_assert(!is_lambda<T>(),
                  "codeupipe: a lambda has no step identity; declare a named struct (conformance/API.md, Step identity)");
    static_assert(!in_anonymous_namespace<T>(),
                  "codeupipe: a step type in an anonymous namespace has no unique identity and cannot be tested "
                  "from another file; declare it in a named namespace");
    return std::string(raw_type_name<T>());
}

}  // namespace cup::detail
