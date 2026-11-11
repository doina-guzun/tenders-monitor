import argparse, json, re, sys, time, unicodedata, html as htmlmod
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Chisinau")
UA = {"User-Agent": "tenders-monitor/1.0"}

CPV_A = "79950000 79951000 79952000 79952100 79953000 55120000 79340000 79341000 79341400 79342000 79342200 72413000 72212200 80500000 80510000 79400000 79410000 79411000 79800000 79810000".split()
CPV_B = "79954000 79956000 79530000 79540000 79961000 79416000 79416100 79416200 79413000 79341100 79341200 79342100 79822500 79970000 92111200 22462000 39294100 79632000 79633000 80520000 80521000 80522000 80530000 80532000 80533000 80570000 80420000".split()
CPV_C = "79900000 79000000 92300000 92000000 55520000 55300000 55110000 60140000 60170000 63510000 80000000 80400000 79310000".split()
DIRECT = set(CPV_A) | set(CPV_B)


KW_GROUPS = {
    "evenimente": [r"\bconferin", r"\bconferen", r"\bконференц", r"\bforum", r"\bфорум",
                   r"\bgala\b", r"\bgale\b", r"\bgalei\b", r"\bгала\b",
                   r"\bdelegati", r"\bdelegation", r"\bделегац", r"\bceremon", r"\bцеремон",
                   r"\beveniment", r"\bevent", r"\bмероприят", r"\bsummit", r"\bсаммит",
                   r"\bcongres", r"\bконгресс", r"\bsimpozi", r"\bsymposi", r"\bсимпозиум",
                   r"\bseminar", r"\bсеминар", r"\bworkshop", r"\bateliere?\b", r"\batelierul",
                   r"\bmasa rotunda", r"\bmese rotunde", r"\bround table", r"\bкругл\w* стол",
                   r"\bteam.?building", r"\bfestival", r"\bфестивал", r"\bexpozit", r"\bexhibition",
                   r"\bвыставк", r"\btarg(ul|uri|urile|ului)?\b", r"\bярмарк", r"\bconcert", r"\bконцерт", r"\blansare",
                   r"\blaunch", r"\bvizit\w* de studiu", r"\bstudy (visit|tour)", r"\bознакомительн",
                   r"\blogistic", r"\bлогистик", r"\bcoffee.?break", r"\bpauz\w* de cafea",
                   r"\bintalnir", r"\bmeeting", r"\bвстреч"],
    "ospitalitate": [r"\bcatering", r"\bкейтеринг", r"\bcazare", r"\baccommodation", r"\bпроживан",
                     r"\bразмещени", r"\bhotel", r"\bотел", r"\bгостиниц", r"\bbilet\w* de avion",
                     r"\bavia", r"\bflight", r"\bair ?tickets?", r"\bавиабилет", r"\btravel",
                     r"\bturism", r"\bтуризм", r"\bvenue", r"\bsal\w* de conferint"],
    "comunicare": [r"\bcomunicare", r"\bcommunication", r"\bкоммуникац", r"\bcampani", r"\bcampaign",
                   r"\bкампани", r"\bpromov", r"\bpromot", r"\bпродвижен", r"\bpublicitat",
                   r"\badvertis", r"\bреклам", r"\bvizibilitat", r"\bvisibility", r"\bawareness",
                   r"\bsensibiliz", r"\bинформирован", r"\bsocial media", r"\bsmm\b",
                   r"\brelatii publice", r"\bpublic relations", r"\bpr\b", r"\bbranding",
                   r"\bidentitat\w* vizual", r"\bvisual identity", r"\bmarketing", r"\bмаркетинг"],
    "tipar": [r"\btipar", r"\btipograf", r"\bprint", r"\bпечат", r"\bполиграф", r"\bpromotional",
              r"\bpersonalizat", r"\bbanner", r"\broll.?up", r"\bsuvenir", r"\bsouvenir", r"\bсувенир",
              r"\bmerch", r"\bfoto\b", r"\bfotograf", r"\bphoto\b", r"\bphotograph", r"\bфото\b",
              r"\bфотограф", r"\bvideo", r"\bвидео", r"\bdesign grafic", r"\bgraphic design",
              r"\bграфическ\w* дизайн", r"\bpodcast"],
    "traduceri": [r"\btraduc", r"\btranslat", r"\bперевод", r"\binterpret", r"\bсинхронн"],
    "instruire": [r"\binstruir", r"\bformare", r"\bcurs", r"\btraining", r"\bобучен", r"\bтренинг",
                  r"\bfacilitat", r"\bфасилитат", r"\bcapacity building", r"\bconsolidarea capacit",
                  r"\bmentor", r"\bментор"],
}
KW_ALL = [p for ps in KW_GROUPS.values() for p in ps]
KW_STRONG = [r"\bconferin", r"\bconferen", r"\bконференц", r"\bforum", r"\bфорум", r"\bgala\b", r"\bgale\b",
    r"\bgalei\b", r"\bгала\b", r"\bceremon", r"\bцеремон", r"\bsummit", r"\bсаммит", r"\bcongres", r"\bконгресс",
    r"\bsimpozi", r"\bsymposi", r"\bсимпозиум", r"\bfestival", r"\bфестивал", r"\bteam.?building",
    r"\bmasa rotunda", r"\bmese rotunde", r"\bround table", r"\bкругл\w* стол", r"\bcatering", r"\bкейтеринг",
    r"\bcazare", r"\baccommodation", r"\bevent (management|planning|organi[sz])", r"\bevent manager",
    r"\borganizar\w* (a )?(unui |unor )?evenimente", r"\borganizar\w* (a )?evenimentului", r"\bservicii de tipar",
    r"\btiparire", r"\bprinting services", r"\binterpretariat", r"\binterpretare sincron", r"\bservicii de traducere",
    r"\btranslation services", r"\bbilet\w* de avion", r"\bstudy (visit|tour)", r"\bvizit\w* de studiu",
    r"\bexpozit", r"\bexhibition"]


