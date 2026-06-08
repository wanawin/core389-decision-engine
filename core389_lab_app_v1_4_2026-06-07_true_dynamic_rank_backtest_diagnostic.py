#!/usr/bin/env python3
"""
Core389 Lab App v1.4 — true dynamic ranking + backtest diagnostic, built from Core025 v182 workflow philosophy.
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

BUILD_MARKER = "BUILD: CORE389_LAB_APP_V1_4_2026-06-07_TRUE_DYNAMIC_RANK_BACKTEST_DIAGNOSTIC_RANK_DEPTH_RESCUE_AUDIT"
FAMILY = "Core389"
MEMBERS = ["3389", "3889", "3899"]
DEFAULT_AUDIT_INTERVAL_DAYS = 90
DEFAULT_NEW_WIN_THRESHOLD = 25

st.set_page_config(page_title="Core389 Lab App v1", layout="wide")
st.title("Core389 Lab — 3389 / 3889 / 3899")
st.caption(BUILD_MARKER)
st.warning("LAB ONLY: Core389 is not production-ready. Overlay/reduction/rescue parity scaffolds are OFF by default. Truth/Separator support is upload-only; generated files do not self-integrate.")

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
        # IMPORTANT: the raw source draw field may contain add-ons after a comma,
        # e.g. "1-6-8-9, Fireball: 3", "9-8-8-5, Superball: 0",
        # or "6-3-8-8, Sum It Up: 25".
        # Only the base Pick-4 result before the first comma is the seed/result.
        # The previous parser counted add-on digits too, which silently dropped
        # Fireball/Wild Ball/Superball/Sum-It-Up streams and collapsed the playlist.
        base_draw=str(draw).split(",", 1)[0].strip()
        digs=re.findall(r"\d", base_draw)
        if len(digs)!=4: continue
        result="".join(digs)
        dt=pd.to_datetime(date_s, errors="coerce")
        if pd.isna(dt): continue
        stream=f"{state} | {game}"
        rows.append({"Date":date_s,"DateParsed":dt.normalize(),"State":state,"Game":game,"StreamKey":stream,"Draw":draw,"Result":result})
    if not rows: return pd.DataFrame()
    df=pd.DataFrame(rows).drop_duplicates(["DateParsed","StreamKey","Result"]).sort_values(["StreamKey","DateParsed"]).reset_index(drop=True)
    return df

def history_stream_diagnostics(hist: pd.DataFrame) -> Dict[str, object]:
    """Visible reconciliation counts for playlist completeness."""
    if hist is None or hist.empty:
        return {
            "history_rows_parsed": 0,
            "unique_streams_parsed": 0,
            "unique_states_parsed": 0,
            "unique_games_parsed": 0,
            "latest_history_date": "",
        }
    return {
        "history_rows_parsed": int(len(hist)),
        "unique_streams_parsed": int(hist["StreamKey"].nunique()),
        "unique_states_parsed": int(hist["State"].nunique()),
        "unique_games_parsed": int(hist["Game"].nunique()),
        "latest_history_date": pd.to_datetime(hist["DateParsed"]).max().date().isoformat(),
    }

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

    # Ranking support: keep these fields separate and visible.
    # StreamRank = rank by Core389 fit score.
    # PlaylistRank = final sorted playlist order.
    # SingleRow = literal one-based row in the full exported playlist.
    # RowPercentile = percentile position computed from SingleRow, not substituted from StreamRank.
    out["StreamRank"] = out["Core389FitRank"].astype(int)
    out["PlaylistRank"] = np.arange(1, len(out)+1, dtype=int)
    out["SingleRow"] = out["PlaylistRank"].astype(int)
    if len(out) <= 1:
        out["RowPercentile"] = 100.0
    else:
        out["RowPercentile"] = ((len(out) - out["SingleRow"]) / (len(out) - 1) * 100).round(2)

    out["RecommendedPlay"] = out["Top1"]
    out["PlayCount"] = 1
    out["RowCost_25c"] = "$0.25"
    out["RunningPlayTotal"] = out["PlayCount"].cumsum()
    out["RunningCost_25c"] = (out["RunningPlayTotal"]*0.25).map(lambda x:f"${x:,.2f}")
    front=["Core389FitRank","StreamRank","PlaylistRank","SingleRow","RowPercentile","PredictionDate","SeedDateUsed","SeedAgeDays","StreamKey","State","Game","SeedResult","RecommendedPlay","Top1","Top2","Top3","Core389FitScore","Core389RawScore","Core389ScoreGap","Score_3389","Score_3889","Score_3899","MatchedRuleCount","OverlayNotes","PlayCount","RunningPlayTotal","RunningCost_25c","SupportReason"]
    return out[front+[c for c in out.columns if c not in front and c!="Features"]]

# -----------------------------
# Core025-style ranking adapter for Core389
# -----------------------------
def _scale_high(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").astype(float)
    if s.notna().sum() == 0:
        return pd.Series(0.0, index=s.index)
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(0.5, index=s.index)
    return ((s - lo) / (hi - lo)).fillna(0.0)

def _scale_low(s: pd.Series) -> pd.Series:
    return 1.0 - _scale_high(s)

def _build_stream_history_stats(hist: pd.DataFrame) -> pd.DataFrame:
    """Actual-history stream production and due-pressure stats for the Core389 family."""
    if hist is None or hist.empty or "StreamKey" not in hist.columns:
        return pd.DataFrame()
    h = hist.copy()
    h["Core389MemberHit"] = h["Result"].map(member_from_result)
    h["IsCore389Win"] = h["Core389MemberHit"].isin(MEMBERS).astype(int)
    latest = pd.to_datetime(h["DateParsed"], errors="coerce").max()
    g = h.groupby("StreamKey", as_index=False).agg(
        StreamDrawRows=("Result", "size"),
        StreamCore389Wins=("IsCore389Win", "sum"),
        StreamFirstDate=("DateParsed", "min"),
        StreamLastDate=("DateParsed", "max"),
    )
    g["StreamCore389WinRate"] = np.where(g["StreamDrawRows"].gt(0), g["StreamCore389Wins"] / g["StreamDrawRows"], 0.0)
    last_win = (h[h["IsCore389Win"].eq(1)]
                .groupby("StreamKey", as_index=False)
                .agg(StreamLastCore389WinDate=("DateParsed", "max")))
    g = g.merge(last_win, on="StreamKey", how="left")
    g["StreamDaysSinceCore389Win"] = (pd.to_datetime(latest) - pd.to_datetime(g["StreamLastCore389WinDate"], errors="coerce")).dt.days
    g["StreamDaysSinceCore389Win"] = g["StreamDaysSinceCore389Win"].fillna(9999).astype(int)
    for m in MEMBERS:
        mm = (h[h["Core389MemberHit"].eq(m)]
              .groupby("StreamKey", as_index=False)
              .agg(**{f"StreamWins_{m}": ("Core389MemberHit", "size")}))
        g = g.merge(mm, on="StreamKey", how="left")
        g[f"StreamWins_{m}"] = pd.to_numeric(g.get(f"StreamWins_{m}", 0), errors="coerce").fillna(0).astype(int)
    return g

def add_core025_style_rank_fields_389(playlist: pd.DataFrame, hist: pd.DataFrame) -> pd.DataFrame:
    """
    Additive Core025-style ranking for Core389.
    Does not remove rows and does not replace baseline member scoring.
    It adds dynamic pressure, actual stream-production strength, due pressure,
    and a final hybrid rank for budget/order decisions.
    """
    if playlist is None or playlist.empty:
        return pd.DataFrame()
    out = playlist.copy()

    # Preserve old order explicitly, like Core025 v139 did.
    out["OldCore389FitRank"] = pd.to_numeric(out.get("Core389FitRank", pd.Series(range(1, len(out)+1), index=out.index)), errors="coerce").fillna(999).astype(int)
    out["OldStreamRank"] = pd.to_numeric(out.get("StreamRank", out["OldCore389FitRank"]), errors="coerce").fillna(999).astype(int)
    out["OldPlaylistRank"] = pd.to_numeric(out.get("PlaylistRank", pd.Series(range(1, len(out)+1), index=out.index)), errors="coerce").fillna(999).astype(int)

    score_cols = {m: f"Score_{m}" for m in MEMBERS}
    for m, c in score_cols.items():
        if c not in out.columns:
            out[c] = 0.0
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    # Member-selection diagnostics in 025 naming style.
    out["Top1_score"] = out.apply(lambda r: float(r.get(score_cols.get(str(r.get("Top1", "")), ""), 0.0)), axis=1)
    out["Top2_score"] = out.apply(lambda r: float(r.get(score_cols.get(str(r.get("Top2", "")), ""), 0.0)), axis=1)
    out["Top3_score"] = out.apply(lambda r: float(r.get(score_cols.get(str(r.get("Top3", "")), ""), 0.0)), axis=1)
    out["gap"] = out["Top1_score"] - out["Top2_score"]
    out["ratio"] = np.where(out["Top1_score"].abs().gt(0), out["Top2_score"] / out["Top1_score"].replace(0, np.nan), 0.0)
    out["ratio"] = pd.to_numeric(out["ratio"], errors="coerce").replace([np.inf, -np.inf], 0).fillna(0.0)
    out["Top2ToTop1Ratio"] = out["ratio"]
    out["Top23Pressure"] = out["Top2_score"] + out["Top3_score"]
    out["ModelConfidenceScore"] = out["Top1_score"]
    out["Margin"] = out["gap"]

    # 025-style dynamic score: vulnerable rows can move up when member pressure is close.
    out["DynamicScore_389_v12"] = (
        1.15 * _scale_low(out["Top1_score"])
        + 1.00 * _scale_low(out["gap"])
        + 0.85 * _scale_high(out["ratio"])
        + 0.70 * _scale_high(out["Top23Pressure"])
        + 0.35 * _scale_high(out["MatchedRuleCount"] if "MatchedRuleCount" in out.columns else pd.Series(0, index=out.index))
        + 0.25 * _scale_high(out["Core389RawScore"] if "Core389RawScore" in out.columns else out["Top1_score"])
    )
    out["DynamicRank_389_v12"] = out["DynamicScore_389_v12"].rank(method="first", ascending=False).astype(int)

    # Actual history stream-production layer: 389 equivalent of 025 SingleRow winner-production strength.
    stats = _build_stream_history_stats(hist)
    if not stats.empty:
        out = out.merge(stats, on="StreamKey", how="left")
    for c in ["StreamDrawRows", "StreamCore389Wins", "StreamCore389WinRate", "StreamDaysSinceCore389Win"] + [f"StreamWins_{m}" for m in MEMBERS]:
        if c not in out.columns:
            out[c] = 0
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)

    out["StreamHistoricalProductionRank_389_v12"] = (
        0.70 * _scale_high(out["StreamCore389Wins"])
        + 0.30 * _scale_high(out["StreamCore389WinRate"])
    ).rank(method="first", ascending=False).astype(int)
    out["DuePressureRank_389_v12"] = out["StreamDaysSinceCore389Win"].rank(method="first", ascending=False).astype(int)

    # Member balance support: tells us whether Top1 is historically supported on that stream.
    out["Top1StreamMemberWins_389_v12"] = out.apply(lambda r: int(r.get(f"StreamWins_{r.get('Top1','')}", 0) or 0), axis=1)
    out["Top1StreamMemberSupportRank_389_v12"] = out["Top1StreamMemberWins_389_v12"].rank(method="first", ascending=False).astype(int)

    # True hybrid rank patterned after Core025 v139:
    # dynamic daily pressure + actual historical stream production + due pressure.
    out["HybridRankScore_389_v12"] = (
        0.50 * out["DynamicRank_389_v12"]
        + 0.35 * out["StreamHistoricalProductionRank_389_v12"]
        + 0.15 * out["DuePressureRank_389_v12"]
    )
    out["HybridFinalRank_389_v12"] = out["HybridRankScore_389_v12"].rank(method="first", ascending=True).astype(int)
    out["HybridVsOldStreamRankDelta_389_v12"] = out["HybridFinalRank_389_v12"] - out["OldStreamRank"]
    try:
        collapsed = pd.to_numeric(out["HybridFinalRank_389_v12"], errors="coerce").reset_index(drop=True).equals(
            pd.to_numeric(out["OldStreamRank"], errors="coerce").reset_index(drop=True)
        )
    except Exception:
        collapsed = False
    out["HybridRankDiagnostic_389_v12"] = "WARNING_COLLAPSED_TO_OLD_STREAMRANK" if collapsed else "TRUE_HYBRID_025_STYLE"

    # Final Core025-style ordered playlist; rows are not removed.
    out = out.sort_values("HybridFinalRank_389_v12").reset_index(drop=True)
    out["DynamicOrder"] = np.arange(1, len(out)+1, dtype=int)
    out["RecommendedPlay"] = out["Top1"]
    out["ActualMembersToPlay"] = out["Top1"]
    out["ActualPlayCount"] = 1
    out["Action"] = "TOP1"
    out["RunningPlayTotal"] = out["ActualPlayCount"].cumsum()
    out["RunningCost_25c"] = (out["RunningPlayTotal"] * 0.25).map(lambda x: f"${x:,.2f}")

    front = [c for c in [
        "DynamicOrder", "HybridFinalRank_389_v12", "HybridRankScore_389_v12", "HybridRankDiagnostic_389_v12",
        "StreamKey", "State", "Game", "SeedDateUsed", "SeedResult",
        "OldPlaylistRank", "OldStreamRank", "OldCore389FitRank", "HybridVsOldStreamRankDelta_389_v12",
        "SingleRow", "RowPercentile", "DynamicRank_389_v12", "StreamHistoricalProductionRank_389_v12", "DuePressureRank_389_v12",
        "StreamCore389Wins", "StreamCore389WinRate", "StreamDaysSinceCore389Win",
        "Top1", "Top2", "Top3", "RecommendedPlay", "Action", "ActualMembersToPlay", "ActualPlayCount",
        "Top1_score", "Top2_score", "Top3_score", "gap", "ratio", "Top23Pressure",
        "Top1StreamMemberWins_389_v12", "Top1StreamMemberSupportRank_389_v12",
        "Score_3389", "Score_3889", "Score_3899", "MatchedRuleCount", "OverlayNotes",
        "RunningPlayTotal", "RunningCost_25c", "SupportReason"
    ] if c in out.columns]
    rest = [c for c in out.columns if c not in front]
    return out[front + rest]


def finalize_true_dynamic_playlist_389(hybrid_playlist: pd.DataFrame) -> pd.DataFrame:
    """
    v1.4 final ordering fix.
    v1.3 computed hybrid fields but still rendered/exported the raw Core389FitRank order.
    This function makes final PlaylistRank truly dynamic while preserving the raw order separately.

    Core389FitRank / RawFitRank_389_v14 = raw separator-fit order.
    SingleRow = raw full-universe row position, not final playlist order.
    StreamRank = dynamic pressure rank.
    PlaylistRank = final hybrid order.
    RowPercentile = percentile of SingleRow only.
    """
    if hybrid_playlist is None or not isinstance(hybrid_playlist, pd.DataFrame) or hybrid_playlist.empty:
        return pd.DataFrame()
    out = hybrid_playlist.copy()

    # Preserve raw rank/order first.
    raw = pd.to_numeric(out.get("Core389FitRank", out.get("OldCore389FitRank", pd.Series(range(1, len(out)+1), index=out.index))), errors="coerce")
    out["RawFitRank_389_v14"] = raw.fillna(raw.rank(method="first", ascending=True)).astype(int)
    out["Core389FitRank"] = out["RawFitRank_389_v14"]

    # Make SingleRow literal raw row position, not the final playlist order.
    out["SingleRow"] = out["RawFitRank_389_v14"].astype(int)
    if len(out) <= 1:
        out["RowPercentile"] = 100.0
    else:
        out["RowPercentile"] = ((len(out) - out["SingleRow"]) / (len(out) - 1) * 100).round(2)

    # StreamRank becomes the dynamic-pressure order, separate from SingleRow/raw fit.
    dyn_col = "DynamicRank_389_v12" if "DynamicRank_389_v12" in out.columns else None
    if dyn_col:
        out["StreamRank"] = pd.to_numeric(out[dyn_col], errors="coerce").fillna(999).astype(int)
    else:
        # Last resort only: derive a dynamic rank from pressure fields.
        pressure = (
            1.15 * _scale_low(pd.to_numeric(out.get("Top1_score", 0), errors="coerce"))
            + 1.00 * _scale_low(pd.to_numeric(out.get("gap", 0), errors="coerce"))
            + 0.85 * _scale_high(pd.to_numeric(out.get("ratio", 0), errors="coerce"))
        )
        out["StreamRank"] = pressure.rank(method="first", ascending=False).astype(int)

    # Final playlist rank is the hybrid order.
    hyb_col = "HybridFinalRank_389_v12" if "HybridFinalRank_389_v12" in out.columns else None
    if hyb_col:
        out["PlaylistRank"] = pd.to_numeric(out[hyb_col], errors="coerce").fillna(999).astype(int)
    else:
        out["PlaylistRank"] = out["StreamRank"].rank(method="first", ascending=True).astype(int)

    out = out.sort_values(["PlaylistRank", "StreamRank", "RawFitRank_389_v14"], ascending=[True, True, True]).reset_index(drop=True)
    out["DynamicOrder_389_v14"] = np.arange(1, len(out)+1, dtype=int)
    out["PlaylistRank"] = out["DynamicOrder_389_v14"].astype(int)

    # Recompute running cost after final order and actual depth.
    if "ActualPlayCount" not in out.columns:
        out["ActualPlayCount"] = pd.to_numeric(out.get("PlayCount", 1), errors="coerce").fillna(1).astype(int)
    out["PlayCount"] = pd.to_numeric(out["ActualPlayCount"], errors="coerce").fillna(0).astype(int)
    out["RunningPlayTotal"] = out["PlayCount"].cumsum()
    out["RunningCost_25c"] = (out["RunningPlayTotal"] * 0.25).map(lambda x: f"${x:,.2f}")

    # Explicit diagnostic fields.
    out["RankSystem_389_v14"] = "TRUE_DYNAMIC_PLAYLISTRANK"
    out["PlaylistVsRawFitDelta_389_v14"] = pd.to_numeric(out["PlaylistRank"], errors="coerce") - pd.to_numeric(out["RawFitRank_389_v14"], errors="coerce")
    out["StreamVsSingleRowDelta_389_v14"] = pd.to_numeric(out["StreamRank"], errors="coerce") - pd.to_numeric(out["SingleRow"], errors="coerce")
    moved = int(pd.to_numeric(out["PlaylistVsRawFitDelta_389_v14"], errors="coerce").fillna(0).ne(0).sum())
    out["RankMovementRows_389_v14"] = moved

    front = [c for c in [
        "PlaylistRank", "DynamicOrder_389_v14", "StreamRank", "SingleRow", "RowPercentile", "RawFitRank_389_v14", "Core389FitRank",
        "RankSystem_389_v14", "RankMovementRows_389_v14", "PlaylistVsRawFitDelta_389_v14", "StreamVsSingleRowDelta_389_v14",
        "HybridFinalRank_389_v12", "HybridRankScore_389_v12", "DynamicRank_389_v12", "StreamHistoricalProductionRank_389_v12", "DuePressureRank_389_v12",
        "PredictionDate", "SeedDateUsed", "SeedAgeDays", "StreamKey", "State", "Game", "SeedResult",
        "RecommendedPlay", "Top1", "Top2", "Top3", "Action", "ActualMembersToPlay", "ActualPlayCount", "PlayCount", "RunningPlayTotal", "RunningCost_25c",
        "Core389FitScore", "Core389RawScore", "Core389ScoreGap", "Top1_score", "Top2_score", "Top3_score", "gap", "ratio",
        "Score_3389", "Score_3889", "Score_3899", "MatchedRuleCount", "OverlayNotes", "SupportReason"
    ] if c in out.columns]
    rest = [c for c in out.columns if c not in front]
    return out[front + rest]


def build_backtest_rank_diagnostic_389(final_playlist: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """
    v1.4 lightweight backtest/rank diagnostic.
    This does not pretend to be full walk-forward performance unless the uploaded truth contains dated per-event rows.
    It verifies whether the current final ranking table can locate truth winner streams and reports raw-vs-dynamic ranks.
    """
    if final_playlist is None or final_playlist.empty or truth is None or not isinstance(truth, pd.DataFrame) or truth.empty:
        return pd.DataFrame()
    if "StreamKey" not in final_playlist.columns:
        return pd.DataFrame()
    t = truth.copy()
    # Build StreamKey if truth has State/Game but not StreamKey.
    if "StreamKey" not in t.columns and {"State", "Game"}.issubset(t.columns):
        t["StreamKey"] = t["State"].astype(str) + " | " + t["Game"].astype(str)
    if "StreamKey" not in t.columns:
        return pd.DataFrame()

    member_col = next((c for c in ["TrueMember", "truth_member", "WinnerMember", "winner_member", "CapturedMember", "member", "Result", "Draw"] if c in t.columns), None)
    if member_col is None:
        t["TruthMember"] = ""
    else:
        t["TruthMember"] = t[member_col].map(member_from_result)
        # If member_from_result failed because the column already has 3389/3889/3899 labels.
        mask = ~t["TruthMember"].isin(MEMBERS)
        t.loc[mask, "TruthMember"] = t.loc[mask, member_col].astype(str).str.extract(r"(3389|3889|3899)", expand=False).fillna("")

    rank_cols = [c for c in [
        "StreamKey", "PlaylistRank", "StreamRank", "SingleRow", "RowPercentile", "RawFitRank_389_v14", "Core389FitRank",
        "Top1", "Top2", "Top3", "Action", "ActualMembersToPlay", "ActualPlayCount", "PlaylistVsRawFitDelta_389_v14"
    ] if c in final_playlist.columns]
    fp = final_playlist[rank_cols].drop_duplicates("StreamKey")
    joined = t.merge(fp, on="StreamKey", how="left", suffixes=("_Truth", ""))
    joined["WinnerStreamFoundInPlaylist"] = joined["PlaylistRank"].notna()
    joined["TruthMemberInTop1"] = joined["TruthMember"].astype(str).eq(joined.get("Top1", "").astype(str))
    joined["TruthMemberInTop2"] = joined.apply(lambda r: str(r.get("TruthMember", "")) in {str(r.get("Top1", "")), str(r.get("Top2", ""))}, axis=1)
    joined["TruthMemberInTop3"] = joined.apply(lambda r: str(r.get("TruthMember", "")) in {str(r.get("Top1", "")), str(r.get("Top2", "")), str(r.get("Top3", ""))}, axis=1)
    joined["BacktestDiagnostic_389_v14"] = "RANK_LOOKUP_ONLY_NOT_FULL_WALK_FORWARD"
    front = [c for c in [
        "Date", "DrawDate", "PredictionDate", "StreamKey", "TruthMember", "WinnerStreamFoundInPlaylist",
        "PlaylistRank", "RawFitRank_389_v14", "StreamRank", "SingleRow", "RowPercentile", "PlaylistVsRawFitDelta_389_v14",
        "Top1", "Top2", "Top3", "TruthMemberInTop1", "TruthMemberInTop2", "TruthMemberInTop3", "BacktestDiagnostic_389_v14"
    ] if c in joined.columns]
    rest = [c for c in joined.columns if c not in front]
    return joined[front + rest]




# -----------------------------
# Core025 parity scaffold: rank guards, depth/reduction/rescue, cadence, scoring
# -----------------------------
def _member_tokens_389(x) -> List[str]:
    found=[]
    for tok in re.findall(r"\d+", str(x)):
        z=tok.zfill(4)
        if z in MEMBERS and z not in found:
            found.append(z)
    return found

def _clean_member_389(x) -> str:
    toks=_member_tokens_389(x)
    return toks[0] if toks else ""

def normalize_parity_rulepack(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """
    Normalizes Core389-specific reduction/rescue rulepacks.
    Expected fields are intentionally close to Core025:
      RuleID/Step, Rule/TraitStack, ReductionAction or RescueAction, Enabled.
    No embedded 025 rules are used here.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    out=df.copy()
    lower={str(c).lower().strip():c for c in out.columns}
    rename={}
    aliases={
        "RuleID":["ruleid","rule_id","id","step"],
        "TraitStack":["traitstack","trait_stack","rule","trait","condition","conditions"],
        "ReductionAction":["reductionaction","reduction_action","action","depthaction"],
        "RescueAction":["rescueaction","rescue_action","action"],
        "Enabled":["enabled","active","use","is_enabled"],
        "LockedOrder":["lockedorder","order","priority","step"],
        "TargetMember":["targetmember","target_member","member","winner_member"],
    }
    for canonical, vals in aliases.items():
        for a in vals:
            if a in lower:
                rename[lower[a]]=canonical
                break
    out=out.rename(columns=rename)
    if "TraitStack" not in out.columns:
        return pd.DataFrame()
    if "RuleID" not in out.columns:
        out["RuleID"]=[f"{kind.upper()}_{i+1}" for i in range(len(out))]
    if "LockedOrder" not in out.columns:
        out["LockedOrder"]=range(1,len(out)+1)
    if "Enabled" not in out.columns:
        out["Enabled"]=True
    out["Enabled"]=out["Enabled"].astype(str).str.strip().str.lower().isin(["1","true","yes","y","on","enabled","active"])
    out["LockedOrder"]=pd.to_numeric(out["LockedOrder"], errors="coerce").fillna(999999).astype(int)
    if kind == "reduction" and "ReductionAction" not in out.columns:
        return pd.DataFrame()
    if kind == "rescue" and "RescueAction" not in out.columns:
        return pd.DataFrame()
    return out.sort_values(["Enabled","LockedOrder"], ascending=[False, True]).reset_index(drop=True)

