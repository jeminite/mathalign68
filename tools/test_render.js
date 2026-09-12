#!/usr/bin/env node
/* The analyse page's rendering suite.
 *
 *   npm test        (runs tools/test_engine.js first, then this)
 *
 * WHY IT IS CRUDE
 * It extracts the inline <script> blocks from the BUILT page and runs them in
 * `vm` against a stub DOM. A real headless browser would be a better test and
 * would not run here, and a test that cannot be run is not a test. Taking the
 * built page rather than the template is deliberate: it also proves the
 * placeholder substitution in build/render.py actually happened.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..");
const PAGE = path.join(ROOT, "site", "analyze", "index.html");

let failures = 0;
let checks = 0;

function check(label, got, want) {
  checks++;
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    failures++;
    console.log("FAIL  " + label + "\n        got  " + JSON.stringify(got) +
                "\n        want " + JSON.stringify(want));
  } else {
    console.log("ok    " + label);
  }
}
// Not routed through check(): passing the detail as the "got" value meant a
// failing assertion whose detail was `true` compared true to true and passed.
function ok(label, cond, detail) {
  checks++;
  if (cond) { console.log("ok    " + label); return; }
  failures++;
  console.log("FAIL  " + label +
              (detail === undefined ? "" : "\n        " + JSON.stringify(detail)));
}

if (!fs.existsSync(PAGE)) {
  console.error("site/analyze/index.html is missing -- run python3 publish.py first.");
  process.exit(1);
}
const html = fs.readFileSync(PAGE, "utf8");

/* ------------------------------------------------------------ the built page */

ok("no placeholder survived the build", !/__[A-Z_]+__/.test(html),
   (html.match(/__[A-Z_]+__/g) || []).slice(0, 3));

// The page may load nothing from anywhere else. This is preflight's check too,
// deliberately duplicated: it should fail in the suite a developer runs every
// time, not only at the deploy gate.
const srcs = (html.match(/(?:src|href)\s*=\s*["']([^"']+)["']/g) || [])
  .map((s) => s.replace(/^.*["']([^"']+)["']$/, "$1"))
  .filter((u) => /^(https?:)?\/\//.test(u));
check("the page loads nothing from another origin", srcs, []);
ok("the page has no external script tag at all", !/<script[^>]+src=/.test(html), true);

// One network request, and it is the published data.
const fetches = (html.match(/fetch\(\s*["']([^"']+)["']/g) || [])
  .map((s) => s.replace(/^.*["']([^"']+)["']$/, "$1"));
check("the only fetch is ../data.json", fetches, ["../data.json"]);

ok("the privacy promise is on the page itself",
   /does not leave this computer/.test(html), true);
ok("the guard is present in the shipped page", /assertNoIdentity/.test(html), true);

/* ----------------------------------------------------------------- stub DOM */

function el() {
  const node = {
    innerHTML: "", value: "", hidden: false, files: [], onclick: null, onchange: null,
    classList: { add() {}, remove() {} },
    addEventListener(type, fn) { (this._ev[type] = this._ev[type] || []).push(fn); },
    _ev: {},
  };
  return node;
}

const nodes = { drop: el(), file: el(), out: el(), print: el(), again: el() };
const doc = {
  readyState: "complete",
  getElementById: (id) => (nodes[id] = nodes[id] || el()),
  addEventListener() {},
};

// Real stream globals, not stubs. xlsx.js picks its inflate at call time: with
// `module` undefined it takes the browser path, which is DecompressionStream +
// Blob + Response. Stubbing those would mean the suite exercised a code path
// the browser never runs, and the one the browser DOES run would go untested.
const sandbox = {
  document: doc, window: { print() {} }, console,
  fetch: () => Promise.resolve({ json: () => Promise.resolve(DATA) }),
  Promise, JSON, Math, Object, Array, String, Number, Boolean, Date, RegExp, Error,
  setTimeout, isNaN, parseInt, parseFloat,
  TextDecoder, DecompressionStream, Blob, Response, Uint8Array, DataView, ArrayBuffer,
  module: undefined,
};
sandbox.self = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, "site", "data.json"), "utf8"));