def strip_diacritics(s):
    s = (s or "").lower()

    out = []
    for ch in unicodedata.normalize("NFD", s):
        if unicodedata.category(ch) == "Mn":
            continue
        out.append(ch)
    s = unicodedata.normalize("NFC", "".join(out))
    return s.replace("ş", "s").replace("ţ", "t")


def kw_hit(text, patterns):
    t = strip_diacritics(text)
    for p in patterns:
        m = re.search(p, t)
        if m:
            return m.group(0)
    return None


def cpv8(code):
    return re.sub(r"\D", "", code or "")[:8]


def get_json(url, tries=3):
    err = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            err = e
            time.sleep(3)
    raise err


def get_text(url, tries=3):
    err = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except Exception as e:
            err = e
            if getattr(e, "code", None) in (401, 403, 404):
                break
            time.sleep(3)
    raise err


def to_local(iso):
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.astimezone(TZ).strftime("%d.%m.%Y %H:%M")


def classify(codes, text, title=""):
    seen = []
    for c, d in codes:
        c8 = cpv8(c)
        if c8 and c8 not in [x[0] for x in seen]:
            seen.append((c8, c, d))
    for c8, c, d in seen:
        if c8 in DIRECT:
            return c, d, "CPV " + ("A" if c8 in CPV_A else "B")
    for c8, c, d in seen:
        if c8 in CPV_C:
            hit = kw_hit(text, KW_ALL)
            if hit:
                return c, d, f"CPV C + cuvânt cheie „{hit}”"
    hit = kw_hit(title, KW_ALL)
    if hit:
        c, d = (seen[0][1], seen[0][2]) if seen else ("", "")
        return c, d, f"cuvânt cheie în titlu „{hit}” (CPV în afara listelor)"
    return None


