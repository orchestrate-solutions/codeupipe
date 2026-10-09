// CUP persistent subprocess runner for Rust.
// Reads length-prefixed CUP envelopes from stdin (JSON, msgpack, or shm file),
// processes them, writes results to stdout in the same format.
//
// Protocol: [4-byte LE length][payload bytes]
// Format auto-detected from first byte:
//   0x7b '{' → JSON
//   0x80-0x8f / 0xde / 0xdf → msgpack map
//   0x00      → shm file handle (msgpack {"f": "/path/cup_xxx.mp"})
//
// Build: cargo build --release --manifest-path runtimes/rs/Cargo.toml --bin cup_runner
// Usage: runtimes/rs/target/release/cup_runner

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{self, Read, Write};
use std::sync::atomic::{AtomicU64, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);

#[derive(Serialize, Deserialize)]
struct Envelope {
    data: HashMap<String, serde_json::Value>,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    trace_id: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    lineage: Vec<String>,
}

#[derive(Serialize, Deserialize)]
struct ShmHandle {
    f: String,
}

fn read_exact(reader: &mut impl Read, buf: &mut [u8]) -> io::Result<()> {
    let mut filled = 0;
    while filled < buf.len() {
        let n = reader.read(&mut buf[filled..])?;
        if n == 0 {
            return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "EOF"));
        }
        filled += n;
    }
    Ok(())
}

fn write_frame(stdout: &mut impl Write, data: &[u8]) -> io::Result<()> {
    stdout.write_all(&(data.len() as u32).to_le_bytes())?;
    stdout.write_all(data)?;
    stdout.flush()
}

/// Detect msgpack map format from first byte.
fn is_msgpack(b: u8) -> bool {
    (0x80..=0x8F).contains(&b) || b == 0xDE || b == 0xDF
}

/// Return preferred directory for shm temp files.
fn shm_dir() -> std::path::PathBuf {
    let devshm = std::path::Path::new("/dev/shm");
    if devshm.is_dir() {
        devshm.to_path_buf()
    } else {
        std::env::temp_dir()
    }
}

fn main() -> io::Result<()> {
    let mut stdin = io::stdin().lock();
    let mut stdout = io::stdout().lock();

    loop {
        // Read 4-byte LE length prefix
        let mut len_buf = [0u8; 4];
        if let Err(e) = read_exact(&mut stdin, &mut len_buf) {
            if e.kind() == io::ErrorKind::UnexpectedEof {
                break;
            }
            return Err(e);
        }
        let msg_len = u32::from_le_bytes(len_buf) as usize;

        // Read message bytes
        let mut msg_buf = vec![0u8; msg_len];
        read_exact(&mut stdin, &mut msg_buf)?;

        // ── Shm file mode: first byte is 0x00 ────────────────────────────
        if !msg_buf.is_empty() && msg_buf[0] == 0x00 {
            let handle: ShmHandle = rmp_serde::from_slice(&msg_buf[1..])
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

            // Read payload from shm file and delete it
            let file_data = std::fs::read(&handle.f)?;
            let _ = std::fs::remove_file(&handle.f);

            // Decode envelope (always msgpack inside shm files)
            let mut env: Envelope = rmp_serde::from_slice(&file_data)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

            // Transform
            env.data
                .insert("rust_processed".to_string(), serde_json::Value::Bool(true));
            env.data.insert(
                "lang".to_string(),
                serde_json::Value::String("rust".to_string()),
            );

            // Write result to new shm file
            let result_data = rmp_serde::to_vec_named(&env)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            let count = COUNTER.fetch_add(1, Ordering::Relaxed);
            let result_path = shm_dir().join(format!("cup_{}_{}.mp", std::process::id(), count));
            std::fs::write(&result_path, &result_data)?;

            // Send back shm handle
            let result_handle = ShmHandle {
                f: result_path.to_str().unwrap().to_string(),
            };
            let handle_bytes = rmp_serde::to_vec_named(&result_handle)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
            let mut out = vec![0x00u8];
            out.extend_from_slice(&handle_bytes);
            write_frame(&mut stdout, &out)?;
            continue;
        }

        // ── JSON / msgpack mode ───────────────────────────────────────────
        let use_msgpack = !msg_buf.is_empty() && is_msgpack(msg_buf[0]);

        let mut env: Envelope = if use_msgpack {
            rmp_serde::from_slice(&msg_buf)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?
        } else {
            serde_json::from_slice(&msg_buf)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?
        };

        env.data
            .insert("rust_processed".to_string(), serde_json::Value::Bool(true));
        env.data.insert(
            "lang".to_string(),
            serde_json::Value::String("rust".to_string()),
        );

        let out_bytes = if use_msgpack {
            rmp_serde::to_vec_named(&env)
                .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?
        } else {
            serde_json::to_vec(&env).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?
        };

        write_frame(&mut stdout, &out_bytes)?;
    }

    Ok(())
}
