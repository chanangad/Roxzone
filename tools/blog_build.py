#!/usr/bin/env python3
"""Build the blog from blog/_src/*.html.

Run from the repo root after editing a post:  python3 tools/blog_build.py

Each source file starts with an HTML comment holding a JSON header, then the
post body:

    <!--{
      "slug": "garmin-setup-first-hyrox",
      "title": "How to set up your Garmin for your first HYROX",
      "seo_title": "...",          (optional, the <title>; " | ROXZONE" is added)
      "description": "...",
      "card": "...",               (optional, the line on cards; defaults to description)
      "date": "2026-11-20",
      "updated": "2026-11-20",     (optional)
      "category": "Setup",         (one of CATEGORIES; the label on cards and the index filter)
      "order": 1,                  (ties on the same date: lower first)
      "image": "assets/guide/06-run.webp",
      "hero": ["garmin-setup-first-hyrox", "alt text"],   (optional photo under the title: assets/blog/<name>-1440.webp,
                                                           -720.webp, -1440.jpg, and <name>-share.jpg for link previews)
      "guide": [["race-plan", "Race Plan in the guide"]],
      "related": ["first-hyrox-pacing"]
    }-->
    <p class="post__lede">...</p>
    ...

Shorthand in the body (kept out of Google Translate, with the space inside so
the translated text keeps its gaps):
    {{*LAP}}        a button name, bold
    {{Sled Push}}   a station or watch term

Writes blog/<slug>/index.html, blog/index.html, blog/feed.xml and the blog
block of sitemap.xml. Standard library only. Output is committed: GitHub
Pages serves it as it is, and the leading underscore keeps _src off the site.
"""
import datetime, html, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "blog", "_src")
SITE = "https://roxzone.app"
STORE = "https://apps.garmin.com/apps/95ff2e3b-7417-4bcf-8ced-7e4b70113616"
V = {"styles": "82", "blog": "2", "pixel": "3", "i18n": "7", "headroom": "2", "favicon": "2"}
OG_IMAGE = SITE + "/og-v2.jpg"
# The index filter shows these in this order, only the ones in use.
CATEGORIES = ["Setup", "Race day", "Pacing", "Training", "Stations", "Updates"]


def esc(s):
    return html.escape(s, quote=True)


def shorthand(body):
    # The gap next to a shielded word goes inside it as &nbsp; (Google drops a
    # plain space there). A side gets one when the source had a space or a
    # letter right against the braces: "press{{*LAP}}at" and "press {{*LAP}} at"
    # both come out as "press<strong>&nbsp;LAP&nbsp;</strong>at".
    def one(m):
        start, end = m.start(), m.end()
        before = body[start - 1] if start else ""
        after = body[end] if end < len(body) else ""
        star, word = m.group(2), m.group(3)
        lead = m.group(1) or before.isalnum()
        tail = m.group(4) or after.isalnum()
        inner = ("&nbsp;" if lead else "") + word + ("&nbsp;" if tail else "")
        # A shielded word that ends a sentence with another one after it:
        # Google drops the full stop and glues the next sentence on
        # ("LAPDas ist..."). Inside the shield, with the gap, it survives.
        if m.group(4) == ". ":
            inner = ("&nbsp;" if lead else "") + word + ".&nbsp;"
        tag = "strong" if star else "span"
        return '<%s class="notranslate" translate="no">%s</%s>' % (tag, inner, tag)
    return re.sub(r"( ?)\{\{(\*?)([^{}]+?)\}\}(\. (?=[^<\s])| ?)", one, body)