def ocds_extract(rec):
    r = rec["releases"][0]
    t = r.get("tender", {}) or {}
    codes = []
    if t.get("classification"):
        codes.append((t["classification"].get("id"), t["classification"].get("description")))
    for it in t.get("items", []) or []:
        cl = it.get("classification") or {}
        codes.append((cl.get("id"), cl.get("description")))
    texts = [r.get("title"), r.get("description"), t.get("title"), t.get("description"),
             (r.get("planning", {}).get("budget", {}) or {}).get("project")]
    for lot in t.get("lots", []) or []:
        texts += [lot.get("title"), lot.get("description")]
    for it in t.get("items", []) or []:
        texts.append(it.get("description"))
    text = " | ".join(x for x in texts if x)
    title = (t.get("title") or r.get("title") or (r.get("planning", {}).get("budget", {}) or {}).get("project") or "").strip()
    pub = (t.get("enquiryPeriod") or {}).get("startDate") or (t.get("tenderPeriod") or {}).get("startDate")
    val = (t.get("value") or {})
    amount = val.get("amount")
    cur = val.get("currency")
    if amount is None:
        b = (r.get("planning", {}).get("budget", {}) or {}).get("amount") or {}
        amount, cur = b.get("amount"), b.get("currency")
    buyer = (t.get("procuringEntity") or {}).get("name")
    if not buyer:
        for p in r.get("parties", []) or []:
            if "buyer" in (p.get("roles") or []):
                buyer = p.get("name"); break
    return dict(ocid=r.get("ocid"), tag=(r.get("tag") or [""])[0], method=t.get("procurementMethodDetails"),
                status=t.get("status"), codes=codes, text=text, title=title, pub=pub,
                amount=amount, currency=cur, buyer=buyer or "",
                deadline=(t.get("tenderPeriod") or {}).get("endDate"))


def mtender(win_start_utc, win_end_utc, now_utc):
    off = win_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    ocids = {}
    pages = 0
    while True:
        d = get_json(f"https://public.mtender.gov.md/tenders/?offset={off}")
        pages += 1
        data = d.get("data", [])
        for x in data:
            ocids[x["ocid"]] = x["date"]
        if not data or d.get("offset") == off or len(data) < 100 or pages > 500:
            break
        off = d["offset"]

    def fetch(o):
        try:
            return o, get_json(f"http://public.eprocurement.systems/ocds/tenders/{o}")
        except Exception as e:
            return o, {"_error": str(e)}

    with ThreadPoolExecutor(12) as ex:
        recs = dict(ex.map(fetch, list(ocids)))
    out, errors = {}, [o for o, v in recs.items() if "_error" in v]
    for o, v in recs.items():
        if "_error" in v:
            continue
        try:
            e = ocds_extract(v)
        except Exception:
            errors.append(o); continue
        if not e["pub"]:
            continue
        pub = datetime.fromisoformat(e["pub"].replace("Z", "+00:00"))
        if win_start_utc <= pub < win_end_utc:
            out[o] = e
    return out, dict(listed=len(ocids), fetch_errors=len(errors), published_in_window=len(out))


RO_MONTHS = {"ian": 1, "feb": 2, "mar": 3, "apr": 4, "mai": 5, "iun": 6, "iul": 7, "aug": 8,
             "sep": 9, "sept": 9, "oct": 10, "noi": 11, "nov": 11, "dec": 12}


def parse_ro_date(s):
    m = re.search(r"(\d{1,2})\s+([a-zăâî]+)\.?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})", s.lower())
    if not m:
        return None
    mon = RO_MONTHS.get(m.group(2)[:4]) or RO_MONTHS.get(m.group(2)[:3])
    if not mon:
        return None
    return datetime(int(m.group(3)), mon, int(m.group(1)), int(m.group(4)), int(m.group(5)), tzinfo=TZ)


