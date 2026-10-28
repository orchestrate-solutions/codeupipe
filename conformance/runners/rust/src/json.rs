//! JSON text to a codeupipe `Value` and back. A runner must not download
//! anything, so the runner has its own small reader and writer.

use codeupipe::{Map, Value};

/// Read one JSON value from `text`.
pub fn read(text: &str) -> Result<Value, String> {
    let mut reader = Reader { text, at: 0 };
    let value = reader.value()?;
    reader.space();
    if reader.at != text.len() {
        return Err(reader.problem("text after the value"));
    }
    Ok(value)
}

/// Write `value` as JSON text.
pub fn write(value: &Value) -> String {
    let mut out = String::new();
    write_into(value, &mut out);
    out
}

fn write_into(value: &Value, out: &mut String) {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        // Display gives 12 for 12.0. JSON has no NaN or infinity: null, as JavaScript writes them.
        Value::Number(n) if n.is_finite() => out.push_str(&n.to_string()),
        Value::Number(_) => out.push_str("null"),
        Value::String(s) => write_string(s, out),
        Value::List(items) => {
            out.push('[');
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                write_into(item, out);
            }
            out.push(']');
        }
        Value::Map(map) => {
            out.push('{');
            for (index, (key, item)) in map.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                write_string(key, out);
                out.push(':');
                write_into(item, out);
            }
            out.push('}');
        }
    }
}

fn write_string(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

struct Reader<'a> {
    text: &'a str,
    at: usize,
}