def read_posts():
    posts = []
    for name in sorted(os.listdir(SRC)):
        if not name.endswith(".html"):
            continue
        raw = open(os.path.join(SRC, name), encoding="utf-8").read()
        m = re.match(r"\s*<!--(.*?)-->\s*", raw, re.S)
        if not m:
            sys.exit("%s: no JSON header" % name)
        meta = json.loads(m.group(1))
        meta["body"] = shorthand(raw[m.end():].strip())
        if meta["slug"] + ".html" != name:
            sys.exit("%s: slug does not match the file name" % name)
        meta.setdefault("updated", meta["date"])
        meta.setdefault("card", meta["description"])
        meta.setdefault("related", [])
        meta.setdefault("guide", [])
        meta.setdefault("faq", [])
        meta.setdefault("keywords", [])
        # Search results cut a title at about 60 characters and a description
        # at about 155; say so here instead of finding out in the results.
        full_title = (meta.get("seo_title") or meta["title"]) + " | ROXZONE"
        if len(full_title) > 60:
            print("note: %s title is %d characters (60 is the cut)" % (name, len(full_title)))
        if len(meta["description"]) > 158:
            print("note: %s description is %d characters (155 is the cut)" % (name, len(meta["description"])))
        if meta.get("category") not in CATEGORIES:
            sys.exit("%s: category must be one of %s" % (name, ", ".join(CATEGORIES)))
        words = len(re.sub(r"<[^>]+>", " ", meta["body"]).split())
        meta["words"] = words
        meta["minutes"] = max(1, int(math.ceil(words / 220.0)))
        meta["url"] = "%s/blog/%s/" % (SITE, meta["slug"])
        posts.append(meta)
    posts.sort(key=lambda p: (p["date"], -p.get("order", 0)), reverse=True)
    return posts


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def head(r, title, desc, canonical, og_type, extra="", og_image=None, og_size=(1440, 720)):
    og_image = og_image or OG_IMAGE
    return """<!doctype html>
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <meta name="theme-color" content="#0b0b0c">
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" type="application/atom+xml" title="ROXZONE blog" href="{site}/blog/feed.xml">

  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="ROXZONE">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{og_image}">
  <meta property="og:image:width" content="{ogw}">
  <meta property="og:image:height" content="{ogh}">
  <meta property="og:locale" content="en_US">
{extra}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{og_image}">

  <link rel="icon" type="image/png" href="{r}favicon.png?v={vf}">
  <link rel="apple-touch-icon" href="{r}favicon.png?v={vf}">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap"
    rel="stylesheet">
  <link rel="stylesheet" href="{r}styles.css?v={vs}">
  <link rel="stylesheet" href="{r}blog.css?v={vb}">
""".format(title=esc(title), desc=esc(desc), canonical=canonical, og_type=og_type, site=SITE,
           og_image=og_image, ogw=og_size[0], ogh=og_size[1], extra=extra, r=r,
           vf=V["favicon"], vs=V["styles"], vb=V["blog"])


def topbar(r):
    return """<body>
  <header class="topbar" data-headroom>
    <a href="{r}" class="topbar__brand notranslate" translate="no">ROXZONE</a>
    <button type="button" class="topbar__burger" aria-label="Menu" aria-expanded="false" aria-controls="topnav"><i></i><i></i><i></i></button>
    <nav class="topbar__nav" id="topnav">
      <a href="{r}userguide/" class="topbar__tab topbar__tab--dim">Guide</a>
      <a href="{r}faq/" class="topbar__tab topbar__tab--dim notranslate" translate="no">FAQ</a>
      <a href="{r}blog/" class="topbar__tab topbar__tab--active">Blog</a>
      <a class="topbar__store" href="{store}" target="_blank" rel="noopener"><img src="{r}assets/connect-iq-badge-black.svg" width="278" height="95" alt="Available on the Connect IQ Store" loading="lazy" decoding="async"></a>
    </nav>
    <nav class="modeswitch" aria-label="Store or account">
      <a href="{r}" class="modeswitch__opt modeswitch__opt--on notranslate" translate="no">Store</a>
      <a href="/me" class="modeswitch__opt">My<span class="notranslate" translate="no">&nbsp;ROXZONE</span></a>
    </nav>
    <div class="topbar__lang" data-lang-picker></div>
  </header>
""".format(r=r, store=STORE)