def achizitii(win_start_loc, win_end_loc):
    found, page = [], 1
    while page <= 400:
        h = get_text(f"https://achizitii.md/ro/public/tender/list?page={page}")
        items = h.split('class="tender__list__item"')[1:]
        if not items:
            break
        oldest = None
        for it in items:
            m = re.search(r'href="/ro/public/tender/(\d+)/"', it)
            pm = re.search(r"Data publicării</div>\s*<div[^>]*>.*?<span>([^<]+)</span>", it, re.S)
            if not (m and pm):
                continue
            pd = parse_ro_date(pm.group(1))
            if not pd:
                continue
            oldest = pd if oldest is None or pd < oldest else oldest
            if win_start_loc <= pd < win_end_loc:
                found.append((m.group(1), pd))
        if oldest is not None and oldest < win_start_loc:
            break
        page += 1

    def det(tid):
        try:
            h = get_text(f"https://achizitii.md/ro/public/tender/{tid}/")
            oc = re.findall(r"ocds-b3wdp1-MD-\d+", h)
            return tid, (oc[0] if oc else None)
        except Exception:
            return tid, None

    with ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(det, [f[0] for f in found]))
    return res, dict(pages=page, published_in_window=len(found),
                     without_ocid=sum(1 for v in res.values() if not v))


