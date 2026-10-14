"""
Metin tabanlı hizalama: düzenlenmiş videonun kelimelerini orijinal kelimelerle eşler,
insanın tuttuğu/sildiği bölgeleri çıkarır ve otomatik EDL ile kıyaslar.
python text_compare.py orig_groq.json edited_groq.json edl_auto_v1.json orig16k.wav out_dir
"""
import json, sys, re, wave, difflib
import numpy as np

orig_p, edit_p, edl_p, wav_p, out_dir = sys.argv[1:6]


def norm(w):
    w = w.replace("İ", "i").replace("I", "ı").lower()
    return re.sub(r"[^\wçğıöşü]", "", w)


def load_words(p):
    d = json.load(open(p, encoding="utf-8"))
    ws = [(float(w["start"]), float(w["end"]), w["word"].strip()) for w in d.get("words", []) if w["word"].strip()]
    return ws, d


Ow, Od = load_words(orig_p)
Ew, Ed = load_words(edit_p)
On = [norm(w[2]) for w in Ow]
En = [norm(w[2]) for w in Ew]
print(f"Orijinal kelime={len(Ow)}  Düzenlenmiş kelime={len(Ew)}")

# RMS (10 ms) – konuşma enerjisi
with wave.open(wav_p, "rb") as wv:
    x = np.frombuffer(wv.readframes(wv.getnframes()), np.int16).astype(np.float32) / 32768
HOP = 160
nfr = len(x) // HOP
rms = 10 * np.log10((x[: nfr * HOP].reshape(nfr, HOP) ** 2).mean(1) + 1e-12)
floor = np.percentile(rms, 10)
speech = rms > floor + 12
dur = len(x) / 16000
print(f"Süre={dur:.1f}s gürültü tabanı={floor:.1f}dB")


def speech_sec(a, b):
    return float(speech[int(a * 100):int(b * 100)].sum()) / 100


# 1) Kelime hizalama
sm = difflib.SequenceMatcher(None, On, En, autojunk=False)
pairs = []
for blk in sm.get_matching_blocks():
    for k in range(blk.size):
        pairs.append((blk.a + k, blk.b + k))
print(f"Eşleşen kelime çifti={len(pairs)} ({len(pairs)/max(1,len(Ew))*100:.1f}% düzenlenmiş kelimelerin)")

# 2) Hız faktörü tahmini
ratios = []
for (j1, i1), (j2, i2) in zip(pairs, pairs[1:]):
    if j2 == j1 + 1 and i2 == i1 + 1:
        do = Ow[j2][0] - Ow[j1][0]
        de = Ew[i2][0] - Ew[i1][0]
        if de > 0.15 and do > 0.15:
            ratios.append(do / de)
speed = float(np.median(ratios)) if ratios else 1.0
print(f"Hız faktörü (orig/edited) medyan={speed:.3f}  (1.0 = hız değişikliği yok)")

# 3) Sabit-delta koşuları (kesintisiz tutulmuş bölümler)
runs = []
for j, i in pairs:
    delta = Ow[j][0] - Ew[i][0] * speed
    if runs and abs(delta - runs[-1]["delta"]) < 0.6 and j > runs[-1]["j1"] and i > runs[-1]["i1"]:
        r = runs[-1]
        r["j1"], r["i1"] = j, i
        r["n"] += 1
        r["deltas"].append(delta)
        r["delta"] = float(np.median(r["deltas"][-10:]))
    else:
        runs.append({"j0": j, "j1": j, "i0": i, "i1": i, "n": 1, "delta": delta, "deltas": [delta]})
# tek kelimelik şüpheli koşuları komşusuna kat
runs = [r for r in runs if r["n"] >= 2] or runs
print(f"Kesintisiz tutulmuş bölüm (koşu) sayısı={len(runs)}")

# 4) Otomatik EDL
edl = json.load(open(edl_p, encoding="utf-8-sig"))
cuts = sorted([(c["start"], c["end"], c.get("reason", ""), c.get("command")) for c in edl["cuts"]])


