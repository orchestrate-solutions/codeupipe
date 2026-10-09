// codeupipe/payload.hpp — Immutable data container
//
// Payload is the envelope on the conveyor belt. Immutable at the API level:
// insert() / merge() / remove() / with_trace() return a NEW Payload via
// shared_ptr<const map>. Copy-on-write.
//
// Perf notes:
//   - reserve() on copy avoids the growth-rehash on every insert.
//   - Move-based construction from ValueMap avoids an extra copy.

#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

namespace cup {

class Value;
using ValueList = std::vector<Value>;
using ValueMap  = std::unordered_map<std::string, Value>;

class Value {
public:
    using Variant = std::variant<
        std::monostate, bool, std::int64_t, double,
        std::string, ValueList, ValueMap
    >;

    Value() = default;
    Value(std::nullptr_t) : v_(std::monostate{}) {}
    Value(bool b)         : v_(b) {}
    Value(int i)          : v_(static_cast<std::int64_t>(i)) {}
    Value(std::int64_t i) : v_(i) {}
    Value(double d)       : v_(d) {}
    Value(const char* s)  : v_(std::string(s)) {}
    Value(std::string s)  : v_(std::move(s)) {}
    Value(ValueList l)    : v_(std::move(l)) {}
    Value(ValueMap  m)    : v_(std::move(m)) {}

    bool is_null()   const noexcept { return std::holds_alternative<std::monostate>(v_); }
    bool is_bool()   const noexcept { return std::holds_alternative<bool>(v_); }
    bool is_int()    const noexcept { return std::holds_alternative<std::int64_t>(v_); }
    bool is_float()  const noexcept { return std::holds_alternative<double>(v_); }
    bool is_string() const noexcept { return std::holds_alternative<std::string>(v_); }
    bool is_list()   const noexcept { return std::holds_alternative<ValueList>(v_); }
    bool is_map()    const noexcept { return std::holds_alternative<ValueMap>(v_); }

    std::optional<bool>         as_bool()   const { return is_bool()   ? std::optional{std::get<bool>(v_)}         : std::nullopt; }
    std::optional<std::int64_t> as_int()    const { return is_int()    ? std::optional{std::get<std::int64_t>(v_)} : std::nullopt; }
    std::optional<double>       as_float()  const { return is_float()  ? std::optional{std::get<double>(v_)}       : std::nullopt; }
    const std::string* as_string() const { return is_string() ? &std::get<std::string>(v_) : nullptr; }
    const ValueList*   as_list()   const { return is_list()   ? &std::get<ValueList>(v_)   : nullptr; }
    const ValueMap*    as_map()    const { return is_map()    ? &std::get<ValueMap>(v_)    : nullptr; }

    const Variant& variant() const noexcept { return v_; }
    bool operator==(const Value& other) const { return v_ == other.v_; }

private:
    Variant v_{};
};

class MutablePayload;

class Payload {
public:
    Payload() : data_(std::make_shared<const ValueMap>()) {}

    explicit Payload(ValueMap data)
        : data_(std::make_shared<const ValueMap>(std::move(data))) {}

    // get: the value, the fallback, or the null Value when absent.
    Value get(const std::string& key) const {
        auto it = data_->find(key);
        return it != data_->end() ? it->second : Value{};
    }
    Value get(const std::string& key, Value fallback) const {
        auto it = data_->find(key);
        return it != data_->end() ? it->second : std::move(fallback);
    }
    bool        has(const std::string& key) const { return data_->find(key) != data_->end(); }
    std::size_t size() const noexcept { return data_->size(); }

    // The native map (read-only view; copy it if you need to keep it).
    const ValueMap& to_dict() const noexcept { return *data_; }

    [[nodiscard]] Payload insert(std::string key, Value value) const {
        ValueMap next;
        next.reserve(data_->size() + 1);   // avoid growth-rehash
        for (const auto& kv : *data_) next.emplace(kv.first, kv.second);
        next.insert_or_assign(std::move(key), std::move(value));
        return with_data(std::move(next));
    }

    // Right side wins; trace and lineage carry from this payload, as in the
    // other runtimes.
    [[nodiscard]] Payload merge(const Payload& other) const {
        ValueMap next;
        next.reserve(data_->size() + other.data_->size());
        for (const auto& kv : *data_)        next.emplace(kv.first, kv.second);
        for (const auto& kv : *other.data_)  next.insert_or_assign(kv.first, kv.second);
        return with_data(std::move(next));
    }

    [[nodiscard]] Payload remove(const std::string& key) const {
        if (!has(key)) return *this;
        ValueMap next;
        next.reserve(data_->size());
        for (const auto& kv : *data_) if (kv.first != key) next.emplace(kv.first, kv.second);
        return with_data(std::move(next));
    }

    [[nodiscard]] Payload with_trace(std::string trace_id) const {
        Payload out = *this;
        out.meta_ = std::make_shared<const Meta>(Meta{std::move(trace_id), lineage()});
        return out;
    }
    std::optional<std::string> trace_id() const {
        return meta_ ? meta_->trace_id : std::nullopt;
    }
    const std::vector<std::string>& lineage() const noexcept {
        static const std::vector<std::string> none{};
        return meta_ ? meta_->lineage : none;
    }

    [[nodiscard]] MutablePayload with_mutation() const;

    bool operator==(const Payload& other) const {
        return data_.get() == other.data_.get() || *data_ == *other.data_;
    }

private:
    friend class MutablePayload;

    // Trace and lineage are rarely set, so they live behind one shared
    // pointer that insert() copies for the cost of a refcount.
    struct Meta {
        std::optional<std::string> trace_id;
        std::vector<std::string>   lineage;
    };

    Payload with_data(ValueMap next) const {
        Payload out(std::move(next));
        out.meta_ = meta_;
        return out;
    }

    std::shared_ptr<const ValueMap> data_;
    std::shared_ptr<const Meta>     meta_;
};

// The explicit mutable escape hatch: set() / remove() change this object in
// place, where Payload::insert() returns a new one.
class MutablePayload {
public:
    Value get(const std::string& key) const {
        auto it = data_.find(key);
        return it != data_.end() ? it->second : Value{};
    }
    Value get(const std::string& key, Value fallback) const {
        auto it = data_.find(key);
        return it != data_.end() ? it->second : std::move(fallback);
    }
    bool has(const std::string& key) const { return data_.find(key) != data_.end(); }
    void set(std::string key, Value value) { data_.insert_or_assign(std::move(key), std::move(value)); }
    void remove(const std::string& key) { data_.erase(key); }

    [[nodiscard]] Payload to_immutable() const {
        Payload out(data_);
        out.meta_ = meta_;
        return out;
    }

private:
    friend class Payload;
    MutablePayload(ValueMap data, std::shared_ptr<const Payload::Meta> meta)
        : data_(std::move(data)), meta_(std::move(meta)) {}

    ValueMap                                   data_;
    std::shared_ptr<const Payload::Meta>       meta_;
};

inline MutablePayload Payload::with_mutation() const {
    return MutablePayload(*data_, meta_);
}

} // namespace cup