def footer(r):
    return """
  <footer class="site-footer">
    <nav class="site-footer__links">
      <a href="{r}">Home</a>
      <a href="{r}userguide/">User Guide</a>
      <a href="{r}faq/">FAQ</a>
      <a href="https://www.instagram.com/roxzone.app" target="_blank" rel="noopener">Instagram</a>
      <a href="{r}featured/?from=footer">Get featured</a>
      <a href="https://www.reddit.com/r/roxzone_app/" target="_blank" rel="noopener">Reddit</a>
      <a href="{r}privacy/">Privacy Policy</a>
      <a href="{r}refund/">Refund Policy</a>
      <a href="mailto:hello@roxzone.app">Support</a>
    </nav>
    <p class="site-footer__legal">ROXZONE is an independent training tool and is not affiliated with or endorsed by HYROX.</p>
    <p class="site-footer__copy">© 2026 Chan Digital. All rights reserved.</p>
  </footer>

  <script src="{r}i18n.js?v={vi}"></script>
  <script src="{r}headroom.js?v={vh}"></script>
</body>

</html>
""".format(r=r, vi=V["i18n"], vh=V["headroom"])


def pixel(r):
    return '  <script src="%spixel.js?v=%s" defer></script>\n' % (r, V["pixel"])


def ld(obj):
    return '  <script type="application/ld+json">\n%s\n  </script>\n' % json.dumps(obj, indent=2, ensure_ascii=False)


ORG = {"@type": "Organization", "name": "ROXZONE", "url": SITE + "/", "logo": SITE + "/app-icon.png"}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def card(p, r, heading="h3", feature=False):
    # Text only. The index lays these out as rows (the newest as a lead),
    # the home page and "Read next" as columns; blog.css does both.
    return """      <a class="blog-card{feat}" href="{r}blog/{slug}/" data-cat="{cat_id}">
        <span class="blog-card__meta"><span class="blog-card__cat blog-card__cat--{cat_id}">{cat}</span><span aria-hidden="true"> · </span>{date}</span>
        <{h} class="blog-card__title">{title}</{h}>
        <span class="blog-card__text">{card}</span>
        <span class="blog-card__more">{mins} min read<span aria-hidden="true"> &rarr;</span></span>
      </a>
""".format(feat=" blog-card--feature" if feature else "", r=r, slug=p["slug"], mins=p["minutes"], h=heading,
           title=esc(p["title"]), card=esc(p["card"]), cat=esc(p["category"]), cat_id=slugify(p["category"]),
           date=nice_date(p["date"]))


def row(p, r):
    """A post on the blog index: category and date, title, summary, and the
    reading time set like a split time on the right."""
    return """      <a class="blog-row" href="{r}blog/{slug}/" data-cat="{cat_id}">
        <span class="blog-row__main">
          <span class="blog-row__meta"><span class="blog-row__cat blog-row__cat--{cat_id}">{cat}</span><span class="blog-row__date">{date}</span></span>
          <h2 class="blog-row__title">{title}</h2>
          <span class="blog-row__text">{card}</span>
        </span>
        <span class="blog-row__time"><span class="blog-row__num notranslate" translate="no">{mins}</span><span class="blog-row__unit">min read</span></span>
        <span class="blog-row__arrow" aria-hidden="true">&rarr;</span>
      </a>
""".format(r=r, slug=p["slug"], mins=p["minutes"], title=esc(p["title"]), card=esc(p["card"]),
           cat=esc(p["category"]), cat_id=slugify(p["category"]), date=nice_date(p["date"]))


