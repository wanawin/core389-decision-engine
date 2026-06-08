#!/usr/bin/env python3
"""
Core389 Lab App v1 — built from Core025 v182 workflow philosophy.
Separate family engine. Does not touch Core025 production files.

Status: LAB / NOT PRODUCTION DEFAULT
Family: 3389 / 3889 / 3899
Support files: upload-only. Candidate overlay is OFF by default.
"""
from __future__ import annotations
import io, re, json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
import streamlit as st

BUILD_MARKER = "BUILD: CORE389_LAB_APP_V1_2026-06-05_UPLOAD_ONLY_SUPPORT_OVERLAY_OFF"
FAMILY = "Core389"
MEMBERS = ["3389", "3889", "3899"]
DEFAULT_AUDIT_INTERVAL_DAYS = 90
DEFAULT_NEW_WIN_THRESHOLD = 25

st.set_page_config(page_title="Core389 Lab App v1", layout="wide")
st.title("Core389 Lab — 3389 / 3889 / 3899")
st.caption(BUILD_MARKER)
st.warning("LAB ONLY: Core389 is not production-ready. Overlay is OFF by default. Truth/Separator support is upload-only; generated files do not self-integrate.")

# -----------------------------
# IO helpers
# -----------------------------
def _bytes(obj) -> bytes:
    if obj is None: return b""
    if isinstance(obj, bytes): return obj
    if isinstance(obj, bytearray): return bytes(obj)
    if hasattr(obj, "getvalue"):
        v = obj.getvalue(); return v if isinstance(v, bytes) else str(v).encode("utf-8")
    if hasattr(obj, "read"):
        try: obj.seek(0)
        except Exception: pass
        v = obj.read(); return v if isinstance(v, bytes) else str(v).encode("utf-8")
    p = Path(str(obj))
    if p.exists(): return p.read_bytes()
    return str(obj).encode("utf-8")

def _name(obj, fallback="uploaded.txt") -> str:
    try: return str(getattr(obj, "name", fallback)).lower()
    except Exception: return fallback.lower()

def load_table(obj) -> pd.DataFrame:
    if obj is None: return pd.DataFrame()
    raw = _bytes(obj)
    if not raw: return pd.DataFrame()
    nm = _name(obj)
    if nm.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))
    text = raw.decode("utf-8", errors="replace")
    # Try comma, tab, pipe, whitespace-ish.
    for sep in [",", "\t", "|"]:
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
            if df.shape[1] >= 3: return df
        except Exception: pass
    try:
        return pd.read_csv(io.StringIO(text), sep=None, engine="python")
    except Exception:
        return pd.DataFrame()

def parse_history(obj) -> pd.DataFrame:
    raw = _bytes(obj)
    if not raw: return pd.DataFrame()
    text = raw.decode("utf-8", errors="replace")
    rows=[]
    for line in text.splitlines():
        line=line.strip()
        if not line: continue
        parts=line.split("\t")
        if len(parts) < 4: continue
        date_s,state,game,draw = parts[0], parts[1], parts[2], parts[3]
        digs=re.findall(r"\d", str(draw))
        if len(digs)!=4: continue
        result="".join(digs)
        dt=pd.to_datetime(date_s, errors="coerce")
        if pd.isna(dt): continue
        stream=f"{state} | {game}"
        rows.append({"Date":date_s,"DateParsed":dt.normalize(),"State":state,"Game":game,"StreamKey":stream,"Draw":draw,"Result":result})
    if not rows: return pd.DataFrame()
    df=pd.DataFrame(rows).drop_duplicates(["DateParsed","StreamKey","Result"]).sort_values(["StreamKey","DateParsed"]).reset_index(drop=True)
    return df

def member_from_result(result: str) -> str:
    s="".join(re.findall(r"\d", str(result)))
    if len(s)!=4: return ""
    key="".join(sorted(s))
    mapping={"3389":"3389", "3889":"3889", "3899":"3899"}
    return mapping.get(key, "")

