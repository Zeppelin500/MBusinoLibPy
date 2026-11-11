/* MBusinoLibPy Web Decoder - plain JavaScript, no framework, no build step.
 *
 * Three decoders run on the same input, side by side:
 *   - Python port via Pyodide (sources fetched from jsDelivr @main, so the
 *     page always tests the current upstream source),
 *   - the original C++ MBusinoLib compiled to WebAssembly (docs/cpp/, built
 *     by tools/wasm/build.sh),
 *   - the Rust port (mbusino-lib-rs) compiled to WebAssembly (docs/rust/,
 *     built by tools/wasm/build_rust.sh).
 */
var LIB_BASE_URL = "https://cdn.jsdelivr.net/gh/Zeppelin500/MBusinoLibPy@main/src/MBusinoLibPy/";

/* Pinned Pyodide release for reproducible loads (jsDelivr CDN, ~10 MB). */
var PYODIDE_VERSION = "314.0.7";
var PYODIDE_INDEX_URL = "https://cdn.jsdelivr.net/pyodide/v" + PYODIDE_VERSION + "/full/";

/* Modules of src/MBusinoLibPy/, imported as one package after the files are
 * written into Pyodide's virtual filesystem. */
var LIB_MODULES = ["__init__.py", "enums.py", "vif_defs.py", "lookup_tables.py", "mbusino_lib.py"];

/* Golden test telegrams from tests/golden/*.hex (real captures decoded by
 * the original C++ library). */
var EXAMPLES = {
  efe_heat_meter:
    "68 C1 C1 68 08 00 72 09 34 75 73 C5 14 00 0D 43 00 00 00 04 78 41 63 65 04 04 06 AA 29 00 00 " +
    "04 13 40 A1 75 00 04 2B 00 00 00 00 14 2B 3C F3 00 00 04 3B 48 06 00 00 14 3B 4E 0E 00 00 02 5B 19 00 " +
    "02 5F 19 00 02 61 FA FF 02 23 AC 08 04 6D 03 2A F1 2A 44 06 92 0C 00 00 44 13 2D 9B 1C 00 42 6C DF 2C 01 " +
    "FD 17 00 03 FD 0C 05 00 00 84 10 06 1A 00 00 00 C4 10 06 05 00 00 00 84 20 06 00 00 00 00 C4 20 06 00 00 " +
    "00 00 84 30 06 00 00 00 00 C4 30 06 00 00 00 00 84 40 13 00 00 00 00 C4 40 13 00 00 00 00 84 80 40 13 00 " +
    "00 00 00 C4 80 40 13 00 00 00 00 84 C0 40 13 00 00 00 00 C4 C0 40 13 00 00 00 00 75 16",
  hw_thermostat:
    "68 53 53 68 08 02 72 11 82 00 24 96 15 16 00 20 00 00 00 01 FD 1B 00 02 FC 03 48 52 25 74 62 17 22 FC 03 " +
    "48 52 25 74 5C 17 12 FC 03 48 52 25 74 68 17 02 65 A2 08 22 65 9E 08 12 65 A2 08 01 72 00 72 65 00 00 B2 " +
    "01 65 00 00 0C 78 11 82 00 24 03 FD 0F 05 09 03 1F 9F 16",
  mbusino_example:
    "68 C4 C4 68 08 14 72 72 91 07 29 47 5F 03 16 C2 00 00 00 04 13 8B 01 00 00 04 6D 1E 14 4D 32 42 6C 00 00 " +
    "44 13 00 00 00 00 42 EC 7E 57 36 0C 78 24 33 05 61 82 01 6C 3E 36 84 01 13 00 00 00 00 C2 01 6C 3F 37 C4 " +
    "01 13 00 00 00 00 82 02 6C 3F 38 84 02 13 00 00 00 00 C2 02 6C 3E 39 C4 02 13 00 00 00 00 82 03 6C 3F 3A " +
    "84 03 13 00 00 00 00 C2 03 6C 3E 3B C4 03 13 00 00 00 00 82 04 6C 3F 3C 84 04 13 A9 00 00 00 C2 04 6C 5F " +
    "31 C4 04 13 56 01 00 00 82 05 6C 00 00 84 05 13 00 00 00 00 C2 05 6C 00 00 C4 05 13 00 00 00 00 82 06 6C " +
    "00 00 84 06 13 00 00 00 00 C2 06 6C 00 00 C4 06 13 00 00 00 00 0F 01 00 00 FB 16"
};

/* Runs inside Pyodide: writes the fetched sources into the virtual FS,
 * imports the package and exposes decode() as a JSON-string helper. */
