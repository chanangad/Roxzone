#!/usr/bin/env python3
"""
The guide names watch menus; Google Translate renders those names however it
likes ("Run screen" became "Kør skærm" in Danish, where the watch says
"Løbeskærm"). This marks every watch term in userguide/index.html
notranslate with data-g="<string id>" and writes guide-glossary.js, which
puts the watch's own word for the chosen language into each marked node.

    python3 tools/guide_glossary.py [path/to/Roxzone_site]

Run from the marketing repo root after editing the guide. Idempotent: nodes
already marked are left alone, and the script is rebuilt from the watch's
resources-*/strings/strings.xml every time, so the words cannot drift.

Physical buttons (MENU, SELECT, BACK...) and station names are shielded but
stay English: the buttons are printed on the watch in English, and station
names are kept untranslated by decision.
"""
import html, json, os, re, sys
import xml.etree.ElementTree as ET

WATCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join("..", "Roxzone_site")
GUIDE = os.path.join("userguide", "index.html")
OUT = "guide-glossary.js"

# Site language code (i18n.js LANGUAGES) -> watch resources folder.
LANGS = {"cs": "ces", "da": "dan", "de": "deu", "es": "spa", "fi": "fin", "fr": "fre",
         "hu": "hun", "id": "ind", "it": "ita", "ko": "kor", "nl": "dut", "no": "nob",
         "ja": "jpn", "pl": "pol", "pt-BR": "pob", "pt-PT": "por", "sv": "swe",
         "th": "tha", "zh-CN": "zhs", "zh-TW": "zht"}

# Guide text -> watch string id. Only the watch's own labels: anything the
# guide shows from roxzone.app is translated by Google with the site.
TERMS = {
    "About": "About", "Auto Add Runs": "RunBwStationsLabel", "Build on Phone": "RacePlanBuild",
    "Cancel changes": "ActionCancelChanges", "Clear History": "ClearHistory",
    "Continue": "Continue", "Continue >>": "ContinueArrow",
    "Could not sync - try again": "RacePlanFailed", "Cum D": "CumDelta", "Custom": "Custom",
    "Custom Hyrox": "CustomWorkout", "Delta": "Delta", "Discard": "Discard",
    "Distance + time": "RunScreenDistTime", "Edit Sequence": "Reorder",
    "Full Hyrox": "OfficialHyrox", "GPS Mode": "OutdoorMode", "Half (50%)": "Simulate50",
    "History": "History", "Insert Run Before": "ActionInsertRun", "Manual Unlock": "ManualUnlock",
    "Move": "ActionMove", "My Workouts": "MyWorkouts", "No plan yet": "RacePlanNone",
    "No target": "NoTarget", "None for this workout": "RacePlanMismatch",
    "None found - build one at roxzone.app": "WorkoutSyncNone",
    "None found - build one on your phone": "RacePlanNotFound", "ON PLAN": "LapOnPlan",
    "Online Results": "CloudLinksLabel", "Pace + distance": "RunScreenPaceDist",
    "Pace + time": "RunScreenPaceTime", "Phone not connected": "RacePlanOffline",
    "Quarter (25%)": "Simulate25", "Race Plan": "RacePlan", "Refresh License": "RefreshLicense",
    "Remove Plan": "RacePlanClear", "Remove Run": "ActionRemoveRun",
    "Remove this copy": "ActionRemoveStation", "Removed - Sync restores": "RacePlanRemoved",
    "Repeat station": "ActionRepeatStation", "Resume": "Resume", "Run Distance": "RunDistance",
    "Run screen": "RunScreenLabel", "Save Workout": "SaveWorkout",
    "Save to My Workouts": "SaveToMyWorkouts", "Set All Runs": "SetAllRuns",
    "Set All Stations": "SetAllStations", "Station Details": "StationDetails",
    "Station Weights": "StationWeights", "Sync from Phone": "RacePlanGet",
    "Target Times": "TargetTimes", "This Watch": "RacePlanThisWatch",
    "This watch is not on your account": "RacePlanUnknown", "Three-quarter (75%)": "Simulate75",
    "Time": "RunScreenTime", "Undo Last Lap": "UndoLastLap", "Undo last lap": "UndoLastLap",
    "Weight Category": "Category", "Workout": "PreviewActions", "Start": "QuickStart",
    "Delete": "Delete", "Rename": "Rename",
}
# Section-specific: the same English word is another id there, or is the
# website's button rather than the watch's.
BY_SECTION = {("Start", "warm-up"): "StartWorkout"}
ONLY_IN = {"Delete": {"quick-start-row"}, "Rename": {"quick-start-row"}}