# -----------------------------
# Feature builder matching Phase 2 fields
# -----------------------------
def features_from_seed(seed: str) -> Dict[str, object]:
    ds=[int(x) for x in re.findall(r"\d", str(seed))[-4:]]
    if len(ds)!=4: ds=[0,0,0,0]
    out={}
    for d in range(10):
        c=ds.count(d); out[f"cnt{d}"]=c; out[f"has{d}"]=1 if c>0 else 0
    ss=sum(ds); out["seed_sum"]=ss
    if ss<=9: sb="sum_0_9"
    elif ss<=13: sb="sum_10_13"
    elif ss<=17: sb="sum_14_17"
    elif ss<=21: sb="sum_18_21"
    else: sb="sum_22_plus"
    out["sum_bucket"]=sb
    spread=max(ds)-min(ds); out["spread"]=spread
    out["spread_bucket"]="spread_0_2" if spread<=2 else "spread_3_4" if spread<=4 else "spread_5_6" if spread<=6 else "spread_7_plus"
    out["parity_pattern"]="".join("E" if x%2==0 else "O" for x in ds)
    out["highlow_pattern"]="".join("H" if x>=5 else "L" for x in ds)
    counts=sorted([ds.count(x) for x in set(ds)], reverse=True)
    out["max_rep"]=max(counts); out["unique"]=len(set(ds)); out["pair"]=1 if 2 in counts else 0
    out["consec_links"]=sum(1 for a,b in zip(ds,ds[1:]) if abs(a-b)==1)
    out["even"]=sum(1 for x in ds if x%2==0); out["odd"]=4-out["even"]
    out["low"]=sum(1 for x in ds if x<5); out["high"]=4-out["low"]
    if counts==[4]: structure="AAAA"
    elif counts==[3,1]: structure="AAAB"
    elif counts==[2,2]: structure="AABB"
    elif counts==[2,1,1]: structure="AABC"
    else: structure="ABCD"
    out["structure"]=structure
    out["first_digit"]=ds[0]; out["last_digit"]=ds[-1]
    out["seed_sum_lastdigit"]=ss%10
    root=ss
    while root>=10: root=sum(int(c) for c in str(root))
    out["seed_root_sum"]=root
    out["has_3_8_9"]=1 if all(d in ds for d in [3,8,9]) else 0
    out["lacks_3_8_9"]=1-out["has_3_8_9"]
    out["has_8_9"]=1 if (8 in ds and 9 in ds) else 0
    out["lacks_8_9"]=1-out["has_8_9"]
    return out

def rule_matches(trait_stack: str, feats: Dict[str, object]) -> bool:
    if not isinstance(trait_stack, str) or not trait_stack.strip(): return False
    for cond in [c.strip() for c in trait_stack.split("&&")]:
        if not cond: continue
        if "=" not in cond: return False
        k,v=[x.strip() for x in cond.split("=",1)]
        if k not in feats: return False
        fv=feats[k]
        if isinstance(fv, (int,float,np.integer,np.floating)):
            try:
                if float(fv) != float(v): return False
            except Exception:
                if str(fv) != v: return False
        else:
            if str(fv) != v: return False
    return True

