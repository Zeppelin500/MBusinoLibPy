/* Loader for the Rust port compiled to WebAssembly (docs/rust/mbusino_rs.wasm).
 *
 * Plain C-ABI module - deliberately no wasm-bindgen glue. Mirrors the
 * createMBusinoCpp() factory used for the C++ panel:
 *
 *   createMBusinoRust({ locateFile: function (p) { return "rust/" + p; } })
 *     .then(function (engine) { engine.decode("68 ..."); });
 *
 * decode(hex) -> JSON string, same shape as the C++ wrapper:
 * { slave_address, header, header_ok, records_decoded, error_code, records }.
 */
(function (global) {
  "use strict";

  function createMBusinoRust(options) {
    options = options || {};
    var url = (typeof options.locateFile === "function")
      ? options.locateFile("mbusino_rs.wasm")
      : "rust/mbusino_rs.wasm";
    var encoder = new TextEncoder();
    var decoder = new TextDecoder();

    return fetch(url, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Could not fetch " + url + " (HTTP " + response.status + ").");
        }
        return response.arrayBuffer();
      })
      .then(function (bytes) {
        return WebAssembly.instantiate(bytes, {});
      })
      .then(function (result) {
        var exports = result.instance.exports;
        var memory = exports.memory;

        // The memory is re-read on every call because it can grow (and the
        // ArrayBuffer detach) between allocations.
        function decode(hex) {
          var input = encoder.encode(hex || "");
          var inPtr = exports.alloc(input.length);
          new Uint8Array(memory.buffer, inPtr, input.length).set(input);
          var outLen = exports.decode_hex(input.length);
          var outPtr = exports.out_ptr();
          return decoder.decode(new Uint8Array(memory.buffer, outPtr, outLen));
        }

        return { decode: decode, exports: exports };
      });
  }

  global.createMBusinoRust = createMBusinoRust;
})(typeof self !== "undefined" ? self : this);
