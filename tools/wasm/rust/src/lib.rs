//! WebAssembly wrapper around the Rust `mbusino-lib-rs` crate, for the
//! `docs/` web decoder (the "Rust port" panel).
//!
//! Exposes the **same JSON shape** as the C++ wrapper `tools/wasm/mbusino_wasm.cpp`:
//! `{ slave_address, header, header_ok, records_decoded, error_code, records }`.
//!
//! Built with `rustup target add wasm32-unknown-unknown` +
//! `cargo build --release --target wasm32-unknown-unknown` (see `build_rust.sh`).
//! Deliberately **no wasm-bindgen**: plain C-ABI exports plus a small
//! hand-written JS loader (`docs/rust/mbusino_rs.js`), which keeps the build
//! toolchain to cargo alone.

use std::sync::Mutex;

use mbusino_lib_rs::{Decoder, Json};

static IN: Mutex<Vec<u8>> = Mutex::new(Vec::new());
static OUT: Mutex<Vec<u8>> = Mutex::new(Vec::new());

/// Reserve `len` bytes for the input hex string and return the pointer the JS
/// side writes into (`Uint8Array` over the wasm memory).
#[no_mangle]
pub extern "C" fn alloc(len: usize) -> *mut u8 {
    let mut buf = IN.lock().unwrap();
    buf.clear();
    buf.resize(len, 0);
    buf.as_mut_ptr()
}

/// Decode the `len` bytes previously written into the input buffer and return
/// the length of the JSON result (read it back via [`out_ptr`]).
#[no_mangle]
pub extern "C" fn decode_hex(len: usize) -> usize {
    let hex = {
        let buf = IN.lock().unwrap();
        let n = len.min(buf.len());
        String::from_utf8_lossy(&buf[..n]).into_owned()
    };
    let json = run(&hex);
    let mut out = OUT.lock().unwrap();
    out.clear();
    out.extend_from_slice(json.as_bytes());
    out.len()
}

/// Pointer to the result written by the last [`decode_hex`] call.
#[no_mangle]
pub extern "C" fn out_ptr() -> *const u8 {
    OUT.lock().unwrap().as_ptr()
}

/// Same flow as the C++ wrapper: `packet_size = data[1] + 6`, records from
/// offset `0x13` with length `packet_size - 0x13 - 2`.
fn run(hex: &str) -> String {
    let data = mbusino_lib_rs::parse_hex(hex);
    if data.len() < 6 {
        return error_json("telegram too short");
    }
    let packet_size = data[1] as usize + 6;
    if packet_size > data.len() {
        return error_json("declared length mismatch");
    }

    const START_ADDRESS: usize = 0x13; // frame header + fixed data header

    let mut decoder = Decoder::new();
    let header = decoder.decode_header(&data[..packet_size], Some(packet_size));
    let records = decoder.decode_records(
        &data[START_ADDRESS..packet_size],
        Some(packet_size - START_ADDRESS - 2),
    );
    let error_code = decoder.get_error();

    let mut doc = Json::object();
    doc.set(
        "header",
        header
            .as_ref()
            .map(|h| h.to_json())
            .unwrap_or_else(Json::object),
    );
    doc.set(
        "records",
        Json::Array(records.iter().map(|r| r.to_json()).collect()),
    );
    doc.set("slave_address", data[5]);
    doc.set("header_ok", header.as_ref().map(|h| h.is_ok()).unwrap_or(false));
    doc.set("records_decoded", records.len());
    doc.set("error_code", error_code);
    doc.to_json_string()
}

fn error_json(message: &str) -> String {
    let mut obj = Json::object();
    obj.set("error", message);
    obj.to_json_string()
}
