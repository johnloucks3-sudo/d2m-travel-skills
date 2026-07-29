def describe(item: dict) -> str:
    fid = item.get("id", "")
    type_id = fid.split("-")[0] if "-" in fid else fid
    title = (item.get("title") or "").strip()
    date_val = (item.get("date") or "").strip()
    priority = (item.get("priority") or "routine").strip().lower()
    unread = item.get("unread")
    owner = item.get("owner") or "Wing"
    source = item.get("from") or "Unknown"
    
    if type_id in ("alert", "watch"):
        tags = item.get("tags", [])
        client = tags[1] if len(tags) > 1 else "system"
        what = title
        rec = "immediate review" if priority in ("p0", "p1") else "review"
        deadline_str = f" · DEADLINE: {date_val}" if date_val else ""
        return f"WHO: {client} · WHAT: {what}{deadline_str} · REC: {rec}"
        
    elif type_id == "mission":
        what = title
        rec = "tasked" if item.get("stage") == "T" else "needs decision"
        deadline_str = f" · DEADLINE: {date_val}" if date_val else ""
        return f"WHO: {owner} · WHAT: {what}{deadline_str} · REC: {rec}"
        
    elif type_id == "gmail":
        snippet = (item.get("snippet") or "").strip()
        what = f"{title} - {snippet}"[:100]
        rec = "reply-needed" if (unread or priority in ("p0", "p1")) else "FYI"
        return f"WHO: {source} · WHAT: {what} · DEADLINE: {date_val} · REC: {rec}"
        
    elif type_id == "draft":
        what = title
        rec = "review and send"
        deadline_str = f" · DEADLINE: {date_val}" if date_val else ""
        return f"WHO: {source} · WHAT: {what}{deadline_str} · REC: {rec}"
        
    elif type_id == "keep":
        return f"WHO: Google Keep · WHAT: {title} · DEADLINE:  · REC: review"
        
    elif type_id == "sms":
        snippet = (item.get("snippet") or "").strip()
        return f"WHO: {source} · WHAT: {snippet[:100]} · DEADLINE: {date_val} · REC: reply"
        
    elif type_id in ("techscan", "next7"):
        who = "Tech Scans" if type_id == "techscan" else "Calendar"
        rec = item.get("recommendation", "review")
        return f"WHO: {who} · WHAT: {title} · DEADLINE: {date_val} · REC: Hale recommends: {rec}"
        
    else:
        return f"WHO: {source} · WHAT: {title} · DEADLINE: {date_val} · REC: review"
