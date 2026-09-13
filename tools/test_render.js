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
       out.indexOf(">50.4%<") >= 0, true);
    ok("the state figure on the page is the engine's",
       out.indexOf(">54.8%<") >= 0, true);

    // The three new sections.
    ok("the areas-of-focus section rendered", /Where to focus next year/.test(out), true);
    ok("it explains that weight matters, not just gap",
       /how many credits that standard actually carries/.test(out), true);
    ok("the proficiency-gating section rendered", /What gates proficiency/.test(out), true);
    ok("band sizes are shown, not hidden", /Level 1 \(\d+ students\)/.test(out), true);
    ok("the gating threshold is stated on the page", /at least \d+% of its credits/.test(out), true);
    ok("the pacing section rendered", /When the gating content is taught/.test(out), true);
    ok("the table's unit-level accuracy is stated", /96\.3% of the time/.test(out), true);

    // The sentence that keeps the page honest. Closing the State gap is worth
    // far less than it sounds, and the page has to say so where the figure is.
    ok("the page says closing the State gap does not move a level",
       /not<\/strong>\s*the same as moving a student up a level/.test(out), true);

    // Ordering: what happened comes before what to do about it.
    const gapAt = out.indexOf("Every question, against the State");
    const focusAt = out.indexOf("Where to focus next year");
    ok("the results precede the recommendations", gapAt >= 0 && gapAt < focusAt, [gapAt, focusAt]);

    // Checkpoints
    ok("the checkpoint section rendered", /What to ask, and when/.test(out), true);
    ok("it says the questions are NYSED's own", /nothing here\s*is invented/.test(out), true);
    ok("the cap is explained, not just applied", /an exam does not get used/.test(out), true);
    ok("an answer key is present", /Answer key/.test(out), true);
    ok("the answer key comes after the questions",
       out.indexOf("Answer key") > out.indexOf("What to ask, and when"), true);
    ok("checkpoint items deep-link to the official page",
       /official page/.test(out), true);
    ok("Unit 7's missing mid-unit assessment is called out",
       /has no mid-unit assessment/.test(out), true);
    ok("the unschedulable gating standard is named",
       /NY-6\.G\.5/.test(out) && /Check it by hand/.test(out), true);
    // Figures are served from the site's own assets, not from anywhere else.
    const figs = (out.match(/<img[^>]+src="([^"]+)"/g) || [])
      .map((m) => m.replace(/^.*src="([^"]+)".*$/, "$1"));
    ok("every checkpoint figure is a same-origin asset path",
       figs.every((u) => u.indexOf("../assets/") === 0), figs.slice(0, 3));
    ok("no instructions array leaked as a comma-joined string",
       !/Show your work\.,/.test(out), true);

    // Every class the report uses must actually be styled.
    //
    // This is the nearest automated thing to looking at the page: a class name
    // that was written in the renderer and never in the stylesheet produces a
    // page that is correct in structure and wrong on screen, which no other check
    // here would notice. It is not a substitute for opening the page, and does not
    // pretend to be -- it catches one specific class of mistake that otherwise
    // only shows up visually.
    const styleBlocks = (html.match(/<style>([\s\S]*?)<\/style>/g) || [])
      .map((b) => b.replace(/^<style>|<\/style>$/g, "")).join("\n");
    const usedClasses = new Set();
    (out.match(/class="([^"]+)"/g) || []).forEach((m) => {
      m.replace(/^class="|"$/g, "").split(/\s+/).forEach((c) => { if (c) usedClasses.add(c); });
    });
    const definedClasses = new Set(
      (styleBlocks.match(/\.[A-Za-z][\w-]*/g) || []).map((c) => c.slice(1)));
    const unstyled = [...usedClasses].filter((c) => !definedClasses.has(c));
    check("every class the report uses is styled", unstyled, []);

    // The print rules, which are the whole point of a checkpoint sheet. There are
    // several @media print blocks -- one per stylesheet -- so they are matched by
    // brace depth and merged; reading only the first found base.css's and reported
    // every rule in analyze.css as missing.
    const printBlocks = [];
    for (let at = styleBlocks.indexOf("@media print"); at >= 0;
         at = styleBlocks.indexOf("@media print", at + 1)) {
      const open = styleBlocks.indexOf("{", at);
      let depth = 0, end = open;
      for (let k = open; k < styleBlocks.length; k++) {
        if (styleBlocks[k] === "{") depth++;
        else if (styleBlocks[k] === "}" && --depth === 0) { end = k; break; }
      }
      printBlocks.push(styleBlocks.slice(open + 1, end));
    }
    const printCss = printBlocks.join("\n");
    ok("there is a print stylesheet", printBlocks.length > 0, printBlocks.length);
    // The selector is given plain and escaped where it is used, so the label reads
    // as a selector rather than as a regex.
    [".drop", ".actions", ".cp", ".cp-q", ".answers"].forEach((sel) => {
      const esc2 = sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      ok("print rules cover " + sel,
         new RegExp("(^|[,{}\\s])" + esc2 + "\\s*[,{]", "m").test(printCss), true);
    });
    ok("a checkpoint starts on its own page",
       /\.cp\s*\{[^}]*page-break-before\s*:\s*always/.test(printCss), true);
    ok("a question never splits across a page",
       /\.cp-q\s*\{[^}]*page-break-inside\s*:\s*avoid/.test(printCss), true);
    ok("the answer key starts on its own page",
       /\.answers\s*\{[^}]*page-break-before\s*:\s*always/.test(printCss), true);

    // An individual proficiency level must not reach the page. The curve and the
    // band percentages are aggregate; a per-student PL is not.
    ok("no per-student proficiency level in the rendered report",
       !/"pl"\s*:/.test(out), true);

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