# -----------------------------
# Prediction engine
# -----------------------------
def normalize_separator(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    out=df.copy()
    lower={c.lower().strip():c for c in out.columns}
    rename={}
    for canonical, aliases in {
        "RuleID":["ruleid","rule_id","id"],
        "pair":["pair"],
        "trait_stack":["trait_stack","traitstack","rule","trait"],
        "support":["support"],
        "winner_member":["winner_member","winner","winningmember","oldwinnermember"],
        "winner_rate":["winner_rate","rate","win_rate"],
    }.items():
        for a in aliases:
            if a in lower: rename[lower[a]]=canonical; break
    out=out.rename(columns=rename)
    required=["trait_stack","winner_member"]
    missing=[c for c in required if c not in out.columns]
    if missing: return pd.DataFrame()
    out["winner_member"]=out["winner_member"].astype(str).str.extract(r"(3389|3889|3899)", expand=False).fillna("")
    if "support" not in out.columns: out["support"]=1
    if "winner_rate" not in out.columns: out["winner_rate"]=0.5
    out["support"]=pd.to_numeric(out["support"], errors="coerce").fillna(1)
    out["winner_rate"]=pd.to_numeric(out["winner_rate"], errors="coerce").fillna(0.5)
    out=out[out["winner_member"].isin(MEMBERS)].copy()
    return out

def score_seed(feats: Dict[str, object], sep: pd.DataFrame, max_rules=80) -> Tuple[Dict[str,float], List[str]]:
    scores={m:0.0 for m in MEMBERS}; hits=[]
    if sep is None or sep.empty: return scores,hits
    for _,r in sep.iterrows():
        ts=str(r.get("trait_stack", ""))
        if rule_matches(ts, feats):
            m=r.get("winner_member","")
            if m in scores:
                # moderate weight; avoid one giant support rule overpowering all others
                w=float(r.get("winner_rate",0.5))*np.log1p(float(r.get("support",1)))
                scores[m]+=w
                if len(hits)<max_rules:
                    hits.append(f"{r.get('RuleID','RULE')}->{m}:{ts}")
    return scores,hits

def ranked_members(scores: Dict[str,float]) -> List[str]:
    return sorted(MEMBERS, key=lambda m:(scores.get(m,0.0), m), reverse=True)

def apply_overlay(row: Dict[str,object], overlay: pd.DataFrame) -> Tuple[Dict[str,object], List[str]]:
    """Experimental overlay OFF by default. Applies first matching locked action only per group."""
    notes=[]
    if overlay is None or overlay.empty: return row, notes
    feats=row["Features"]
    ranked=list(row["RankedMembers"])
    top1=ranked[0] if ranked else ""
    # downrank 3389: swap top1/top2 if top1 3389 and rule matches
    for _,r in overlay.sort_values("LockedOrder").iterrows():
        action=str(r.get("LockedAction", ""))
        ts=str(r.get("TraitStack", ""))
        if action=="DOWNRANK_3389_SWAP_TOP1_TOP2" and top1=="3389" and rule_matches(ts, feats):
            if len(ranked)>1:
                ranked[0], ranked[1]=ranked[1], ranked[0]
                notes.append(f"EXP_OVERLAY_DOWNRANK_3389:{r.get('RuleID','')}")
                break
    # promotions from top2
    for target, action_name in [("3889","PROMOTE_3889_FROM_TOP2"),("3899","PROMOTE_3899_FROM_TOP2")]:
        if len(ranked)>1 and ranked[1]==target:
            for _,r in overlay[overlay.get("LockedAction","").astype(str).eq(action_name)].sort_values("LockedOrder").iterrows():
                if rule_matches(str(r.get("TraitStack","")), feats):
                    ranked[0], ranked[1]=ranked[1], ranked[0]
                    notes.append(f"EXP_OVERLAY_PROMOTE_{target}:{r.get('RuleID','')}")
                    break
        if notes and "PROMOTE" in notes[-1]: break
    row["RankedMembers"] = ranked
    row["OverlayNotes"] = "; ".join(notes)
    return row, notes

def build_daily_playlist(hist: pd.DataFrame, sep: pd.DataFrame, overlay: pd.DataFrame=None, use_overlay=False) -> pd.DataFrame:
    if hist is None or hist.empty or sep is None or sep.empty: return pd.DataFrame()
    latest=hist["DateParsed"].max().normalize()
    pred_date=latest+pd.Timedelta(days=1)
    # Use most recent draw per StreamKey, so Monday streams without Sunday game use Saturday or prior automatically.
    last=hist.sort_values(["StreamKey","DateParsed"]).groupby("StreamKey", as_index=False).tail(1).copy()
    rows=[]
    for _,r in last.iterrows():
        feats=features_from_seed(r["Result"])
        scores,hits=score_seed(feats, sep)
        ranked=ranked_members(scores)
        row={
            "PredictionDate": pred_date.date().isoformat(),
            "SeedDateUsed": pd.to_datetime(r["DateParsed"]).date().isoformat(),
            "SeedAgeDays": int((pred_date-r["DateParsed"]).days),
            "State": r["State"], "Game": r["Game"], "StreamKey": r["StreamKey"],
            "SeedResult": r["Result"],
            "Features": feats,
            "Score_3389": scores["3389"], "Score_3889": scores["3889"], "Score_3899": scores["3899"],
            "MatchedRuleCount": len(hits), "SupportReason": " | ".join(hits[:12]),
            "RankedMembers": ranked, "OverlayNotes":""
        }
        if use_overlay and overlay is not None and not overlay.empty:
            row,_=apply_overlay(row, overlay)
            ranked=row["RankedMembers"]
        row.update({"Top1": ranked[0], "Top2": ranked[1], "Top3": ranked[2]})
        # family fit: normalized magnitude + gap
        vals=[row["Score_3389"],row["Score_3889"],row["Score_3899"]]
        row["Core389RawScore"]=max(vals)
        row["Core389ScoreGap"]=sorted(vals, reverse=True)[0]-sorted(vals, reverse=True)[1]
        row["Core389FitScore"]=(row["Core389RawScore"]+0.35*row["Core389ScoreGap"]+0.1*row["MatchedRuleCount"])
        rows.append(row)
    out=pd.DataFrame(rows)
    if out.empty: return out
    out["Core389FitRank"]=out["Core389FitScore"].rank(method="first", ascending=False).astype(int)
    out=out.sort_values("Core389FitRank").reset_index(drop=True)
    out["RecommendedPlay"] = out["Top1"]
    out["PlayCount"] = 1
    out["RowCost_25c"] = "$0.25"
    out["RunningPlayTotal"] = out["PlayCount"].cumsum()
    out["RunningCost_25c"] = (out["RunningPlayTotal"]*0.25).map(lambda x:f"${x:,.2f}")
    front=["Core389FitRank","PredictionDate","SeedDateUsed","SeedAgeDays","StreamKey","State","Game","SeedResult","RecommendedPlay","Top1","Top2","Top3","Core389FitScore","Core389RawScore","Core389ScoreGap","Score_3389","Score_3889","Score_3899","MatchedRuleCount","OverlayNotes","PlayCount","RunningPlayTotal","RunningCost_25c","SupportReason"]
    return out[front+[c for c in out.columns if c not in front and c!="Features"]]

def member_mix(df: pd.DataFrame, col="Top1") -> Dict[str,int]:
    if df is None or df.empty or col not in df.columns: return {m:0 for m in MEMBERS}
    return {m:int((df[col].astype(str)==m).sum()) for m in MEMBERS}

def collapse_flag(mix: Dict[str,int]) -> str:
    total=sum(mix.values())
    if total==0: return "EMPTY"
    if any(v==0 for v in mix.values()): return "WARN_MEMBER_ZERO"
    if max(mix.values())/total>0.80: return "WARN_MEMBER_OVER_80_PERCENT"
    return "PASS"

# -----------------------------
# Sidebar uploads
# -----------------------------
st.sidebar.header("Core389 Uploads")
history_file=st.sidebar.file_uploader("Full history file", type=["txt","csv","tsv"], key="core389_history")
truth_file=st.sidebar.file_uploader("Truth389 file optional", type=["csv","txt","tsv","xlsx"], key="core389_truth")
sep_file=st.sidebar.file_uploader("Separator389 file", type=["csv","txt","tsv","xlsx"], key="core389_sep")
overlay_file=st.sidebar.file_uploader("Experimental overlay rulepack optional", type=["csv","txt","tsv","xlsx"], key="core389_overlay")
use_overlay=st.sidebar.checkbox("Use experimental Phase 7 overlay — OFF by default", value=False)

st.sidebar.header("Audit Clock")
last_audit_date=st.sidebar.date_input("Last Core389 audit date", value=pd.to_datetime("2026-06-07").date())
audit_days=st.sidebar.number_input("Audit interval days", min_value=30, max_value=365, value=90, step=15)
new_win_threshold=st.sidebar.number_input("Early audit threshold: new Core389 wins", min_value=5, max_value=100, value=25, step=5)

hist=parse_history(history_file) if history_file else pd.DataFrame()
truth=load_table(truth_file) if truth_file else pd.DataFrame()
sep=normalize_separator(load_table(sep_file)) if sep_file else pd.DataFrame()
overlay=load_table(overlay_file) if overlay_file else pd.DataFrame()

# -----------------------------
# Status panels
# -----------------------------
st.subheader("Core389 Support Status")
cols=st.columns(4)
cols[0].metric("History Rows", len(hist) if isinstance(hist,pd.DataFrame) else 0)
cols[1].metric("Truth389 Rows", len(truth) if isinstance(truth,pd.DataFrame) else 0)
cols[2].metric("Separator Rules", len(sep) if isinstance(sep,pd.DataFrame) else 0)
cols[3].metric("Overlay Rules", len(overlay) if isinstance(overlay,pd.DataFrame) else 0)

if not hist.empty:
    total_wins=int(hist["Result"].map(member_from_result).isin(MEMBERS).sum())
    latest=hist["DateParsed"].max().date().isoformat()
    st.info(f"Loaded history through {latest}. Raw Core389 wins in history: {total_wins}. Monday/no-draw streams use each stream's most recent available SeedDateUsed.")

# audit status
try:
    today=pd.Timestamp.today().normalize().date()
    days_since=(pd.Timestamp(today)-pd.Timestamp(last_audit_date)).days
    next_due=(pd.Timestamp(last_audit_date)+pd.Timedelta(days=int(audit_days))).date()
    st.subheader("Audit Clock")
    c=st.columns(4)
    c[0].metric("Last Audit", str(last_audit_date))
    c[1].metric("Days Since Audit", days_since)
    c[2].metric("Next Audit Due", str(next_due))
    c[3].metric("Status", "DUE" if days_since>=audit_days else "OK")
except Exception:
    pass

if sep.empty:
    st.warning("Upload Separator389 to generate a daily playlist. Use the Phase 2 separator candidate file for lab testing.")
if hist.empty:
    st.warning("Upload full history to generate a daily playlist.")

if not hist.empty and not sep.empty:
    st.divider()
    st.subheader("Core389 Daily Lab Playlist")
    playlist=build_daily_playlist(hist, sep, overlay, use_overlay=use_overlay)
    mix=member_mix(playlist,"Top1")
    flag=collapse_flag(mix)
    mcols=st.columns(4)
    mcols[0].metric("Top1 3389", mix["3389"])
    mcols[1].metric("Top1 3889", mix["3889"])
    mcols[2].metric("Top1 3899", mix["3899"])
    mcols[3].metric("Collapse Guard", flag)
    if flag != "PASS": st.error(f"Collapse/member-balance warning: {flag}")
    else: st.success("Member mix collapse guard passed.")
    if use_overlay:
        st.warning("Experimental overlay is ON. This is lab-only and not production default.")
    else:
        st.info("Experimental overlay is OFF. Baseline separator-only lab playlist shown.")
    st.dataframe(playlist, use_container_width=True, hide_index=True, height=750)
    csv=playlist.to_csv(index=False).encode("utf-8")
    txt=playlist.to_csv(index=False, sep="\t").encode("utf-8")
    st.download_button("Download Core389 Daily Lab Playlist CSV", csv, file_name="core389_daily_lab_playlist.csv", mime="text/csv")
    st.download_button("Download Core389 Daily Lab Playlist TXT", txt, file_name="core389_daily_lab_playlist.txt", mime="text/plain")
    printable=playlist[["Core389FitRank","StreamKey","SeedDateUsed","SeedResult","RecommendedPlay","Top1","Top2","Top3","Core389FitScore","PlayCount","RunningCost_25c"]].copy()
    st.subheader("Printable Cleaned Lab Playlist")
    st.dataframe(printable, use_container_width=True, hide_index=True, height=550)
    st.download_button("Download Printable Core389 Lab Playlist CSV", printable.to_csv(index=False).encode("utf-8"), file_name="core389_printable_cleaned_lab_playlist.csv", mime="text/csv")
    st.download_button("Download Printable Core389 Lab Playlist TXT", printable.to_csv(index=False, sep="\t").encode("utf-8"), file_name="core389_printable_cleaned_lab_playlist.txt", mime="text/plain")

st.divider()
st.subheader("Core389 Notes")
st.markdown("""
- Core389 lab status: **not production-ready**.
- Use sidebar-uploaded Truth/Separator only. Generated files must be intentionally downloaded and re-uploaded.
- Phase 7 overlay remains OFF by default because it improved Top1 and balance but did not improve Top1+Top2 capture.
- `SeedDateUsed` is shown explicitly; streams without a draw on the immediately prior calendar day use their own most recent available seed.
""")