def _row_match_context(row: pd.Series) -> Dict[str, object]:
    feats = {}
    # Seed features, both original names and Core025-ish aliases.
    seed = str(row.get("SeedResult", ""))
    feats.update(features_from_seed(seed))
    alias = {
        "sum_bucket":"seed_sum_bucket",
        "seed_sum":"seed_sum_exact",
        "seed_sum_lastdigit":"seed_sum_end",
        "parity_pattern":"seed_parity",
        "highlow_pattern":"seed_highlow",
        "structure":"seed_structure",
        "consec_links":"consec_links",
    }
    for src,dst in alias.items():
        if src in feats: feats[dst]=feats[src]
    # Visible row/rank/member context.
    for c in [
        "StreamKey","State","Game","Top1","Top2","Top3","Action","SingleRow","RowPercentile","StreamRank","PlaylistRank",
        "Core389FitRank","OldStreamRank","DynamicRank_389_v12","HybridFinalRank_389_v12","MatchedRuleCount",
        "StreamCore389Wins","StreamCore389WinRate","StreamDaysSinceCore389Win","Top1_score","Top2_score","Top3_score","gap","ratio"
    ]:
        if c in row.index:
            feats[c]=row.get(c)
    feats["top1_member"]=_clean_member_389(row.get("Top1", ""))
    feats["top2_member"]=_clean_member_389(row.get("Top2", ""))
    feats["top3_member"]=_clean_member_389(row.get("Top3", ""))
    ranked=[feats.get("top1_member",""), feats.get("top2_member",""), feats.get("top3_member","")]
    feats["top_order"]="_".join([m for m in ranked if m])
    try:
        sr=int(float(row.get("SingleRow")))
        feats["RowBucket10"] = int(((sr-1)//10)+1)
    except Exception:
        pass
    try:
        osr=int(float(row.get("OldStreamRank", row.get("StreamRank", 999))))
        feats["BRankBand5"] = f"BR_{((osr-1)//5)*5+1:02d}_{((osr-1)//5)*5+5:02d}"
        feats["BRankBand10"] = f"BR_{((osr-1)//10)*10+1:02d}_{((osr-1)//10)*10+10:02d}"
    except Exception:
        pass
    return feats

def _rule_matches_row(trait_stack: str, row: pd.Series) -> bool:
    return rule_matches(str(trait_stack), _row_match_context(row))

def _rank_row_separation_report(df: pd.DataFrame, context: str="playlist") -> Dict[str, object]:
    report={"context":context,"rows":int(len(df)) if isinstance(df,pd.DataFrame) else 0,"status":"OK","warnings":[]}
    if df is None or not isinstance(df,pd.DataFrame) or df.empty:
        report["status"]="EMPTY"; return report
    def ser(c):
        return pd.to_numeric(df[c], errors="coerce") if c in df.columns else None
    def sameish(a,b):
        if a is None or b is None: return False
        mask=a.notna() & b.notna()
        if int(mask.sum()) < 10: return False
        return bool((a[mask].astype(float).round(8)==b[mask].astype(float).round(8)).all())
    sr,rp,sg,pl = ser("StreamRank"), ser("RowPercentile"), ser("SingleRow"), ser("PlaylistRank")
    if sameish(sr,rp): report["warnings"].append("StreamRank equals RowPercentile across comparable rows.")
    if sameish(sr,sg): report["warnings"].append("StreamRank equals SingleRow across comparable rows.")
    if sameish(rp,sg): report["warnings"].append("RowPercentile equals SingleRow across comparable rows; verify derivation.")
    if sameish(pl,sr): report["warnings"].append("PlaylistRank equals StreamRank across comparable rows; verify final order.")
    if sameish(pl,sg): report["warnings"].append("PlaylistRank equals SingleRow across comparable rows; verify final order.")
    fatal=any("StreamRank equals RowPercentile" in w or "StreamRank equals SingleRow" in w for w in report["warnings"])
    report["status"]="RANK_ROW_COLLAPSE_DETECTED" if fatal else ("WARNINGS" if report["warnings"] else "OK")
    return report

def apply_depth_reduction_rescue_389(playlist: pd.DataFrame, reduction_rules: pd.DataFrame=None, rescue_rules: pd.DataFrame=None, use_reduction=False, use_rescue=False) -> pd.DataFrame:
    """
    Core025-style depth/action scaffold for Core389.
    Default is TOP1 only. Optional rulepacks can SET_DEPTH_0/1/2/3 or RAISE_TO_TOP1/2/3.
    Rules are never embedded from 025 and are OFF unless user enables and uploads Core389-specific rule files.
    """
    if playlist is None or playlist.empty:
        return pd.DataFrame()
    out=playlist.copy()
    for c in ["Top1","Top2","Top3"]:
        if c not in out.columns: out[c]=""
    out["BaseDepth_389_v13"]=1
    out["FinalDepth_389_v13"]=1
    out["DepthRuleNotes_389_v13"]="BASE_TOP1_ONLY"

    rr=normalize_parity_rulepack(reduction_rules, "reduction") if use_reduction else pd.DataFrame()
    if use_reduction and not rr.empty:
        for idx,row in out.iterrows():
            for _,r in rr[rr["Enabled"].eq(True)].iterrows():
                if _rule_matches_row(str(r.get("TraitStack","")), row):
                    action=str(r.get("ReductionAction","")).strip().upper()
                    new_depth=None
                    if action in {"SET_DEPTH_0","NO_PLAY","DEPTH_0"}: new_depth=0
                    elif action in {"SET_DEPTH_1","TOP1","DEPTH_1"}: new_depth=1
                    elif action in {"SET_DEPTH_2","TOP2","DEPTH_2"}: new_depth=2
                    elif action in {"SET_DEPTH_3","TOP3","DEPTH_3"}: new_depth=3
                    if new_depth is not None:
                        out.at[idx,"FinalDepth_389_v13"]=int(new_depth)
                        out.at[idx,"DepthRuleNotes_389_v13"]=f"REDUCTION:{r.get('RuleID','')}:{action}"
                        break

    rs=normalize_parity_rulepack(rescue_rules, "rescue") if use_rescue else pd.DataFrame()
    if use_rescue and not rs.empty:
        for idx,row in out.iterrows():
            cur=int(out.at[idx,"FinalDepth_389_v13"])
            for _,r in rs[rs["Enabled"].eq(True)].iterrows():
                if _rule_matches_row(str(r.get("TraitStack","")), out.loc[idx]):
                    action=str(r.get("RescueAction","")).strip().upper()
                    new_depth=None
                    if action in {"RAISE_TO_TOP1","SET_DEPTH_1","TOP1"}: new_depth=max(cur,1)
                    elif action in {"RAISE_TO_TOP2","SET_DEPTH_2","TOP2"}: new_depth=max(cur,2)
                    elif action in {"RAISE_TO_TOP3","SET_DEPTH_3","TOP3"}: new_depth=max(cur,3)
                    if new_depth is not None:
                        out.at[idx,"FinalDepth_389_v13"]=int(new_depth)
                        prev=str(out.at[idx,"DepthRuleNotes_389_v13"])
                        out.at[idx,"DepthRuleNotes_389_v13"]=(prev+"; " if prev else "")+f"RESCUE:{r.get('RuleID','')}:{action}"
                        break

    def members_for_depth(row):
        d=int(row.get("FinalDepth_389_v13",1) or 0)
        ranked=[]
        for c in ["Top1","Top2","Top3"]:
            m=_clean_member_389(row.get(c,""))
            if m and m not in ranked: ranked.append(m)
        return ranked[:max(0,min(3,d))]
    members=out.apply(members_for_depth, axis=1)
    out["ActualMembersToPlay"]=members.map(lambda xs:" + ".join(xs))
    out["ActualPlayCount"]=members.map(len).astype(int)
    out["Action"]=np.where(out["ActualPlayCount"].eq(0),"NO PLAY",np.where(out["ActualPlayCount"].eq(1),"TOP1",np.where(out["ActualPlayCount"].eq(2),"TOP2","TOP3")))
    out["RecommendedPlay"]=out["ActualMembersToPlay"]
    out["RowCost_25c"]=(out["ActualPlayCount"]*0.25).map(lambda x:f"${x:,.2f}")
    out["RunningPlayTotal"]=out["ActualPlayCount"].cumsum()
    out["RunningCost_25c"]=(out["RunningPlayTotal"]*0.25).map(lambda x:f"${x:,.2f}")
    return out

def build_stream_cadence_389(hist: pd.DataFrame) -> pd.DataFrame:
    if hist is None or hist.empty:
        return pd.DataFrame()
    h=hist.copy()
    h["Core389MemberHit"]=h["Result"].map(member_from_result)
    h=h[h["Core389MemberHit"].isin(MEMBERS)].copy()
    if h.empty: return pd.DataFrame()
    latest=pd.to_datetime(hist["DateParsed"], errors="coerce").max()
    g=h.groupby("StreamKey", as_index=False).agg(
        State=("State","last"), Game=("Game","last"), Core389Wins=("Core389MemberHit","size"),
        FirstCore389Win=("DateParsed","min"), LastCore389Win=("DateParsed","max")
    )
    g["CurrentGapAsOfHistoryEnd"]=(pd.to_datetime(latest)-pd.to_datetime(g["LastCore389Win"])).dt.days.astype(int)
    g["StreamCadenceRank_389_v13"]=g["CurrentGapAsOfHistoryEnd"].rank(method="first", ascending=False).astype(int)
    for c in ["FirstCore389Win","LastCore389Win"]:
        g[c]=pd.to_datetime(g[c]).dt.date.astype(str)
    return g.sort_values("StreamCadenceRank_389_v13")

def build_row_cadence_if_available_389(truth: pd.DataFrame) -> pd.DataFrame:
    """Row cadence requires a Core389 truth/backtest file that already contains SingleRow or RowPercentile."""
    if truth is None or truth.empty:
        return pd.DataFrame()
    row_col=next((c for c in ["SingleRow","RowPercentile","PlaylistRank","StreamRank"] if c in truth.columns), None)
    if row_col is None:
        return pd.DataFrame()
    out=truth.copy()
    out["_row"] = pd.to_numeric(out[row_col], errors="coerce")
    out=out[out["_row"].notna()].copy()
    if out.empty: return pd.DataFrame()
    g=out.groupby("_row", as_index=False).size().rename(columns={"_row":"SingleRowLike","size":"Core389TruthRows"})
    g["RowProductionRank_389_v13"]=g["Core389TruthRows"].rank(method="first", ascending=False).astype(int)
    return g.sort_values("RowProductionRank_389_v13")

def add_truth_operational_scoring_389(playlist: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """Additive current-day scoring if uploaded truth contains matching StreamKey/date/member fields."""
    if playlist is None or playlist.empty or truth is None or truth.empty:
        return playlist
    t=truth.copy()
    # best-effort normalization only; no fake truth.
    lower={str(c).lower().strip():c for c in t.columns}
    stream_col=next((lower[x] for x in ["streamkey","stream_key"] if x in lower), None)
    result_col=next((lower[x] for x in ["result","draw","winningnumber","winner"] if x in lower), None)
    member_col=next((lower[x] for x in ["truemember","true_member","winner_member","member"] if x in lower), None)
    if stream_col is None:
        return playlist
    if member_col is None and result_col is None:
        return playlist
    if member_col is None:
        t["TrueMember_389_v13"]=t[result_col].map(member_from_result)
    else:
        t["TrueMember_389_v13"]=t[member_col].map(_clean_member_389)
    t=t[t["TrueMember_389_v13"].isin(MEMBERS)].copy()
    if t.empty: return playlist
    # If multiple truth rows per stream exist, keep the latest row in file order as current best-effort.
    t=t.drop_duplicates(stream_col, keep="last")[[stream_col,"TrueMember_389_v13"]]
    out=playlist.merge(t, left_on="StreamKey", right_on=stream_col, how="left")
    played=out["ActualMembersToPlay"].astype(str)
    out["TruthEval_389_v13"]=np.where(out["TrueMember_389_v13"].isna(),"NO_TRUTH",
        np.where(out["ActualPlayCount"].eq(0),"NO_PLAY",
        np.where(out["Top1"].astype(str).eq(out["TrueMember_389_v13"].astype(str)),"TOP1_WIN",
        np.where(out.apply(lambda r: str(r.get("TrueMember_389_v13","")) in _member_tokens_389(r.get("ActualMembersToPlay","")), axis=1),"CAPTURED_NOT_TOP1","MISS"))))
    return out.drop(columns=[stream_col], errors="ignore")


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
reduction_file=st.sidebar.file_uploader("Core389 reduction/depth rulepack optional", type=["csv","txt","tsv","xlsx"], key="core389_reduction")
rescue_file=st.sidebar.file_uploader("Core389 rescue rulepack optional", type=["csv","txt","tsv","xlsx"], key="core389_rescue")
use_overlay=st.sidebar.checkbox("Use experimental Phase 7 overlay — OFF by default", value=False)
use_reduction=st.sidebar.checkbox("Use Core389 reduction/depth rulepack — OFF by default", value=False)
use_rescue=st.sidebar.checkbox("Use Core389 rescue rulepack — OFF by default", value=False)

st.sidebar.header("Audit Clock")
last_audit_date=st.sidebar.date_input("Last Core389 audit date", value=pd.to_datetime("2026-06-07").date())
audit_days=st.sidebar.number_input("Audit interval days", min_value=30, max_value=365, value=90, step=15)
new_win_threshold=st.sidebar.number_input("Early audit threshold: new Core389 wins", min_value=5, max_value=100, value=25, step=5)

hist=parse_history(history_file) if history_file else pd.DataFrame()
truth=load_table(truth_file) if truth_file else pd.DataFrame()
sep=normalize_separator(load_table(sep_file)) if sep_file else pd.DataFrame()
overlay=load_table(overlay_file) if overlay_file else pd.DataFrame()
reduction_rules=load_table(reduction_file) if reduction_file else pd.DataFrame()
rescue_rules=load_table(rescue_file) if rescue_file else pd.DataFrame()

# -----------------------------
# Status panels
# -----------------------------
st.subheader("Core389 Support Status")
diag=history_stream_diagnostics(hist)
cols=st.columns(4)
cols[0].metric("History Rows Parsed", diag["history_rows_parsed"])
cols[1].metric("Unique Streams Parsed", diag["unique_streams_parsed"])
cols[2].metric("Truth389 Rows", len(truth) if isinstance(truth,pd.DataFrame) else 0)
cols[3].metric("Separator Rules", len(sep) if isinstance(sep,pd.DataFrame) else 0)

cols2=st.columns(4)
cols2[0].metric("Unique States Parsed", diag["unique_states_parsed"])
cols2[1].metric("Unique Games Parsed", diag["unique_games_parsed"])
cols2[2].metric("Latest History Date", diag["latest_history_date"] or "—")
cols2[3].metric("Overlay / Depth / Rescue Rules", f"{len(overlay) if isinstance(overlay,pd.DataFrame) else 0} / {len(reduction_rules) if isinstance(reduction_rules,pd.DataFrame) else 0} / {len(rescue_rules) if isinstance(rescue_rules,pd.DataFrame) else 0}")

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
    raw_playlist=build_daily_playlist(hist, sep, overlay, use_overlay=use_overlay)
    hybrid_playlist=add_core025_style_rank_fields_389(raw_playlist, hist)
    hybrid_playlist=apply_depth_reduction_rescue_389(hybrid_playlist, reduction_rules, rescue_rules, use_reduction=use_reduction, use_rescue=use_rescue)
    hybrid_playlist=add_truth_operational_scoring_389(hybrid_playlist, truth)
    playlist=finalize_true_dynamic_playlist_389(hybrid_playlist)
    backtest_diag=build_backtest_rank_diagnostic_389(playlist, truth)

    streams_parsed=int(hist["StreamKey"].nunique()) if "StreamKey" in hist.columns else 0
    streams_scored=int(len(raw_playlist))
    streams_exported=int(len(playlist))
    reconcile_ok=(streams_parsed==streams_scored==streams_exported)

    st.subheader("Playlist Completeness Diagnostics")
    dcols=st.columns(4)
    dcols[0].metric("Streams Parsed", streams_parsed)
    dcols[1].metric("Streams Scored", streams_scored)
    dcols[2].metric("Streams Exported", streams_exported)
    dcols[3].metric("Reconciliation", "PASS" if reconcile_ok else "FAIL")
    if reconcile_ok:
        st.success("Playlist completeness reconciliation passed: parsed = scored = exported.")
    else:
        st.error("Playlist completeness reconciliation failed. Do not trust performance testing until this is resolved.")

    rank_guard=_rank_row_separation_report(playlist, "Core389 v1.4 true dynamic playlist")
    st.subheader("Rank / Row Separation Guard")
    gcols=st.columns(3)
    gcols[0].metric("Rank Guard Status", rank_guard.get("status",""))
    gcols[1].metric("Rows Checked", rank_guard.get("rows",0))
    gcols[2].metric("Warnings", len(rank_guard.get("warnings",[])))
    if rank_guard.get("status") == "OK":
        st.success("Rank/row separation guard passed.")
    else:
        st.warning("Rank/row guard found warnings. Review before trusting rank/row comparisons.")
        st.json(rank_guard)

    stream_cadence=build_stream_cadence_389(hist)
    row_cadence=build_row_cadence_if_available_389(truth)
    with st.expander("Core389 Stream Cadence — separate from Row Cadence", expanded=False):
        if stream_cadence.empty:
            st.info("No Core389 stream cadence available yet.")
        else:
            st.dataframe(stream_cadence, use_container_width=True, hide_index=True, height=450)
            st.download_button("Download Core389 Stream Cadence CSV", stream_cadence.to_csv(index=False).encode("utf-8"), file_name="core389_stream_cadence_v13.csv", mime="text/csv")
            st.download_button("Download Core389 Stream Cadence TXT", stream_cadence.to_csv(index=False, sep="	").encode("utf-8"), file_name="core389_stream_cadence_v13.txt", mime="text/plain")
    with st.expander("Core389 Row Cadence — requires uploaded truth/backtest rows with SingleRow/RowPercentile", expanded=False):
        if row_cadence.empty:
            st.info("Row cadence was not computed because the uploaded truth/backtest file does not contain SingleRow/RowPercentile/PlaylistRank/StreamRank fields.")
        else:
            st.dataframe(row_cadence, use_container_width=True, hide_index=True, height=450)
            st.download_button("Download Core389 Row Cadence CSV", row_cadence.to_csv(index=False).encode("utf-8"), file_name="core389_row_cadence_v13.csv", mime="text/csv")
            st.download_button("Download Core389 Row Cadence TXT", row_cadence.to_csv(index=False, sep="	").encode("utf-8"), file_name="core389_row_cadence_v13.txt", mime="text/plain")

    stream_audit=(hist.groupby("StreamKey", as_index=False)
                    .agg(State=("State","last"),
                         Game=("Game","last"),
                         DrawRows=("Result","size"),
                         FirstDate=("DateParsed","min"),
                         LastDate=("DateParsed","max"))
                    .sort_values(["State","Game","StreamKey"]))
    stream_audit["FirstDate"]=pd.to_datetime(stream_audit["FirstDate"]).dt.date.astype(str)
    stream_audit["LastDate"]=pd.to_datetime(stream_audit["LastDate"]).dt.date.astype(str)
    with st.expander("Unique StreamKey Audit Table", expanded=False):
        st.dataframe(stream_audit, use_container_width=True, hide_index=True, height=450)
        st.download_button("Download Unique StreamKey Audit CSV", stream_audit.to_csv(index=False).encode("utf-8"), file_name="core389_unique_streamkey_audit.csv", mime="text/csv")
        st.download_button("Download Unique StreamKey Audit TXT", stream_audit.to_csv(index=False, sep="\t").encode("utf-8"), file_name="core389_unique_streamkey_audit.txt", mime="text/plain")

    with st.expander("Core389 v1.4 Backtest / Rank Diagnostic", expanded=True):
        if backtest_diag.empty:
            st.info("Backtest rank diagnostic was not computed. Upload Truth389 with StreamKey or State/Game and a truth member/result column.")
        else:
            found=int(backtest_diag["WinnerStreamFoundInPlaylist"].sum()) if "WinnerStreamFoundInPlaylist" in backtest_diag.columns else 0
            total=int(len(backtest_diag))
            top1=int(backtest_diag["TruthMemberInTop1"].sum()) if "TruthMemberInTop1" in backtest_diag.columns else 0
            top2=int(backtest_diag["TruthMemberInTop2"].sum()) if "TruthMemberInTop2" in backtest_diag.columns else 0
            top3=int(backtest_diag["TruthMemberInTop3"].sum()) if "TruthMemberInTop3" in backtest_diag.columns else 0
            bc=st.columns(4)
            bc[0].metric("Truth Rows Checked", total)
            bc[1].metric("Winner Streams Found", found)
            bc[2].metric("Truth Member Top1", top1)
            bc[3].metric("Truth Member Top1+Top2", top2)
            st.caption("Diagnostic only unless the uploaded truth file is true per-date walk-forward truth. It reports raw-fit rank vs dynamic PlaylistRank for winner streams.")
            st.dataframe(backtest_diag, use_container_width=True, hide_index=True, height=450)
            st.download_button("Download Core389 v1.4 Backtest Rank Diagnostic CSV", backtest_diag.to_csv(index=False).encode("utf-8"), file_name="core389_v14_backtest_rank_diagnostic.csv", mime="text/csv")
            st.download_button("Download Core389 v1.4 Backtest Rank Diagnostic TXT", backtest_diag.to_csv(index=False, sep="\t").encode("utf-8"), file_name="core389_v14_backtest_rank_diagnostic.txt", mime="text/plain")

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
        st.info("Experimental overlay is OFF. v1.4 true dynamic PlaylistRank is shown/exported; raw fit rank remains visible as RawFitRank/Core389FitRank.")
    st.dataframe(playlist, use_container_width=True, hide_index=True, height=750)
    csv=playlist.to_csv(index=False).encode("utf-8")
    txt=playlist.to_csv(index=False, sep="\t").encode("utf-8")
    st.download_button("Download Core389 v1.4 TRUE DYNAMIC Daily Lab Playlist CSV", csv, file_name="core389_v14_true_dynamic_daily_lab_playlist.csv", mime="text/csv")
    st.download_button("Download Core389 v1.4 TRUE DYNAMIC Daily Lab Playlist TXT", txt, file_name="core389_v14_true_dynamic_daily_lab_playlist.txt", mime="text/plain")
    printable=playlist[[c for c in ["PlaylistRank","StreamRank","SingleRow","RowPercentile","RawFitRank_389_v14","Core389FitRank","RankSystem_389_v14","PlaylistVsRawFitDelta_389_v14","StreamKey","SeedDateUsed","SeedResult","RecommendedPlay","Top1","Top2","Top3","Action","ActualMembersToPlay","Core389FitScore","PlayCount","RunningCost_25c"] if c in playlist.columns]].copy()
    st.subheader("Printable Cleaned Lab Playlist")
    st.dataframe(printable, use_container_width=True, hide_index=True, height=550)
    st.download_button("Download Printable Core389 Lab Playlist CSV", printable.to_csv(index=False).encode("utf-8"), file_name="core389_v14_printable_true_dynamic_lab_playlist.csv", mime="text/csv")
    st.download_button("Download Printable Core389 Lab Playlist TXT", printable.to_csv(index=False, sep="\t").encode("utf-8"), file_name="core389_v14_printable_true_dynamic_lab_playlist.txt", mime="text/plain")

st.divider()
st.subheader("Core389 Notes")
st.markdown("""
- Core389 lab status: **not production-ready**.
- Use sidebar-uploaded Truth/Separator only. Generated files must be intentionally downloaded and re-uploaded.
- Phase 7 overlay remains OFF by default because it improved Top1 and balance but did not improve Top1+Top2 capture.
- `SeedDateUsed` is shown explicitly; streams without a draw on the immediately prior calendar day use their own most recent available seed.
- Playlist completeness diagnostics must reconcile: **Streams Parsed = Streams Scored = Streams Exported**.
- Raw draw add-ons after a comma, such as Fireball/Wild Ball/Superball/Sum-It-Up, are ignored for base Pick-4 parsing.
- `StreamRank`, `PlaylistRank`, `SingleRow`, and `RowPercentile` are separate visible fields.
- v1.4 fixes v1.3 rank collapse: hybrid ranking is actually rendered/exported; rank-row guard, stream cadence, optional row cadence, TOP1/TOP2/TOP3 depth/action fields, optional Core389-only reduction/rescue rulepack hooks, and optional truth operational scoring. No 025 historical constants or embedded 025 rules are used.
""")