// Run every inline script in order, exactly as the browser would.
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
check("the page carries three inline scripts", scripts.length, 3);
scripts.forEach((src, i) => {
  try { vm.runInContext(src, sandbox, { filename: "inline-" + i + ".js" }); }
  catch (e) { failures++; console.log("FAIL  inline script " + i + " threw: " + e.message); }
});

ok("the reader is exposed to the page", typeof sandbox.XlsxLite === "object", typeof sandbox.XlsxLite);
ok("the engine is exposed to the page", typeof sandbox.ClassEngine === "object", typeof sandbox.ClassEngine);

/* ------------------------------------------------------------ render a report */

const Xlsx = require(path.join(ROOT, "templates", "analyze", "xlsx.js"));
const Engine = require(path.join(ROOT, "templates", "analyze", "engine.js"));

Xlsx.parse(fs.readFileSync(path.join(ROOT, "fixtures", "isa_g6_2026_synthetic.xlsx")))
  .then((grid) => {
    const report = Engine.run(grid, DATA);
    if (report.error) throw new Error("the fixture did not analyse: " + report.error);

    // render() is private to the page's closure, so drive it the way a teacher
    // does: hand a file to the input's change handler. That runs handle(),
    // XlsxLite.parse, ClassEngine.run and render() together, which is the only
    // way to catch a break in the wiring between them.
    const bytes = fs.readFileSync(path.join(ROOT, "fixtures", "isa_g6_2026_synthetic.xlsx"));
    nodes.file.files = [{
      name: "isa.xlsx",
      arrayBuffer: () => Promise.resolve(bytes.buffer.slice(
        bytes.byteOffset, bytes.byteOffset + bytes.byteLength)),
    }];
    nodes.file.onchange();

    // The handler is promise-chained through an inflate; poll rather than
    // guess at a delay, and fail loudly instead of asserting against a page
    // that never finished rendering.
    return new Promise((resolve, reject) => {
      let waited = 0;
      (function poll() {
        const out = nodes.out.innerHTML;
        if (/Every question, against the State/.test(out)) return resolve({ report, out });
        if (/class="err"/.test(out)) return reject(new Error("the page errored: " + out));
        if ((waited += 25) > 5000) return reject(new Error("render never completed; out was: " + out));
        setTimeout(poll, 25);
      })();
    });
  })
  .then(({ report, out }) => {
    ok("something was rendered", out.length > 2000, out.length);
    ok("the test is named", /Grade 6, 2026/.test(out), true);
    ok("the student count is shown", /78<\/strong> students/.test(out), true);

    // The caution comes before any number. Ordering is the whole point of it:
    // a reader who meets the percentages first has already drawn a conclusion.
    const cautionAt = out.indexOf("Before reading anything below");
    const firstPct = out.search(/\d+\.\d%/);
    ok("the small-sample caution precedes the first percentage",
       cautionAt >= 0 && cautionAt < firstPct, [cautionAt, firstPct]);

    ok("NYSED's undefined P-value population is stated, not buried",
       /does not publish the population/.test(out), true);
    ok("the dominant-distractor section rendered", /one wrong answer dominated/.test(out), true);
    ok("the by-class table rendered", /By class/.test(out), true);
    ok("grade 6 alignment shows as not yet placed", /not yet placed/.test(out), true);
    ok("constructed response is kept separate from multiple choice",
       /not a percent correct/.test(out), true);
    ok("items deep-link to the official PDF",
       /nysedregents\.org[^"]*#page=/.test(out), true);

    // The report that was rendered came from the page's own copy of the engine,
    // so the numbers on screen have to be the numbers the suite pinned.
    ok("the overall figure on the page is the engine's",
       out.indexOf(">53.0%<") >= 0, true);
    ok("the state figure on the page is the engine's",
       out.indexOf(">54.8%<") >= 0, true);

    // Nothing identity-shaped may survive rendering either.
    ok("no OSIS-shaped run in the rendered report", !/\b\d{9}\b/.test(out), true);
    ok("no SURNAME, FORENAME in the rendered report",
       !/\b[A-Z]{2,}, ?[A-Z]{2,}\b/.test(out), true);

    console.log("");
    if (failures) {
      console.log(failures + " of " + checks + " checks FAILED");
      process.exit(1);
    }
    console.log(checks + " checks, all render checks passed");
  })
  .catch((err) => { console.error(err); process.exit(1); });