def merge(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


auto_iv = merge([(a, b) for a, b, _, _ in cuts])
auto_ret = merge([(a, b) for a, b, r, _ in cuts if "retake" in r])


def cut_cover(a, b, iv=auto_iv):
    t = 0.0
    for c, d in iv:
        if d <= a:
            continue
        if c >= b:
            break
        t += min(b, d) - max(a, c)
    return t


def word_removed_by_auto(j):
    s, e, _ = Ow[j]
    return cut_cover(s, e) / max(0.01, e - s) >= 0.5


def word_clipped_by_auto(j):
    s, e, _ = Ow[j]
    c = cut_cover(s, e)
    return 0.05 < c / max(0.01, e - s) < 0.5


# 5) İnsan kararları (kelime bazında)
kept_orig = set()
for r in runs:
    for j in range(r["j0"], r["j1"] + 1):
        kept_orig.add(j)
# Koşu içindeki eşleşmeyen kelimeler ASR farkı sayılır → tutulmuş kabul
removed_orig = [j for j in range(len(Ow)) if j not in kept_orig]

# 6) İnsan kesim bölgeleri (koşular arası)
human_cuts = []
for r1, r2 in zip(runs, runs[1:]):
    a_word = Ow[r1["j1"]]
    b_word = Ow[r2["j0"]]
    rem = list(range(r1["j1"] + 1, r2["j0"]))
    o_gap = b_word[0] - a_word[1]
    e_gap = Ew[r2["i0"]][0] - Ew[r1["i1"]][1]  # insanın kesim noktasında bıraktığı boşluk
    rem_text = " ".join(Ow[j][2] for j in rem)
    sp = speech_sec(a_word[1], b_word[0])
    human_cuts.append({
        "orig_start": round(a_word[1], 2), "orig_end": round(b_word[0], 2),
        "orig_gap": round(o_gap, 2), "edited_gap_left": round(e_gap, 2),
        "removed_words": len(rem), "removed_text": rem_text,
        "speech_sec_in_gap": round(sp, 2),
        "before": " ".join(w[2] for w in Ow[max(0, r1["j1"] - 7): r1["j1"] + 1]),
        "after": " ".join(w[2] for w in Ow[r2["j0"]: r2["j0"] + 8]),
        "auto_cover": round(cut_cover(a_word[1], b_word[0]) / max(0.01, o_gap), 2) if o_gap > 0 else None,
        "auto_retake_cover": round(cut_cover(a_word[1], b_word[0], auto_ret) / max(0.01, o_gap), 2) if o_gap > 0 else None,
    })

# Baş ve son
lead_removed = runs[0]["j0"]
tail_removed = len(Ow) - 1 - runs[-1]["j1"]

# 7) Koşu içi duraklamalar: insan ne kadar boşluk bırakmış?
def pauses_in_run_edited(r):
    out = []
    for i in range(r["i0"], r["i1"]):
        g = Ew[i + 1][0] - Ew[i][1]
        if g > 0:
            out.append((g, i))
    return out


def pauses_orig_for_run(r):
    out = []
    for j in range(r["j0"], r["j1"]):
        g = Ow[j + 1][0] - Ow[j][1]
        if g > 0:
            out.append(g)
    return out


# İnsan çıktısındaki tüm kelime arası boşluklar
human_out_gaps = [Ew[i + 1][0] - Ew[i][1] for i in range(len(Ew) - 1)]

# Otomatik çıktıdaki kelime arası boşluklar (kesimler uygulandıktan sonra)
auto_kept_words = [j for j in range(len(Ow)) if not word_removed_by_auto(j)]
auto_out_gaps = []
for j1, j2 in zip(auto_kept_words, auto_kept_words[1:]):
    a, b = Ow[j1][1], Ow[j2][0]
    if b > a:
        auto_out_gaps.append((b - a) - cut_cover(a, b))
    else:
        auto_out_gaps.append(0.0)

# Orijinal kelime arası boşluklar
orig_gaps = [Ow[j + 1][0] - Ow[j][1] for j in range(len(Ow) - 1)]


def pct(v, ps=(10, 25, 50, 75, 90, 95, 99)):
    v = np.array([x for x in v])
    return {str(p): round(float(np.percentile(v, p)), 3) for p in ps} if len(v) else {}


# İnsan: orijinaldeki boşluk -> çıktıda kalan boşluk eşlemesi (sessizlik kısaltma eğrisi)
gap_map = []
for r in runs:
    for j in range(r["j0"], r["j1"]):
        if j + 1 > r["j1"]:
            break
        og = Ow[j + 1][0] - Ow[j][1]
        # karşılık gelen düzenlenmiş kelimeler
        pass
pair_map = {j: i for j, i in pairs}
for j in range(len(Ow) - 1):
    if j in pair_map and (j + 1) in pair_map and pair_map[j + 1] == pair_map[j] + 1:
        og = Ow[j + 1][0] - Ow[j][1]
        eg = Ew[pair_map[j + 1]][0] - Ew[pair_map[j]][1]
        gap_map.append((og, eg))
# Ayrıca kesim noktaları (koşu sınırları)
for hc in human_cuts:
    gap_map.append((hc["orig_gap"], hc["edited_gap_left"]))

bins = [(0, 0.2), (0.2, 0.4), (0.4, 0.7), (0.7, 1.0), (1.0, 1.5), (1.5, 2.5), (2.5, 5), (5, 1e9)]
curve = []
for lo, hi in bins:
    sel = [(o, e) for o, e in gap_map if lo <= o < hi]
    if sel:
        es = np.array([e for _, e in sel])
        curve.append({"orig_gap": f"{lo}-{hi if hi < 1e8 else 'inf'}", "n": len(sel),
                      "kept_median": round(float(np.median(es)), 3),
                      "kept_p25": round(float(np.percentile(es, 25)), 3),
                      "kept_p75": round(float(np.percentile(es, 75)), 3),
                      "ratio_median": round(float(np.median(es / np.maximum(0.01, np.array([o for o, _ in sel])))), 3)})

# Otomatik için aynı eğri
auto_gap_map = []
for j1, j2 in zip(auto_kept_words, auto_kept_words[1:]):
    if j2 == j1 + 1:
        a, b = Ow[j1][1], Ow[j2][0]
        og = max(0.0, b - a)
        auto_gap_map.append((og, og - cut_cover(a, b) if b > a else 0.0))
auto_curve = []
for lo, hi in bins:
    sel = [(o, e) for o, e in auto_gap_map if lo <= o < hi]
    if sel:
        es = np.array([e for _, e in sel])
        auto_curve.append({"orig_gap": f"{lo}-{hi if hi < 1e8 else 'inf'}", "n": len(sel),
                           "kept_median": round(float(np.median(es)), 3),
                           "kept_p25": round(float(np.percentile(es, 25)), 3),
                           "kept_p75": round(float(np.percentile(es, 75)), 3)})

# 8) Kelime düzeyinde karşılaştırma
n_rm_h = len(removed_orig)
rm_h_set = set(removed_orig)
auto_rm = set(j for j in range(len(Ow)) if word_removed_by_auto(j))
clipped = [j for j in range(len(Ow)) if j in kept_orig and word_clipped_by_auto(j)]
tp = len(rm_h_set & auto_rm)
fp = len(auto_rm - rm_h_set)     # insan tuttu, oto sildi (kelime kaybı)
fn = len(rm_h_set - auto_rm)     # insan sildi, oto tuttu (kaçan retake)

# 9) Otomatik retake kesimlerinin isabeti
auto_ret_items = []
for a, b, r, cmd in cuts:
    if "retake" not in r:
        continue
    ws = [j for j in range(len(Ow)) if Ow[j][0] < b and Ow[j][1] > a]
    hum = [j for j in ws if j in rm_h_set]
    auto_ret_items.append({"start": a, "end": b, "words": len(ws), "human_removed_words": len(hum),
                           "precision": round(len(hum) / max(1, len(ws)), 2),
                           "text": " ".join(Ow[j][2] for j in ws), "reason": r})

# Oto'nun yanlışlıkla sildiği (insanın tuttuğu) kelime öbekleri
fp_runs = []
cur = []
for j in sorted(auto_rm - rm_h_set):
    if cur and j == cur[-1] + 1:
        cur.append(j)
    else:
        if cur:
            fp_runs.append(cur)
        cur = [j]
if cur:
    fp_runs.append(cur)
fp_items = []
for run in fp_runs:
    s, e = Ow[run[0]][0], Ow[run[-1]][1]
    reasons = sorted(set(r.split(" ")[0] for a, b, r, _ in cuts if a < e and b > s))
    fp_items.append({"start": round(s, 2), "end": round(e, 2), "n": len(run), "text": " ".join(Ow[j][2] for j in run), "by": reasons})

# İnsan kesimlerindeki "transkripte girmemiş konuşma" (Whisper'ın yuttuğu tekrarlar)
hidden_speech = [hc for hc in human_cuts if hc["removed_words"] == 0 and hc["speech_sec_in_gap"] >= 0.5]

summary = {
    "orig_words": len(Ow), "edited_words": len(Ew), "matched_pairs": len(pairs),
    "speed_factor": round(speed, 3),
    "runs": len(runs), "human_cut_points": len(human_cuts),
    "lead_removed_words": lead_removed, "tail_removed_words": tail_removed,
    "human_removed_words": n_rm_h,
    "auto_removed_words": len(auto_rm),
    "agree_removed_words": tp, "auto_false_removed_words": fp, "auto_missed_removed_words": fn,
    "auto_clipped_kept_words": len(clipped),
    "human_cuts_with_words": sum(1 for h in human_cuts if h["removed_words"] > 0),
    "human_cuts_pause_only": sum(1 for h in human_cuts if h["removed_words"] == 0),
    "human_cuts_hidden_speech": len(hidden_speech),
    "orig_word_gaps": pct(orig_gaps),
    "human_output_word_gaps": pct(human_out_gaps),
    "auto_output_word_gaps": pct(auto_out_gaps),
    "human_gap_left_at_cut": pct([h["edited_gap_left"] for h in human_cuts]),
    "auto_retake_count": len(auto_ret_items),
    "auto_retake_precision_mean": round(float(np.mean([x["precision"] for x in auto_ret_items])), 3) if auto_ret_items else None,
    "auto_retake_good(>=0.6)": sum(1 for x in auto_ret_items if x["precision"] >= 0.6),
    "auto_retake_bad(<0.3)": sum(1 for x in auto_ret_items if x["precision"] < 0.3),
    "human_curve": curve, "auto_curve": auto_curve,
    "human_removed_sec_est": round(dur - Ed.get("duration", 0) * speed, 1),
}
json.dump({"summary": summary, "human_cuts": human_cuts, "auto_retakes": auto_ret_items, "auto_false_removed": fp_items,
           "clipped_words": [{"t": round(Ow[j][0], 2), "w": Ow[j][2]} for j in clipped]},
          open(f"{out_dir}/text_compare.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