def closing(p, r):
    guide = p["guide"] if p else []
    links = ""
    if guide:
        links = ('        <ul class="post-end__links">%s\n        </ul>\n'
                 % "".join('\n          <li><a href="%suserguide/#%s">%s</a></li>' % (r, a, esc(t)) for a, t in guide))
    return """
      <aside class="post-end" aria-labelledby="post-end-title">
        <p class="post-end__eyebrow">ROXZONE for Garmin</p>
        <h2 id="post-end-title" class="post-end__title">Race your next HYROX with a plan</h2>
        <p class="post-end__text">Choose your category and start. Every run and station named, the Roxzone timed, and your goal split into a target for every leg, with ahead or behind on your wrist the whole way. One-time purchase, no subscription.</p>
        <div class="post-end__ctas">
          <a class="post-btn" href="{store}" target="_blank" rel="noopener">Get it on Connect IQ</a>
          <a class="post-btn post-btn--ghost" href="/me/plan">Build your race plan</a>
        </div>
{links}      </aside>
""".format(store=STORE, links=links)


def plain(text):
    """Shorthand out, for places that take plain text (structured data)."""
    return re.sub(r"\{\{\*?([^{}]+?)\}\}", r"\1", text)


def faq_section(p):
    # The questions people type into a search box, answered in two or three
    # sentences from what the post already says. The same list feeds the
    # FAQPage data, so the page and its data cannot drift apart.
    if not p["faq"]:
        return ""
    rows = "".join('        <h3>%s</h3>\n        <p>%s</p>\n' % (esc(q), shorthand(a)) for q, a in p["faq"])
    return ('\n        <section class="post-faq" aria-labelledby="post-faq-title">\n'
            '        <h2 id="post-faq-title">Common questions</h2>\n%s        </section>\n') % rows


def post_page(p, posts):
    r = "../../"
    title = (p.get("seo_title") or p["title"]) + " | ROXZONE"
    extra = ('  <meta property="article:published_time" content="%sT08:00:00Z">\n'
             '  <meta property="article:modified_time" content="%sT08:00:00Z">\n') % (p["date"], p["updated"])
    image = SITE + "/" + p["image"]
    hero, share, share_size = "", None, (1440, 720)
    if p.get("hero"):
        name, alt = p["hero"]
        base = "assets/blog/" + name
        share, share_size = SITE + "/" + base + "-share.jpg", (1200, 630)
        image = share
        # Phones get a tighter 3:2 crop when one exists, so the watch stays readable.
        phone = ""
        if os.path.exists(os.path.join(ROOT, base + "-phone.webp")):
            phone = '          <source media="(max-width: 640px)" type="image/webp" srcset="%s%s-phone.webp" width="1080" height="720">\n' % (r, base)
        hero = """      <figure class="post__hero">
        <picture>
{phone}          <source type="image/webp" srcset="{r}{b}-720.webp 720w, {r}{b}-1440.webp 1440w" sizes="(max-width: 760px) 100vw, 720px">
          <img src="{r}{b}-1440.jpg" width="1440" height="810" fetchpriority="high" decoding="async" alt="{alt}">
        </picture>
      </figure>
""".format(r=r, b=base, alt=esc(alt), phone=phone)
    posting = {"@type": "BlogPosting", "@id": p["url"] + "#post", "headline": p["title"],
               "description": p["description"], "image": [image, OG_IMAGE],
               "datePublished": p["date"], "dateModified": p["updated"],
               "inLanguage": "en", "mainEntityOfPage": p["url"],
               "articleSection": p["category"], "wordCount": p["words"],
               "isPartOf": {"@type": "Blog", "name": "ROXZONE blog", "url": SITE + "/blog/"},
               "author": ORG, "publisher": ORG}
    if p["keywords"]:
        posting["keywords"] = ", ".join(p["keywords"])
    graph = [
        posting,
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": SITE + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": p["url"]}]},
    ]
    if p["faq"]:
        graph.append({"@type": "FAQPage", "@id": p["url"] + "#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(a)}}
            for q, a in p["faq"]]})
    data = ld({"@context": "https://schema.org", "@graph": graph})
    rel = [q for s in p["related"] for q in posts if q["slug"] == s]
    read_next = ""
    if rel:
        read_next = ('\n      <section class="post-next" aria-labelledby="post-next-title">\n'
                     '        <h2 id="post-next-title" class="post-next__title">Read next</h2>\n'
                     '        <div class="blog-grid blog-grid--two">\n%s        </div>\n      </section>\n'
                     ) % "".join(card(q, r) for q in rel)
    updated = ""
    if p["updated"] != p["date"]:
        updated = ' · Updated <time datetime="%s">%s</time>' % (p["updated"], nice_date(p["updated"]))
    return (head(r, title, p["description"], p["url"], "article", extra, share, share_size) + data + pixel(r) + "</head>\n\n"
            + topbar(r) + """
  <main class="page-shell">
    <article class="post">
      <nav class="post__crumbs" aria-label="Breadcrumb"><a href="../">Blog</a><span aria-hidden="true"> · </span><span>{cat}</span></nav>
      <h1 class="post__title">{title}</h1>
      <p class="post__meta"><time datetime="{date}">{nice}</time>{updated} · {mins} min read</p>
{hero}
      <div class="post__body">
{body}
{faq}      </div>
{closing}{read_next}    </article>
  </main>
""".format(title=esc(p["title"]), hero=hero, cat=esc(p["category"]), date=p["date"], nice=nice_date(p["date"]), updated=updated,
           mins=p["minutes"], body=p["body"], faq=faq_section(p), closing=closing(p, r), read_next=read_next)
            + footer(r))