HEADINGS = {"review & start": "ReviewAndStart", "run screen": "RunScreenLabel",
            "warm-up": "WarmUpLabel", "undo last lap": "UndoLastLap",
            "manual unlock": "ManualUnlock", "full hyrox": "OfficialHyrox",
            "custom hyrox": "CustomWorkout", "online results": "CloudLinksLabel"}

# Watch labels the guide also writes in running text, not bold. Marked
# wherever they appear in a text node outside an already-shielded node.
PLAIN = {"Review & Start": "ReviewAndStart", "GPS Mode": "OutdoorMode",
         "My Workouts": "MyWorkouts", "Target Times": "TargetTimes",
         "Set Target Pace": "RunPace", "Online Results": "CloudLinksLabel",
         "Warm-Up": "WarmUpLabel", "Race Plan": "RacePlan"}

ENGLISH_ONLY = {"MENU", "SELECT", "BACK", "Down", "Up", "LAP", "START", "Lap", "ROXZONE",
                "Air Bike", "Battle Ropes", "Burpees", "KB Swings", "Box Jumps", "Bike Erg",
                "Sled Push", "Sled Pull", "Farmers Carry", "SB Lunges", "Wall Balls"}

def mark_plain(body, used):
    """Wrap PLAIN labels found in text nodes. Walks the markup by hand so
    tags, scripts, styles and anything inside a notranslate node are left
    alone; that also makes a second run a no-op."""
    from html.parser import HTMLParser
    VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr", "area", "col", "embed", "param", "track"}
    spans = []  # (start, end) offsets of text nodes that may be marked

    class P(HTMLParser):
        # Text arrives split at every entity ("Review ", "&amp;", " Start"),
        # so consecutive pieces are joined into one raw run before matching.
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.stack = []
            self.run_start = None
            self.run_raw = ""
        def flush(self):
            if self.run_start is not None and not (self.stack and self.stack[-1][1]):
                spans.append((self.run_start, self.run_raw))
            self.run_start, self.run_raw = None, ""
        def piece(self, raw):
            if self.run_start is None:
                line, col = self.getpos()
                self.run_start = offset(line, col)
            self.run_raw += raw
        def handle_entityref(self, name): self.piece("&%s;" % name)
        def handle_charref(self, name): self.piece("&#%s;" % name)
        def handle_startendtag(self, tag, attrs): self.flush()
        def handle_comment(self, data): self.flush()
        def handle_starttag(self, tag, attrs):
            self.flush()
            if tag in VOID: return
            a = dict(attrs)
            shield = ("notranslate" in (a.get("class") or "") or a.get("translate") == "no"
                      or tag in ("script", "style", "title", "svg"))
            inherited = bool(self.stack) and self.stack[-1][1]
            self.stack.append((tag, bool(shield or inherited)))
        def handle_endtag(self, tag):
            self.flush()
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    del self.stack[i:]; break
        def handle_data(self, data): self.piece(data)

    lines = body.split("\n")
    starts = [0]
    for ln in lines[:-1]: starts.append(starts[-1] + len(ln) + 1)
    def offset(line, col): return starts[line - 1] + col

    p = P(); p.feed(body); p.flush()
    pat = re.compile("|".join(re.escape(html.escape(k, quote=False)) for k in sorted(PLAIN, key=len, reverse=True)))
    out, last = [], 0
    for start, data in spans:
        for m in pat.finditer(data):
            a, b = start + m.start(), start + m.end()
            if a < last: continue
            key = html.unescape(m.group(0)); gid = PLAIN[key]; used.add(gid)
            lead = body[a - 1] == " "
            trail = b < len(body) and body[b] == " "
            out.append(body[last:a - 1] if lead else body[last:a])
            out.append('<span class="notranslate" translate="no" data-g="%s">%s%s%s</span>'
                       % (gid, "&nbsp;" if lead else "", m.group(0), "&nbsp;" if trail else ""))
            last = b + 1 if trail else b
    out.append(body[last:])
    return "".join(out)

def strings(folder):
    p = os.path.join(WATCH, folder, "strings", "strings.xml")
    out = {}
    for el in ET.parse(p).getroot().iter("string"):
        out[el.get("id")] = (el.text or "").strip()
    return out

