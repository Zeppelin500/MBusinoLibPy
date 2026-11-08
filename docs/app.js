/* MBusinoLibPy Web Decoder - plain JavaScript, no framework, no build step.
 *
 * The library source is fetched at runtime from jsDelivr's GitHub CDN with
 * the @main pin so this page always tests the current upstream main branch:
 * no library copy lives in this repository, and the served code can never
 * silently drift from the repo it demonstrates.
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

var pyodide = null;
var decodeJson = null;
var ready = false;
var initRunning = false;

var statusEl, statusTextEl, errorBanner, errorTextEl, retryBtn;
var inputEl, decodeBtn, clearBtn, outputEl, resultBanner;
var headerCard, headerGrid, recordsCard, recordsBody, recordsEmpty, recordsHeading;

/* ------------------------------------------------------------------ */
/* Runtime status                                                      */
/* ------------------------------------------------------------------ */

function setStatus(state, text) {
  statusEl.classList.remove("is-loading", "is-ready", "is-error");
  statusEl.classList.add("is-" + state);
  statusTextEl.textContent = text;
}

function showError(message) {
  errorTextEl.textContent = " " + message + " Check your connection and retry.";
  errorBanner.hidden = false;
}

function hideError() {
  errorBanner.hidden = true;
}

/* ------------------------------------------------------------------ */
/* Pyodide startup                                                     */
/* ------------------------------------------------------------------ */

async function init() {
  if (initRunning || ready) {
    return;
  }
  initRunning = true;
  hideError();
  setStatus("loading", "Loading Python runtime... (about 10 MB on first visit)");
  decodeBtn.disabled = true;

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
    decodeJson = pyodide.globals.get("decode_json");

    ready = true;
    setStatus("ready", "Ready");
    decodeBtn.disabled = false;
  } catch (err) {
    setStatus("error", "Failed to load the Python runtime");
    showError(String((err && err.message) || err));
  } finally {
    initRunning = false;
  }
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

  var result;
  try {
    result = JSON.parse(decodeJson(hex));
  } catch (err) {
    renderPythonError(err);
    return;
  }
  renderResult(result);
}

function renderPythonError(err) {
  outputEl.hidden = false;
  headerCard.hidden = true;
  recordsCard.hidden = true;
  resultBanner.className = "banner banner-fail";
  resultBanner.innerHTML = "";
  var title = document.createElement("span");
  title.className = "banner-title";
  title.textContent = "Decoding failed:";
  var detail = document.createElement("span");
  // PythonError messages carry the whole traceback; the last line is the
  // actual exception and reads much better in a small banner.
  var message = String((err && err.message) || err);
  var lines = message.split("\n").map(function (line) { return line.trim(); }).filter(Boolean);
  detail.textContent = lines.length ? lines[lines.length - 1] : message;
  resultBanner.appendChild(title);
  resultBanner.appendChild(detail);
}

function renderResult(result) {
  outputEl.hidden = false;

  var frame = result.frame || {};
  var success = frame.ok === true && result.error === 0;
  resultBanner.className = "banner " + (success ? "banner-ok" : "banner-fail");
  resultBanner.innerHTML = "";
  var title = document.createElement("span");
  title.className = "banner-title";
  title.textContent = success ? "Frame OK" : "Frame error";
  var detail = document.createElement("span");
  detail.textContent = success
    ? "Start/stop byte, length, checksum and records all verified."
    : (result.error_message || frame.error_message || "Unknown problem.");
  resultBanner.appendChild(title);
  resultBanner.appendChild(detail);

  renderHeader(result.header || {});
  renderRecords(result.records || []);
}

function renderHeader(header) {
  var entries = flatten(header);
  headerGrid.innerHTML = "";
  if (entries.length === 0) {
    headerCard.hidden = false;
    var note = document.createElement("p");
    note.className = "muted";
    note.textContent = "No fixed data header decoded for this frame.";
    headerGrid.appendChild(note);
    return;
  }
  entries.forEach(function (entry) {
    var dt = document.createElement("dt");
    dt.textContent = entry[0];
    var dd = document.createElement("dd");
    dd.textContent = entry[1];
    headerGrid.appendChild(dt);
    headerGrid.appendChild(dd);
  });
  headerCard.hidden = false;
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

function renderRecords(records) {
  recordsBody.innerHTML = "";
  recordsCard.hidden = false;
  recordsHeading.textContent = "Records (" + records.length + ")";
  if (records.length === 0) {
    recordsEmpty.hidden = false;
    return;
  }
  recordsEmpty.hidden = true;

  records.forEach(function (record, index) {
    var row = document.createElement("tr");

    var num = document.createElement("td");
    num.textContent = String(index + 1);
    row.appendChild(num);

    var name = document.createElement("td");
    name.textContent = record.name || "-";
    row.appendChild(name);

    var value = document.createElement("td");
    var raw = record.value_scaled;
    if (raw === null || raw === undefined) {
      raw = record.value_string;
    }
    value.textContent = raw === null || raw === undefined || raw === "" ? "-" : String(raw);
    row.appendChild(value);

    var unit = document.createElement("td");
    unit.textContent = record.units || "";
    row.appendChild(unit);

    recordsBody.appendChild(row);
  });
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
  resultBanner = document.getElementById("result-banner");
  headerCard = document.getElementById("header-card");
  headerGrid = document.getElementById("header-grid");
  recordsCard = document.getElementById("records-card");
  recordsBody = document.querySelector("#records-table tbody");
  recordsEmpty = document.getElementById("records-empty");
  recordsHeading = document.getElementById("records-heading");

  decodeBtn.addEventListener("click", decode);
  clearBtn.addEventListener("click", clearAll);
  retryBtn.addEventListener("click", init);

  inputEl.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      if (ready) {
        decode();
      }
    }
  });

  document.querySelectorAll(".btn-example").forEach(function (button) {
    button.addEventListener("click", function () {
      inputEl.value = EXAMPLES[button.dataset.example] || "";
      if (ready) {
        decode();
      }
    });
  });

  init();
});