def index_page(posts):
    r = "../"
    title = "Blog: HYROX on your Garmin | ROXZONE"
    desc = ("Articles for HYROX athletes with a Garmin watch: setting up your watch, race day, "
            "and pacing your first race with a plan.")
    data = ld({
        "@context": "https://schema.org", "@type": "Blog", "@id": SITE + "/blog/#blog",
        "name": "ROXZONE blog", "url": SITE + "/blog/", "description": desc, "publisher": ORG,
        "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": p["url"],
                      "datePublished": p["date"]} for p in posts]})
    used = [c for c in CATEGORIES if any(p["category"] == c for p in posts)]
    chips = "".join('\n        <button type="button" class="blog-tab" data-cat="%s" aria-pressed="false">%s</button>' % (slugify(c), esc(c)) for c in used)
    cards = "".join(row(p, r) for p in posts)
    # Filters only once there is something to filter: six posts and at least
    # two categories. Three posts behind three tabs reads as an empty blog.
    tabs = ""
    if len(posts) >= 6 and len(used) >= 2:
        tabs = ('    <div class="blog-tabs" role="group" aria-label="Filter posts">\n'
                '      <button type="button" class="blog-tab" data-cat="" aria-pressed="true">All</button>%s\n'
                '    </div>\n') % chips
    return (head(r, title, desc, SITE + "/blog/", "website") + data + pixel(r) + "</head>\n\n" + topbar(r) + """
  <main class="page-shell blog-index">
    <header class="blog-mast">
      <picture class="blog-mast__photo">
        <source type="image/webp" srcset="../assets/gym-720.webp 720w, ../assets/gym-960.webp 960w, ../assets/gym-1440.webp 1440w" sizes="(max-width: 700px) 100vw, 760px">
        <img src="../assets/gym-960.jpg" srcset="../assets/gym-720.jpg 720w, ../assets/gym-960.jpg 960w, ../assets/gym-1440.jpg 1440w" sizes="(max-width: 700px) 100vw, 760px"
             width="1440" height="720" fetchpriority="high" decoding="async"
             alt="A Garmin watch running ROXZONE on an athlete's wrist at a HYROX event: Run 2, 1000 m, Sled Push next">
      </picture>
      <div class="blog-mast__text">
        <h1 class="blog-mast__title">Blog</h1>
        <p class="blog-mast__lede">Setting up your Garmin, racing to a plan and pacing your first HYROX race.</p>
      </div>
    </header>
    <div class="blog-body">
      <h2 class="blog-body__label">Latest articles</h2>
{tabs}      <div class="blog-list">
{cards}      </div>
{cta}    </div>
  </main>
  <script>
    // Category filter: no reload, nothing stored.
    (function () {{
      var chips = document.querySelectorAll(".blog-tab");
      var cards = document.querySelectorAll(".blog-list .blog-row");
      chips.forEach(function (chip) {{
        chip.addEventListener("click", function () {{
          var cat = chip.getAttribute("data-cat");
          chips.forEach(function (c) {{ c.setAttribute("aria-pressed", c === chip ? "true" : "false"); }});
          cards.forEach(function (card) {{ card.hidden = !!cat && card.getAttribute("data-cat") !== cat; }});
        }});
      }});
    }})();
  </script>
""".format(tabs=tabs, cards=cards, cta=closing(None, r)) + footer(r))