def main():
    s = open(GUIDE, encoding="utf-8").read()
    head, body = s[:s.index("<body")], s[s.index("<body"):]
    used = set()

    def section_at(pos):
        ids = re.findall(r'id="([a-z0-9-]+)"', body[:pos])
        return ids[-1] if ids else ""

    def strong(m):
        raw = m.group(2)
        text = html.unescape(raw)
        sec = section_at(m.start())
        if text in ENGLISH_ONLY:
            attrs = ' class="notranslate" translate="no"'
        elif text in TERMS and (text not in ONLY_IN or sec in ONLY_IN[text]):
            gid = BY_SECTION.get((text, sec), TERMS[text])
            used.add(gid)
            attrs = ' class="notranslate" translate="no" data-g="%s"' % gid
        else:
            return m.group(0)
        # Google drops the space between a shielded node and the text around
        # it, so the space moves inside the node as &nbsp;.
        lead = "&nbsp;" if m.group(1) else ""
        trail = "&nbsp;" if m.group(3) else ""
        return "<strong%s>%s%s%s</strong>" % (attrs, lead, raw, trail)

    body = re.sub(r"( ?)<strong>([^<]{1,60})</strong>( ?)", strong, body)

    def heading(m):
        text = html.unescape(m.group(2)).strip()
        gid = HEADINGS.get(text.lower())
        if not gid: return m.group(0)
        used.add(gid)
        return '%s<span class="notranslate" translate="no" data-g="%s">%s</span>%s' % (m.group(1), gid, m.group(2), m.group(3))

    body = re.sub(r'(<h3 class="(?:manual-section__title|rz-flow__title)"[^>]*>)([^<]{2,60})(</h3>)', heading, body)
    body = re.sub(r'(<li><a href="#[^"]+">)([^<]{2,60})(</a></li>)', heading, body)

    body = mark_plain(body, used)

    if "guide-glossary.js" not in body:
        body = body.replace('<script src="../i18n.js?v=4"></script>',
                            '<script src="../i18n.js?v=4"></script>\n  <script src="../guide-glossary.js?v=1"></script>', 1)
    open(GUIDE, "w", encoding="utf-8").write(head + body)

    # Every id in use, whether marked this run or an earlier one.
    used |= set(re.findall(r'data-g="([A-Za-z0-9]+)"', body))
    words = {}
    for code, folder in LANGS.items():
        tbl = strings("resources-" + folder)
        for gid in sorted(used):
            if gid in tbl and tbl[gid]:
                words.setdefault(gid, {})[code] = tbl[gid]
    missing = sorted(g for g in used if g not in words)
    js = """// Generated by tools/guide_glossary.py from the watch's strings.xml files.
// Do not edit by hand: run the script after changing the guide.
//
// Nodes marked data-g="<watch string id>" are notranslate; this writes the
// watch's own word for the site's chosen language into them, so the guide
// names every menu exactly as the watch shows it. Runs on load and again
// when a language pill is tapped (i18n.js stores the choice first).
(function () {
  var W = %s;
  function lang() {
    try { return localStorage.getItem("roxzone-lang") || "en"; } catch (e) { return "en"; }
  }
  function apply() {
    var code = lang(), els = document.querySelectorAll("[data-g]");
    for (var i = 0; i < els.length; i++) {
      var el = els[i], t = el.textContent;
      // Remember the English once; it is what "en" puts back.
      if (el.__en === undefined) { el.__en = t.replace(/^[\\s\\u00a0]+|[\\s\\u00a0]+$/g, ""); }
      var w = (W[el.getAttribute("data-g")] || {})[code] || el.__en;
      // Keep the node's own edge spaces (the &nbsp; Google would drop).
      var lead = t.match(/^[\\s\\u00a0]*/)[0], trail = t.match(/[\\s\\u00a0]*$/)[0];
      if (t !== lead + w + trail) { el.textContent = lead + w + trail; }
    }
  }
  apply();
  document.addEventListener("click", function (e) {
    var pill = e.target.closest && e.target.closest(".lang-pill");
    if (pill) { setTimeout(apply, 0); }
  });
})();
""" % json.dumps(words, ensure_ascii=False, indent=1, sort_keys=True)
    open(OUT, "w", encoding="utf-8").write(js)
    print("ids used:", len(used), " languages:", len(LANGS), " missing in watch strings:", missing)
    print("marked nodes:", len(re.findall(r'data-g="', body)), " english-only shields:",
          len(re.findall(r'<strong class="notranslate" translate="no">', body)))

if __name__ == "__main__":
    main()