var BOOTSTRAP_PY = [
  "import importlib, json, os, sys",
  "files = json.loads(_files_json)",
  "os.makedirs('/lib/MBusinoLibPy', exist_ok=True)",
  "for name, text in files.items():",
  "    with open(os.path.join('/lib/MBusinoLibPy', name), 'w', encoding='utf-8') as fh:",
  "        fh.write(text)",
  "importlib.invalidate_caches()",
  "if '/lib' not in sys.path:",
  "    sys.path.insert(0, '/lib')",
  "from MBusinoLibPy import MBusinoLib",
  "def decode_json(hex_str):",
  "    return json.dumps(MBusinoLib().decode_telegram(hex_str))"
].join("\n");

/* Engine state. Each engine exposes decode(hex) -> JSON string once ready. */
var engines = {
  python: { ready: false, failed: false, decode: null },
  cpp: { ready: false, failed: false, decode: null },
  rust: { ready: false, failed: false, decode: null }
};

var pyodide = null;
var initRunning = false;

var statusEl, statusTextEl, errorBanner, errorTextEl, retryBtn;
var inputEl, decodeBtn, clearBtn, outputEl;
var panelPython, panelCpp, panelRust;

/* ------------------------------------------------------------------ */
/* Runtime status                                                      */
/* ------------------------------------------------------------------ */

function setStatus(state, text) {
  statusEl.classList.remove("is-loading", "is-ready", "is-error");
  statusEl.classList.add("is-" + state);
  statusTextEl.textContent = text;
}

function updateStatus() {
  var list = [engines.python, engines.cpp, engines.rust];
  var ready = list.filter(function (e) { return e.ready; }).length;
  var failed = list.filter(function (e) { return e.failed; }).length;
  var settled = list.filter(function (e) { return e.ready || e.failed; }).length;
  if (ready === list.length) {
    setStatus("ready", "Ready");
  } else if (failed === list.length) {
    setStatus("error", "All runtimes failed to load");
  } else if (settled > 0) {
    setStatus("loading", "One runtime still loading…");
  } else {
    setStatus("loading", "Loading runtimes… (Python ~10 MB, C++ ~70 KB)");
  }
  // Decode needs at least one working engine, and all to be settled
  // (ready or failed) so "decode all at once" is meaningful.
  decodeBtn.disabled = settled !== list.length || ready === 0;
}

function showError(message) {
  errorTextEl.textContent = " " + message + " Check your connection and retry.";
  errorBanner.hidden = false;
}

function hideError() {
  errorBanner.hidden = true;
}

/* ------------------------------------------------------------------ */
/* Python (Pyodide) startup                                            */
/* ------------------------------------------------------------------ */

async function initPython() {
  engines.python.failed = false;
  try {
    if (typeof loadPyodide !== "function") {
      throw new Error("The Pyodide loader script could not be loaded from the CDN.");
    }
    if (!pyodide) {
      pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });
    }

    var files = {};
    await Promise.all(
      LIB_MODULES.map(async function (name) {
        var response = await fetch(LIB_BASE_URL + name, { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Could not fetch " + name + " (HTTP " + response.status + ").");
        }
        files[name] = await response.text();
      })
    );

    pyodide.globals.set("_files_json", JSON.stringify(files));
    pyodide.runPython(BOOTSTRAP_PY);
    engines.python.decode = pyodide.globals.get("decode_json");
    engines.python.ready = true;
  } catch (err) {
    engines.python.failed = true;
    showError(String((err && err.message) || err));
  } finally {
    updateStatus();
  }
}

/* ------------------------------------------------------------------ */
/* C++ (WASM) startup                                                  */
/* ------------------------------------------------------------------ */

function initCpp() {
  engines.cpp.failed = false;
  if (typeof createMBusinoCpp !== "function") {
    engines.cpp.failed = true;
    showError("The C++ WebAssembly module could not be loaded.");
    updateStatus();
    return;
  }
  createMBusinoCpp({ locateFile: function (path) { return "cpp/" + path; } })
    .then(function (module) {
      engines.cpp.decode = module.cwrap("decode_hex", "string", ["string"]);
      engines.cpp.ready = true;
    })
    .catch(function (err) {
      engines.cpp.failed = true;
      showError(String((err && err.message) || err));
    })
    .then(updateStatus);
}

function initRust() {
  engines.rust.failed = false;
  if (typeof createMBusinoRust !== "function") {
    engines.rust.failed = true;
    showError("The Rust WebAssembly module could not be loaded.");
    updateStatus();
    return;
  }
  createMBusinoRust({ locateFile: function (path) { return "rust/" + path; } })
    .then(function (module) {
      engines.rust.decode = module.decode;
      engines.rust.ready = true;
    })
    .catch(function (err) {
      engines.rust.failed = true;
      showError(String((err && err.message) || err));
    })
    .then(updateStatus);
}