impl Reader<'_> {
    fn problem(&self, what: &str) -> String {
        format!("not JSON at byte {}: {what}", self.at)
    }

    fn peek(&self) -> Option<u8> {
        self.text.as_bytes().get(self.at).copied()
    }

    fn space(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\t' | b'\n' | b'\r')) {
            self.at += 1;
        }
    }

    fn expect(&mut self, byte: u8) -> Result<(), String> {
        self.space();
        if self.peek() == Some(byte) {
            self.at += 1;
            Ok(())
        } else {
            Err(self.problem(&format!("expected '{}'", byte as char)))
        }
    }

    fn word(&mut self, word: &str, value: Value) -> Result<Value, String> {
        if self.text[self.at..].starts_with(word) {
            self.at += word.len();
            Ok(value)
        } else {
            Err(self.problem("unknown word"))
        }
    }

    fn value(&mut self) -> Result<Value, String> {
        self.space();
        match self.peek() {
            Some(b'n') => self.word("null", Value::Null),
            Some(b't') => self.word("true", Value::Bool(true)),
            Some(b'f') => self.word("false", Value::Bool(false)),
            Some(b'"') => self.string().map(Value::String),
            Some(b'[') => self.list(),
            Some(b'{') => self.map(),
            Some(b'-' | b'0'..=b'9') => self.number(),
            Some(_) => Err(self.problem("unexpected character")),
            None => Err(self.problem("end of the text")),
        }
    }

    fn number(&mut self) -> Result<Value, String> {
        let start = self.at;
        while matches!(
            self.peek(),
            Some(b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9')
        ) {
            self.at += 1;
        }
        self.text[start..self.at]
            .parse::<f64>()
            .map(Value::Number)
            .map_err(|_| self.problem("bad number"))
    }

    fn list(&mut self) -> Result<Value, String> {
        self.expect(b'[')?;
        let mut items = Vec::new();
        self.space();
        if self.peek() == Some(b']') {
            self.at += 1;
            return Ok(Value::List(items));
        }
        loop {
            items.push(self.value()?);
            self.space();
            match self.peek() {
                Some(b',') => self.at += 1,
                Some(b']') => {
                    self.at += 1;
                    return Ok(Value::List(items));
                }
                _ => return Err(self.problem("expected ',' or ']'")),
            }
        }
    }

    fn map(&mut self) -> Result<Value, String> {
        self.expect(b'{')?;
        let mut map = Map::new();
        self.space();
        if self.peek() == Some(b'}') {
            self.at += 1;
            return Ok(Value::Map(map));
        }
        loop {
            self.space();
            if self.peek() != Some(b'"') {
                return Err(self.problem("expected a key"));
            }
            let key = self.string()?;
            self.expect(b':')?;
            let value = self.value()?;
            map.insert(key, value);
            self.space();
            match self.peek() {
                Some(b',') => self.at += 1,
                Some(b'}') => {
                    self.at += 1;
                    return Ok(Value::Map(map));
                }
                _ => return Err(self.problem("expected ',' or '}'")),
            }
        }
    }

    fn string(&mut self) -> Result<String, String> {
        self.at += 1; // the opening quote
        let mut out = String::new();
        loop {
            let rest = &self.text[self.at..];
            let Some(c) = rest.chars().next() else {
                return Err(self.problem("string with no end"));
            };
            self.at += c.len_utf8();
            match c {
                '"' => return Ok(out),
                '\\' => out.push(self.escape()?),
                c => out.push(c),
            }
        }
    }

    fn escape(&mut self) -> Result<char, String> {
        let Some(byte) = self.peek() else {
            return Err(self.problem("string with no end"));
        };
        self.at += 1;
        Ok(match byte {
            b'"' => '"',
            b'\\' => '\\',
            b'/' => '/',
            b'b' => '\u{8}',
            b'f' => '\u{c}',
            b'n' => '\n',
            b'r' => '\r',
            b't' => '\t',
            b'u' => {
                let first = self.hex4()?;
                if (0xd800..0xdc00).contains(&first) {
                    // A pair of UTF-16 halves: 😀
                    if !self.text[self.at..].starts_with("\\u") {
                        return Err(self.problem("half of a UTF-16 pair"));
                    }
                    self.at += 2;
                    let second = self.hex4()?;
                    let code = 0x10000 + ((first - 0xd800) << 10) + (second.wrapping_sub(0xdc00));
                    char::from_u32(code).ok_or_else(|| self.problem("bad UTF-16 pair"))?
                } else {
                    char::from_u32(first).ok_or_else(|| self.problem("bad \\u escape"))?
                }
            }
            _ => return Err(self.problem("unknown escape")),
        })
    }

    fn hex4(&mut self) -> Result<u32, String> {
        let digits = self
            .text
            .get(self.at..self.at + 4)
            .ok_or_else(|| self.problem("short \\u escape"))?;
        let code = u32::from_str_radix(digits, 16).map_err(|_| self.problem("bad \\u escape"))?;
        self.at += 4;
        Ok(code)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use codeupipe::Map;

    #[test]
    fn reads_each_kind_of_value() {
        assert_eq!(read("null").unwrap(), Value::Null);
        assert_eq!(read("true").unwrap(), Value::Bool(true));
        assert_eq!(read("false").unwrap(), Value::Bool(false));
        assert_eq!(read("12").unwrap(), Value::Number(12.0));
        assert_eq!(read("-1.5e2").unwrap(), Value::Number(-150.0));
        assert_eq!(read("\"x\"").unwrap(), Value::from("x"));
        assert_eq!(
            read(" [1, \"two\", [3]] ").unwrap(),
            Value::List(vec![
                Value::from(1),
                Value::from("two"),
                Value::List(vec![Value::from(3)])
            ])
        );
        assert_eq!(
            read("{\"a\": 1, \"b\": {}}").unwrap(),
            Value::Map(Map::from([
                ("a", Value::from(1)),
                ("b", Value::Map(Map::new()))
            ]))
        );
    }

    #[test]
    fn reads_the_escapes_of_a_string() {
        assert_eq!(
            read(r#""q\" b\\ s\/ n\n t\t ué pair😀""#).unwrap(),
            Value::from("q\" b\\ s/ n\n t\t u\u{e9} pair\u{1f600}")
        );
    }

    #[test]
    fn keeps_the_order_of_the_keys() {
        let value = read("{\"z\": 1, \"a\": 2, \"m\": 3}").unwrap();
        let keys: Vec<&str> = value.as_map().unwrap().keys().collect();
        assert_eq!(keys, ["z", "a", "m"]);
    }

    #[test]
    fn refuses_text_that_is_not_json() {
        for text in ["", "[1,", "{\"a\" 1}", "tru", "\"open", "1 2", "{1: 2}"] {
            assert!(read(text).is_err(), "{text:?}");
        }
    }

    #[test]
    fn writes_each_kind_of_value() {
        let value = Value::Map(Map::from([
            ("n", Value::from(1.5)),
            ("w", Value::from(12)),
            ("s", Value::from("x")),
            ("b", Value::from(false)),
            ("z", Value::Null),
            (
                "l",
                Value::List(vec![Value::from(1), Value::List(vec![Value::from(3)])]),
            ),
        ]));
        assert_eq!(
            write(&value),
            r#"{"n":1.5,"w":12,"s":"x","b":false,"z":null,"l":[1,[3]]}"#
        );
    }

    #[test]
    fn writes_the_escapes_of_a_string() {
        assert_eq!(
            write(&Value::from("q\" b\\ n\n c\u{1} \u{e9}")),
            r#""q\" b\\ n\n c\u0001 é""#
        );
    }

    #[test]
    fn what_it_writes_reads_back_the_same() {
        let text = r#"{"v":{"n":1.5,"s":"x","b":false,"z":null,"l":[1,"two",[3]]},"e":"a\"b"}"#;
        assert_eq!(write(&read(text).unwrap()), text);
    }
}