def feed(posts):
    newest = max(p["updated"] for p in posts)
    entries = "".join("""  <entry>
    <title>{t}</title>
    <link href="{u}"/>
    <id>{u}</id>
    <published>{d}T08:00:00Z</published>
    <updated>{m}T08:00:00Z</updated>
    <summary>{s}</summary>
  </entry>
""".format(t=esc(p["title"]), u=p["url"], d=p["date"], m=p["updated"], s=esc(p["description"])) for p in posts)
    return """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ROXZONE blog</title>
  <subtitle>HYROX on your Garmin</subtitle>
  <link href="{site}/blog/feed.xml" rel="self"/>
  <link href="{site}/blog/"/>
  <id>{site}/blog/</id>
  <updated>{n}T08:00:00Z</updated>
  <author><name>ROXZONE</name></author>
{e}</feed>
""".format(site=SITE, n=newest, e=entries)


def sitemap(posts):
    path = os.path.join(ROOT, "sitemap.xml")
    s = open(path, encoding="utf-8").read()
    rows = ["  <!-- blog:start (tools/blog_build.py writes this block) -->",
            "  <url>\n    <loc>%s/blog/</loc>\n    <lastmod>%s</lastmod>\n  </url>" % (SITE, max(p["updated"] for p in posts))]
    for p in posts:
        rows.append("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n  </url>" % (p["url"], p["updated"]))
    rows.append("  <!-- blog:end -->")
    block = "\n".join(rows)
    if "<!-- blog:start" in s:
        s = re.sub(r"  <!-- blog:start.*?<!-- blog:end -->", lambda m: block, s, flags=re.S)
    else:
        s = s.replace("</urlset>", block + "\n</urlset>")
    open(path, "w", encoding="utf-8").write(s)


def home_strip(posts):
    path = os.path.join(ROOT, "index.html")
    s = open(path, encoding="utf-8").read()
    cards = "".join(card(p, "./") for p in posts[:3])
    block = """    <!-- blog-strip:start (tools/blog_build.py writes this block) -->
    <section class="home-blog" aria-labelledby="home-blog-title">
      <div class="home-blog__head">
        <h2 id="home-blog-title" class="home-blog__title">From the blog</h2>
        <a class="home-blog__all" href="./blog/">All articles<span aria-hidden="true"> &rarr;</span></a>
      </div>
      <div class="blog-grid">
%s      </div>
    </section>
    <!-- blog-strip:end -->""" % cards
    if "<!-- blog-strip:start" not in s:
        sys.exit("index.html: blog strip markers missing")
    s = re.sub(r"    <!-- blog-strip:start.*?<!-- blog-strip:end -->", lambda m: block, s, flags=re.S)
    open(path, "w", encoding="utf-8").write(s)


def write(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def main():
    posts = read_posts()
    slugs = {p["slug"] for p in posts}
    for p in posts:
        for s in p["related"]:
            if s not in slugs:
                print("warning: %s: related post %s does not exist yet, left out" % (p["slug"], s))
        write("blog/%s/index.html" % p["slug"], post_page(p, posts))
    write("blog/index.html", index_page(posts))
    write("blog/feed.xml", feed(posts))
    sitemap(posts)
    home_strip(posts)
    print("built %d posts: %s" % (len(posts), ", ".join(p["slug"] for p in posts)))


if __name__ == "__main__":
    main()
