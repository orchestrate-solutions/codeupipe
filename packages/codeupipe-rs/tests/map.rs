use codeupipe::{Map, Value};

/// A map with `n` keys k0, k1, ... in order, each with its number.
fn numbered(n: usize) -> Map {
    (0..n).map(|i| (format!("k{i}"), i)).collect()
}

// A small map is searched in order and a large one through an index, so each
// test runs on both sides of the size where the index starts.
const SIZES: [usize; 4] = [3, 8, 9, 40];

#[test]
fn get_finds_every_key() {
    for size in SIZES {
        let map = numbered(size);
        for i in 0..size {
            assert_eq!(map.get(&format!("k{i}")), Some(&Value::from(i)), "{size}");
        }
        assert_eq!(map.get("absent"), None);
        assert!(!map.contains_key("absent"));
    }
}

#[test]
fn an_insert_of_a_key_that_is_there_keeps_its_place() {
    for size in SIZES {
        let mut map = numbered(size);
        map.insert("k1", "new");
        assert_eq!(map.len(), size);
        assert_eq!(map.keys().nth(1), Some("k1"));
        assert_eq!(map.get("k1"), Some(&Value::from("new")));
    }
}

#[test]
fn a_remove_keeps_the_order_and_every_other_key() {
    for size in SIZES {
        let mut map = numbered(size);
        assert_eq!(map.remove("k1"), Some(Value::from(1)));
        assert_eq!(map.remove("k1"), None);
        assert_eq!(map.len(), size - 1);
        let want: Vec<String> = (0..size)
            .filter(|&i| i != 1)
            .map(|i| format!("k{i}"))
            .collect();
        assert_eq!(map.keys().collect::<Vec<_>>(), want);
        for i in (0..size).filter(|&i| i != 1) {
            assert_eq!(map.get(&format!("k{i}")), Some(&Value::from(i)), "{size}");
        }
        map.insert("k1", "back");
        assert_eq!(map.keys().last(), Some("k1"));
        assert_eq!(map.get("k1"), Some(&Value::from("back")));
    }
}

#[test]
fn a_map_that_grows_past_the_index_and_shrinks_back_still_finds_its_keys() {
    let mut map = numbered(20);
    for i in 0..18 {
        map.remove(&format!("k{i}"));
    }
    assert_eq!(map.keys().collect::<Vec<_>>(), ["k18", "k19"]);
    assert_eq!(map.get("k19"), Some(&Value::from(19)));
    map.insert("k0", 0);
    assert_eq!(map.get("k0"), Some(&Value::from(0)));
}

#[test]
fn a_clone_is_separate() {
    for size in SIZES {
        let map = numbered(size);
        let mut other = map.clone();
        other.insert("k0", "changed");
        other.insert("extra", true);
        assert_eq!(map.get("k0"), Some(&Value::from(0)));
        assert!(!map.contains_key("extra"));
    }
}

#[test]
fn two_maps_with_the_same_entries_in_another_order_are_equal() {
    for size in SIZES {
        let forward = numbered(size);
        let backward: Map = (0..size).rev().map(|i| (format!("k{i}"), i)).collect();
        assert_eq!(forward, backward);
        let mut different = numbered(size);
        different.insert("k0", "x");
        assert_ne!(forward, different);
    }
}