/* ------------------------------------------------------------------ */
/* Decoding                                                            */
/* ------------------------------------------------------------------ */

function decode() {
  var hex = inputEl.value.trim();
  if (!hex) {
    outputEl.hidden = true;
    return;
  }
  outputEl.hidden = false;
  runEngine(panelPython, "python", hex);
  runEngine(panelCpp, "cpp", hex);
  runEngine(panelRust, "rust", hex);
}

function runEngine(panel, name, hex) {
  var engine = engines[name];
  if (!engine.ready || typeof engine.decode !== "function") {
    renderPanelError(panel, name, "Runtime not available.");
    return;
  }
  var raw;
  try {
    raw = engine.decode(hex);
  } catch (err) {
    renderPanelError(panel, name, lastLine(err));
    return;
  }
  var result;
  try {
    result = JSON.parse(raw);
  } catch (err) {
    renderPanelError(panel, name, lastLine(err));
    return;
  }
  if (name === "python") {
    renderPythonResult(panel, result);
  } else if (name === "rust") {
    renderRustResult(panel, result);
  } else {
    renderCppResult(panel, result);
  }
}

function lastLine(err) {
  // PythonError messages carry the whole traceback; the last line reads best.
  var message = String((err && err.message) || err);
  var lines = message.split("\n").map(function (line) { return line.trim(); }).filter(Boolean);
  return lines.length ? lines[lines.length - 1] : message;
}

function renderPythonResult(panel, result) {
  var frame = result.frame || {};
  var success = frame.ok === true && result.error === 0;
  renderPanel(panel, {
    bannerClass: success ? "banner-ok" : "banner-fail",
    bannerTitle: success ? "Frame OK" : "Frame error",
    bannerDetail: success
      ? "Start/stop byte, length, checksum and records all verified."
      : (result.error_message || frame.error_message || "Unknown problem."),
    header: result.header || {},
    records: result.records || []
  });
}

function renderCppResult(panel, result) {
  var success = result.header_ok === true && result.error_code === 0;
  var count = result.records ? result.records.length : 0;
  renderPanel(panel, {
    bannerClass: success ? "banner-ok" : "banner-fail",
    bannerTitle: success ? "Decoded" : "Decode error",
    bannerDetail: success
      ? "Original C++ library: header + " + count + " records decoded."
      : "The original library reported error code " + result.error_code + ".",
    header: result.header || {},
    records: result.records || []
  });
}

function renderRustResult(panel, result) {
  var success = result.header_ok === true && result.error_code === 0;
  var count = result.records ? result.records.length : 0;
  renderPanel(panel, {
    bannerClass: success ? "banner-ok" : "banner-fail",
    bannerTitle: success ? "Decoded" : "Decode error",
    bannerDetail: success
      ? "Rust port: header + " + count + " records decoded."
      : "The Rust port reported error code " + result.error_code + ".",
    header: result.header || {},
    records: result.records || []
  });
}

function renderPanelError(panel, name, message) {
  renderPanel(panel, {
    bannerClass: "banner-fail",
    bannerTitle: "Decoding failed",
    bannerDetail: message,
    header: null,
    records: null
  });
}

/* Renders one engine's whole panel body: banner, fixed-data-header card and
 * records card. `model` is {bannerClass, bannerTitle, bannerDetail, header,
 * records}; header/records null means "not decoded". */
function renderPanel(panel, model) {
  panel.innerHTML = "";

  var banner = document.createElement("div");
  banner.className = "banner " + model.bannerClass;
  var title = document.createElement("span");
  title.className = "banner-title";
  title.textContent = model.bannerTitle;
  var detail = document.createElement("span");
  detail.textContent = model.bannerDetail;
  banner.appendChild(title);
  banner.appendChild(detail);
  panel.appendChild(banner);

  if (model.header === null) {
    return;
  }

  panel.appendChild(buildHeaderCard(model.header));
  panel.appendChild(buildRecordsCard(model.records || []));
}

function buildHeaderCard(header) {
  var card = document.createElement("section");
  card.className = "card";
  var h = document.createElement("h4");
  h.textContent = "Fixed data header";
  card.appendChild(h);

  var grid = document.createElement("dl");
  grid.className = "kv-grid";
  var entries = flatten(header);
  if (entries.length === 0) {
    var none = document.createElement("p");
    none.className = "muted";
    none.textContent = "No fixed data header decoded for this frame.";
    grid.appendChild(none);
  } else {
    entries.forEach(function (entry) {
      var dt = document.createElement("dt");
      dt.textContent = formatKey(entry[0]);
      var dd = document.createElement("dd");
      dd.textContent = entry[1];
      grid.appendChild(dt);
      grid.appendChild(dd);
    });
  }
  card.appendChild(grid);
  return card;
}

