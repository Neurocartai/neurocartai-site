import os, json, time, hashlib
from typing import Dict, Any, List, Tuple
import yaml

class RiskGuard:
    def _init_(self, path:str):
        with open(path, "r") as f:
            self.cfg = yaml.safe_load(f)
        self.index = {
            r["id"]: r
            for r in self.cfg.get("risks", [])
        }
        # simple in-memory cache for demo; swap with Redis/Firestore in prod
        self.history = []  # list of {ts, channel, caption, body, image_hash, user_id, locale}

    def _similarity(self, a:str, b:str)->float:
        # very rough placeholder (swap for proper embedding sim later)
        set_a, set_b = set(a.lower().split()), set(b.lower().split())
        if not set_a or not set_b: return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    def _hash_image(self, blob_id:str)->str:
        return hashlib.sha1(blob_id.encode("utf-8")).hexdigest()

    def record_event(self, event:Dict[str,Any]):
        """Call after successful post to feed history (for duplicate/rate limits)."""
        event = dict(event)
        event["ts"] = time.time()
        if "image_id" in event and "image_hash" not in event:
            event["image_hash"] = self._hash_image(event["image_id"])
        self.history.append(event)

    def check(self, action:Dict[str,Any]) -> Tuple[bool, List[Dict[str,Any]]]:
        """
        Validate a pending action. Return (ok, violations[])
        action keys (example):
          kind: 'social_post' | 'reply' | ...
          channel: 'twitter'|'instagram'|'youtube'|...
          caption/body: text
          image_hash or image_id
          user_id, audience_id, locale
        """
        violations = []
        now = time.time()
        kind = action.get("kind", "social_post")
        caption = action.get("caption","") or action.get("body","")
        locale = (action.get("locale") or "US").upper()
        channel = action.get("channel") or "generic"

        # RULE: content_duplicate
        r = self.index.get("content_duplicate")
        if r and kind in r.get("applies_to", []):
            window = 3600 * r["detect"].get("window_hours", 48)
            thresh = r["detect"].get("threshold", 0.92)
            hsh = action.get("image_hash") or (action.get("image_id") and self._hash_image(action["image_id"]))
            for ev in reversed(self.history[-500:]):  # small window; replace with query later
                if now - ev["ts"] > window: break
                if ev.get("channel")==channel:
                    sim = self._similarity(caption, (ev.get("caption") or ev.get("body") or ""))
                    same_img = hsh and hsh==ev.get("image_hash")
                    if sim >= thresh or same_img:
                        violations.append({
                            "risk_id":"content_duplicate",
                            "detail":f"Similarity={sim:.2f} same_img={bool(same_img)} within {r['detect']['window_hours']}h"
                        })
                        break

        # RULE: rate_limit_spam
        r = self.index.get("rate_limit_spam")
        if r and kind in r.get("applies_to", []):
            per_day = r["detect"].get("per_channel_per_day", 24)
            hour_burst = r["detect"].get("burst_limit_per_hour", 5)
            day_count = 0; hour_count = 0
            for ev in reversed(self.history[-1000:]):
                age = now - ev["ts"]
                if ev.get("channel") != channel: continue
                if age <= 3600: hour_count += 1
                if age <= 86400: day_count += 1
            if hour_count >= hour_burst or day_count >= per_day:
                violations.append({
                    "risk_id":"rate_limit_spam",
                    "detail":f"hour_count={hour_count} day_count={day_count} (limits h={hour_burst}, d={per_day})"
                })

        # RULE: regional_tone_mismatch (lightweight placeholder)
        r = self.index.get("regional_tone_mismatch")
        if r and kind in r.get("applies_to", []):
            rules = r["detect"].get("rules", [])
            for rule in rules:
                if rule.get("locale") == locale:
                    # very light checks; replace with your style/tone analyzer
                    if rule.get("emoji_max", 999) < caption.count("😀"):
                        violations.append({"risk_id":"regional_tone_mismatch",
                                           "detail": f"emoji overuse for locale {locale}"})
                    break

        # RULE: ip_licensing (basic placeholder)
        r = self.index.get("ip_licensing")
        if r and kind in r.get("applies_to", []):
            if action.get("asset_source") and (action["asset_source"] not in r["detect"]["allowed_sources"]):
                violations.append({"risk_id":"ip_licensing",
                                   "detail": f"asset_source={action['asset_source']} not allowed"})
            if r["detect"].get("require_license_tag") and not action.get("license_tag"):
                violations.append({"risk_id":"ip_licensing",
                                   "detail": "missing license_tag"})

        # RULE: factuality_offer_integrity (stub: enforce SOT checks upstream)
        # Here we just honor a flag that upstream set if SOT failed
        r = self.index.get("factuality_offer_integrity")
        if r and kind in r.get("applies_to", []):
            if action.get("sot_checked") is False:
                violations.append({"risk_id":"factuality_offer_integrity",
                                   "detail":"source-of-truth check not performed"})

        ok = len(violations) == 0
        return ok, violations