def civic(win_start_loc, win_end_loc):
    def clean(s):
        return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

    found, start, in_window = [], 0, 0
    while start <= 600:
        url = f"https://civic.md/anunturi/achizitii.html?limitstart={start}"
        cards = []
        for attempt in range(3):
            req = urllib.request.Request(url, headers=UA)
            resp = urllib.request.urlopen(req, timeout=60)
            if f"limitstart={start}" not in resp.geturl():
                raise RuntimeError(f"civic.md a redirecționat pagina {start} la {resp.geturl()}")
            h = resp.read().decode("utf-8", "replace")
            cards = h.split('<article class="civiccontent-blog-card"')[1:]
            if cards:
                break
            time.sleep(5)
        if not cards:
            raise RuntimeError(f"civic.md: pagina {start} nu are anunțuri")
        oldest = None
        for c in cards:
            tm = re.search(r'civiccontent-blog-title">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', c, re.S)
            dm = re.search(r'civiccontent-blog-meta">.*?(\d{1,2})/(\d{1,2})/(\d{4})', c, re.S)
            if not (tm and dm):
                continue
            d = datetime(int(dm.group(3)), int(dm.group(2)), int(dm.group(1)), tzinfo=TZ)
            oldest = d if oldest is None or d < oldest else oldest
            if not (win_start_loc <= d < win_end_loc):
                continue
            in_window += 1
            href = tm.group(1).split("?")[0]
            title = clean(tm.group(2))
            im = re.search(r'civiccontent-blog-intro">(.*?)</div>', c, re.S)
            intro = clean(im.group(1)) if im else ""
            om = re.search(r'civiccontent-blog-badge-tag"[^>]*title="([^"]+)"', c)
            body = ""
            if True:
              try:
                dh = get_text("https://civic.md" + href)
                a = dh.find('class="desc-article"')
                b = dh.find('class="civic-google-content"', a)
                if a >= 0:
                    seg = dh[a:b if b > a else a + 60000]
                    seg = re.sub(r"<script.*?</script>", " ", seg, flags=re.S)
                    body = clean(seg)
              except Exception:
                body = ""
            hit = kw_hit(title + " | " + intro, KW_ALL) or kw_hit(body, KW_STRONG)
            if hit:
                num = re.search(r"/(\d+)-", href)
                found.append(dict(id="civic-" + (num.group(1) if num else href), title=title, pub=d,
                                  link="https://civic.md" + href, kw=hit, body=body[:20000],
                                  org=htmlmod.unescape(om.group(1)) if om else ""))
        if oldest is not None and oldest < win_start_loc:
            break
        start += 20
    return found, in_window


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="dfrom", required=True)
    ap.add_argument("--to", dest="dto", required=True)
    ap.add_argument("--existing", default=None)
    ap.add_argument("--next-id", type=int, default=1)
    ap.add_argument("--out", default="result.json")
    a = ap.parse_args()

    ws = datetime.fromisoformat(a.dfrom).replace(tzinfo=TZ)
    we = datetime.fromisoformat(a.dto).replace(tzinfo=TZ) + timedelta(days=1)
    ws_u, we_u = ws.astimezone(timezone.utc), we.astimezone(timezone.utc)
    now = datetime.now(TZ)
    existing = set(json.load(open(a.existing))) if a.existing else set()
    errors, stats = {}, {}

    try:
        mt, stats["mtender"] = mtender(ws_u, we_u, now.astimezone(timezone.utc))
    except Exception as e:
        mt, errors["mtender"] = {}, str(e)

    via_ach = set()
    try:
        ach, stats["achizitii"] = achizitii(ws, we)
        missing = [o for o in ach.values() if o and o not in mt]
        for o in missing:
            try:
                e = ocds_extract(get_json(f"http://public.eprocurement.systems/ocds/tenders/{o}"))
                mt[o] = e
                via_ach.add(o)
            except Exception:
                pass
        stats["achizitii"]["missing_from_mtender_list"] = len(missing)
    except Exception as e:
        errors["achizitii"] = str(e)

    rows, matched = [], []
    for o, e in mt.items():
        if e["method"] == "directAward" or e["tag"].startswith("planning"):
            continue
        if e["status"] in ("cancelled", "unsuccessful"):
            continue
        c = classify(e["codes"], e["text"], e["title"])
        if not c:
            continue
        matched.append((e, c))

    try:
        civ, civ_n = civic(ws, we)
        stats["civic"] = dict(published_in_window=civ_n, matched=len(civ))
    except Exception as ex:
        civ, errors["civic"] = [], str(ex)

    civ_reasons = {}
    year = now.year
    n = a.next_id
    today = now.strftime("%d.%m.%Y")
    for e, (code, desc, why) in sorted(matched, key=lambda x: x[0]["pub"] or ""):
        if e["ocid"] in existing:
            continue
        amount = e["amount"]
        if amount is not None and e["currency"] and e["currency"] != "MDL":
            amount = f"{amount} {e['currency']}"
        rows.append([f"TND-{year}-{n:04d}", e["ocid"], today, to_local(e["pub"])[:10],
                     "MTender (via achizitii.md)" if e["ocid"] in via_ach else "MTender",
                     e["title"], e["buyer"], code, desc or "", amount if amount is not None else "",
                     to_local(e["deadline"]), f"https://mtender.gov.md/tenders/{e['ocid']}",
                     "Pending", ""])
        existing.add(e["ocid"]); n += 1
    for c in sorted(civ, key=lambda x: x["pub"]):
        if c["id"] in existing:
            continue
        rows.append([f"TND-{year}-{n:04d}", c["id"], today, c["pub"].strftime("%d.%m.%Y"), "civic.md",
                     c["title"], c["org"], "", "", "", "", c["link"], "Pending", ""])
        existing.add(c["id"]); n += 1
        civ_reasons[c["id"]] = f"civic.md, cuvânt cheie „{c['kw']}”"

    civic_texts = {c["id"]: c.get("body", "") for c in civ if c["id"] in {r[1] for r in rows}}
    json.dump(dict(rows=rows, stats=stats, errors=errors, civic_texts=civic_texts,
                   reasons={**{r[1]: next((w for e, (cc, dd, w) in matched if e["ocid"] == r[1]), "civic.md") for r in rows}, **civ_reasons}),
              open(a.out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(dict(new_rows=len(rows), stats=stats, errors=errors), ensure_ascii=False))


if __name__ == "__main__":
    main()