function buildRecordsCard(records) {
  var card = document.createElement("section");
  card.className = "card";
  var h = document.createElement("h4");
  h.textContent = "Records (" + records.length + ")";
  card.appendChild(h);

  if (records.length === 0) {
    var empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No records decoded.";
    card.appendChild(empty);
    return card;
  }

  var scroll = document.createElement("div");
  scroll.className = "table-scroll";
  var table = document.createElement("table");
  table.className = "records-table";
  var thead = document.createElement("thead");
  var headRow = document.createElement("tr");
  ["#", "Property", "Value", "Unit", "VIF", "SubUnit", "Storage", "Tariff"].forEach(function (label) {
    var th = document.createElement("th");
    th.scope = "col";
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  var tbody = document.createElement("tbody");
  var follows = false;
  records.forEach(function (record, index) {
    var row = document.createElement("tr");
    addCell(row, String(index + 1));
    addCell(row, record.name || "-");

    // value_scaled for numeric records, value_string for dates/ASCII.
    var raw = record.value_scaled;
    if (raw === null || raw === undefined) {
      raw = record.value_string;
    }
    addCell(row, raw === null || raw === undefined || raw === "" ? "-" : String(raw));

    addCell(row, record.units || "");
    addCell(row, record.vif || "");
    addCell(row, record.subUnit ? String(record.subUnit) : "");
    addCell(row, record.storage ? String(record.storage) : "");
    addCell(row, record.tariff ? String(record.tariff) : "");

    if (record.telegramFollow) {
      follows = true;
    }
    tbody.appendChild(row);
  });
  table.appendChild(tbody);
  scroll.appendChild(table);
  card.appendChild(scroll);

  if (follows) {
    var note = document.createElement("p");
    note.className = "note-follow";
    note.textContent =
      "This telegram is marked: another telegram is ready for retrieval " +
      "(0x1F end marker).";
    card.appendChild(note);
  }
  return card;
}

/* One level of nesting (status_details.*) -> flat key/value pairs. */
function flatten(obj) {
  var out = [];
  Object.keys(obj).forEach(function (key) {
    var value = obj[key];
    if (value === null || value === undefined || value === "") {
      return;
    }
    if (typeof value === "object" && !Array.isArray(value)) {
      Object.keys(value).forEach(function (subKey) {
        var subValue = value[subKey];
        if (subValue === null || subValue === undefined || subValue === "") {
          return;
        }
        out.push([key + "." + subKey, String(subValue)]);
      });
      return;
    }
    out.push([key, String(value)]);
  });
  return out;
}

/* "status_details.battery_low" -> "status details · battery low": readable,
   and it wraps at spaces instead of mid-word inside the label column. */
function formatKey(key) {
  return String(key).replace(/_/g, " ").replace(/\./g, " \u00b7 ");
}

function addCell(row, text) {
  var cell = document.createElement("td");
  cell.textContent = text;
  row.appendChild(cell);
}

/* ------------------------------------------------------------------ */
/* Wiring                                                              */
/* ------------------------------------------------------------------ */

function clearAll() {
  inputEl.value = "";
  outputEl.hidden = true;
  inputEl.focus();
}

document.addEventListener("DOMContentLoaded", function () {
  statusEl = document.getElementById("runtime-status");
  statusTextEl = document.getElementById("runtime-status-text");
  errorBanner = document.getElementById("error-banner");
  errorTextEl = document.getElementById("error-banner-text");
  retryBtn = document.getElementById("retry-btn");
  inputEl = document.getElementById("hex-input");
  decodeBtn = document.getElementById("decode-btn");
  clearBtn = document.getElementById("clear-btn");
  outputEl = document.getElementById("output");
  panelPython = document.querySelector("#panel-python .panel-body");
  panelCpp = document.querySelector("#panel-cpp .panel-body");
  panelRust = document.querySelector("#panel-rust .panel-body");

  decodeBtn.addEventListener("click", decode);
  clearBtn.addEventListener("click", clearAll);
  retryBtn.addEventListener("click", function () {
    hideError();
    if (!engines.python.ready) { initPython(); }
    if (!engines.cpp.ready) { initCpp(); }
    if (!engines.rust.ready) { initRust(); }
  });

  inputEl.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      if (!decodeBtn.disabled) {
        decode();
      }
    }
  });

  document.querySelectorAll(".btn-example").forEach(function (button) {
    button.addEventListener("click", function () {
      inputEl.value = EXAMPLES[button.dataset.example] || "";
      if (!decodeBtn.disabled) {
        decode();
      }
    });
  });

  updateStatus();
  initPython();
  initCpp();
  initRust();
});
