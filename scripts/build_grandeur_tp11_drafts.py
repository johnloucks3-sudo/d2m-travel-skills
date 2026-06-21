#!/usr/bin/env python3
"""
Build Grandeur Group TP 1.1 Voyage Preview emails using navy template.
Three personalized versions for Furlow, Nichols, Ely/Darrow.
Ready for Commander review in johnloucks3 Gmail drafts.

Source: TP_1.1_Grandeur_Group_Voyage_Preview_FINAL_THREE_VERSIONS.txt
Template: kuklinski_excursion_survey_intro_dani.html (proven navy format)
"""
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
OUT = ROOT / "output" / "grandeur_tp11_html"
OUT.mkdir(parents=True, exist_ok=True)

# Load gold-standard navy template
GOLD = (ROOT / "drafts/kuklinski_excursion_survey_intro_dani.html").read_text(encoding="utf-8")

# Extract prefix (everything up to body content starts)
BODY_OPEN = 'line-height:1.85;color:#e8f1ff;">'
PREFIX = GOLD[: GOLD.index(BODY_OPEN) + len(BODY_OPEN)]

# Extract suffix (from first shimmer comment onward)
SUFFIX = '\n    </td>\n  </tr>\n\n  ' + GOLD[GOLD.index('<!-- Mid shimmer -->'):]

# Update Dani's title to disclose AI (Commander edit 2026-06-20)
SUFFIX = SUFFIX.replace("Luxury Travel Concierge", "Luxury AI Travel Concierge")

# ---- Helper functions (match gold standard) ----
def P(t):
    return f'<p style="margin:0 0 20px 0;">{t}</p>'

def H2(t):
    return (f'<h2 style="color:#c8dcff;font-family:Georgia,serif;font-size:18px;'
            f'border-bottom:1px solid rgba(180,200,255,0.35);padding-bottom:8px;'
            f'margin:0 0 18px 0;letter-spacing:1px;">{t}</h2>')

def B(t):
    return f'<strong style="color:#f0f6ff;">{t}</strong>'

DIV = ('<div style="height:1px;margin:24px 0;background:linear-gradient(90deg,'
       'transparent 0%,rgba(220,235,255,0.5) 50%,transparent 100%);"></div>')

def NOTE_GOLD(t):
    return (f'<div style="background:rgba(255,215,0,0.07);'
            f'border-left:4px solid rgba(255,215,0,0.55);'
            f'padding:14px 18px;margin:0 0 20px 0;border-radius:0 4px 4px 0;">{t}</div>')

def assemble(*parts):
    return PREFIX + "\n\n" + "\n".join(parts) + "\n" + SUFFIX

# ===================== FURLOW =====================
# From: TP_1.1_Grandeur_Group_Voyage_Preview_FINAL_THREE_VERSIONS.txt lines 6-61

furlow_body = [
    P("Dear John & Missy,"),
    P("You're traveling with your dearest friends, and I want you to know what's waiting for you."),
    P("For ten days in the heart of summer-bleeding-into-autumn, you'll chase the light that lingers in Scandinavia — where midnight is twilight and the sky lives in shades of honey and silver. This voyage is not just a cruise; it's an invitation to step into a world that has inspired millennia of stories: the Viking seas, the royal capitals, the landscape that shaped European history. You've both thought carefully about this trip, and it shows — from your direct flight bookings to the questions you've asked along the way. That's the kind of clarity that turns a voyage into a real story."),
    P("Stockholm spreads across fourteen islands like a watercolor someone spilled deliberately — each bridge a stroke. Your two days here open with the cobblestones of Gamla Stan and the royal gravitas of the Drottningholm Palace. The museums hold centuries: the Vasa (the only warship that never fought), the Nordic art that whispers in shadow and light. You'll move through it together, three couples anchored in friendship."),
    P("Berlin teaches hardness and honesty in a day. Warnemunde exhales — Baltic light on water, the weight lifted, room to think. The excursions turn contemplative here, and you can feel the continent's story written into the architecture and the silence."),
    P("Copenhagen is the unexpected jewel — Nyhavn's candy-colored buildings framing the harbor, Christiania's counterculture whisper, the Little Mermaid watching it all. Here the design is intentional, the smørrebrød is an art form, and the air tastes like salt and bicycles and civilized rebellion."),
    P("Kristiansand and Oslo are Norway — the fjord-carved coastline, the Resistance legacy, the modern architecture that pays homage to ancient wood-working. In Oslo, you'll stand in the presence of Munch, of Viking ships, of a nation that has held its peace and its purpose for generations."),
    P("This is the story Scandinavia tells to those who arrive as witnesses: of light, endurance, craft, and the particular magic that happens when you travel with people you genuinely love."),
    DIV,
    H2("WHAT YOU'VE BOOKED"),
    P("You've secured the best of what Regent offers. Both you and Missy have booked seven shore excursions across the voyage — each included, each scheduled with care so you're exploring together. The lineup moves through history and landscape both: Stockholm's Vasa Museum and city highlights · Berlin's concentrated weight · Copenhagen's design and gardens · Oslo's museums and stories."),
    P(f"On specialty dining — Regent's most elegant culinary experiences — you've already claimed three of the signature restaurants. August 30 at {B('Pacific Rim')}. September 2 at {B('Chartreuse')}. September 4 at {B('Prime 7')}. These windows opened just recently, and you've secured them. The ship's Culinary Arts Kitchen Classes open May 1 if you'd like to book one of those onboard."),
    DIV,
    H2("TIMELINE & LOGISTICS"),
    P("Your flights leave Dallas on August 26 at 4:50 PM (American Airlines/Finnair, Business Class). You'll arrive in Helsinki August 27 morning and connect the same day to Stockholm, where you'll spend two nights at the At Six Stockholm (your choice). Regent picks you up from your hotel August 29 and delivers you to Suite embarkation."),
    P(f"Your suite assignments on Regent Grandeur are confirmed:{B('<br>John & Missy: Suite 827, Deck 8<br>Larry & Heidi: Suite 939, Deck 9<br>Al & Amy: Suite 961, Deck 9')}"),
    P("Online check-in opens August 8 — you can complete that on the Regent portal at your convenience. Excursions and specialty dining selections close August 22 (seven days out) — but you've already selected yours, so you're clear."),
    P("Return flights leave Oslo September 8 at 11:15 AM, connecting through London to Dallas at 6:35 PM the same day. Regent handles your transport from ship to airport."),
    DIV,
    H2("NEXT STEPS"),
    P("This is a lot of detail, so I wanted to lay it out clearly. If you have questions — about the restaurants, about your cabins, about what to expect in each port — reach out. I'm here for it."),
    P("In the meantime, when you're ready, you can log into rssc.com/myaccount with your booking confirmation and explore the Regent portal. Your guest registrations are live. The pre-voyage information builds out over the next weeks."),
    P("I'll be in touch in July with your final confirmation and any last details. For now, know that you're ready, your bookings are locked, and Scandinavia in August is something else entirely."),
    P("Thank you for letting me be part of this."),
    P("<br>Dani<br>Luxury AI Travel Concierge, Dreams2Memories Travel"),
]

furlow_html = assemble(*furlow_body)

# ===================== NICHOLS =====================
# From: TP_1.1_Grandeur_Group_Voyage_Preview_FINAL_THREE_VERSIONS.txt lines 66-122

nichols_body = [
    P("Dear Larry & Heidi,"),
    P("You're traveling with your dearest friends, and I want you to know what's waiting for you."),
    P("For ten days in the heart of summer-bleeding-into-autumn, you'll chase the light that lingers in Scandinavia — where midnight is twilight and the sky lives in shades of honey and silver. This voyage is not just a cruise; it's an invitation to step into a world that has inspired millennia of stories: the Viking seas, the royal capitals, the landscape that shaped European history. And Heidi, you're turning another year on the water — on August 29, at sea where there are no distractions, just the horizon and the two couples who know you best. That's the kind of birthday worth waiting for."),
    P("Stockholm spreads across fourteen islands like a watercolor someone spilled deliberately — each bridge a stroke. Your two days here open with the cobblestones of Gamla Stan and the royal gravitas of the Drottningholm Palace. The museums hold centuries: the Vasa (the only warship that never fought), the Nordic art that whispers in shadow and light. You'll move through it together, three couples anchored in friendship."),
    P("Berlin teaches hardness and honesty in a day. Warnemunde exhales — Baltic light on water, the weight lifted, room to think. The excursions turn contemplative here, and you can feel the continent's story written into the architecture and the silence."),
    P("Copenhagen is the unexpected jewel — Nyhavn's candy-colored buildings framing the harbor, Christiania's counterculture whisper, the Little Mermaid watching it all. Here the design is intentional, the smørrebrød is an art form, and the air tastes like salt and bicycles and civilized rebellion."),
    P("Kristiansand and Oslo are Norway — the fjord-carved coastline, the Resistance legacy, the modern architecture that pays homage to ancient wood-working. In Oslo, you'll stand in the presence of Munch, of Viking ships, of a nation that has held its peace and its purpose for generations."),
    P("This is the story Scandinavia tells to those who arrive as witnesses: of light, endurance, craft, and the particular magic that happens when you travel with people you genuinely love."),
    DIV,
    H2("WHAT YOU'VE BOOKED"),
    P("You've secured the best of what Regent offers. Both you and Larry have booked seven shore excursions across the voyage — each included, each scheduled with care so you're exploring together. The lineup moves through history and landscape both: Stockholm's Vasa Museum and city highlights · Berlin's concentrated weight · Copenhagen's design and gardens · Oslo's museums and stories."),
    P(f"On specialty dining — Regent's most elegant culinary experiences — you've already claimed three of the signature restaurants. August 30 at {B('Pacific Rim')}. September 2 at {B('Chartreuse')}. September 4 at {B('Prime 7')}. That September 2 dinner at Chartreuse — that's your birthday night at sea. These windows opened just recently, and you've secured them. The ship's Culinary Arts Kitchen Classes open May 1 if you'd like to book one of those onboard."),
    DIV,
    H2("TIMELINE & LOGISTICS"),
    P("Your flights leave Dallas on August 26 at 4:50 PM (American Airlines/Finnair, Business Class). You'll arrive in Helsinki August 27 morning and connect the same day to Stockholm, where you'll spend two nights at the At Six Stockholm (your choice). Regent picks you up from your hotel August 29 and delivers you to Suite embarkation."),
    P(f"Your suite assignments on Regent Grandeur are confirmed:{B('<br>John & Missy: Suite 827, Deck 8<br>Larry & Heidi: Suite 939, Deck 9<br>Al & Amy: Suite 961, Deck 9')}"),
    P("Online check-in opens August 8 — you can complete that on the Regent portal at your convenience. Excursions and specialty dining selections close August 22 (seven days out) — but you've already selected yours, so you're clear."),
    P("Return flights leave Oslo September 8 at 11:15 AM, connecting through London to Dallas at 6:35 PM the same day. Regent handles your transport from ship to airport."),
    DIV,
    H2("NEXT STEPS"),
    P("This is a lot of detail, so I wanted to lay it out clearly. If you have questions — about the restaurants, about your cabins, about what to expect in each port — reach out. I'm here for it."),
    P("In the meantime, when you're ready, you can log into rssc.com/myaccount with your booking confirmation and explore the Regent portal. Your guest registrations are live. The pre-voyage information builds out over the next weeks."),
    P("I'll be in touch in July with your final confirmation and any last details. For now, know that you're ready, your bookings are locked, and Scandinavia in August is something else entirely."),
    P("Thank you for letting me be part of this."),
    P("<br>Dani<br>Luxury AI Travel Concierge, Dreams2Memories Travel"),
]

nichols_html = assemble(*nichols_body)

# ===================== ELY/DARROW =====================
# From: TP_1.1_Grandeur_Group_Voyage_Preview_FINAL_THREE_VERSIONS.txt lines 126-182

ely_body = [
    P("Dear Al & Amy,"),
    P("You're traveling with your dearest friends, and I want you to know what's waiting for you."),
    P("For ten days in the heart of summer-bleeding-into-autumn, you'll chase the light that lingers in Scandinavia — where midnight is twilight and the sky lives in shades of honey and silver. This voyage is not just a cruise; it's an invitation to step into a world that has inspired millennia of stories: the Viking seas, the royal capitals, the landscape that shaped European history. You've both been thoughtful about every detail — the right insurance, the right timeline, the logistics that let you travel well. That care shows up in every piece of this voyage, and it will matter."),
    P("Stockholm spreads across fourteen islands like a watercolor someone spilled deliberately — each bridge a stroke. Your two days here open with the cobblestones of Gamla Stan and the royal gravitas of the Drottningholm Palace. The museums hold centuries: the Vasa (the only warship that never fought), the Nordic art that whispers in shadow and light. You'll move through it together, three couples anchored in friendship."),
    P("Berlin teaches hardness and honesty in a day. Warnemunde exhales — Baltic light on water, the weight lifted, room to think. The excursions turn contemplative here, and you can feel the continent's story written into the architecture and the silence."),
    P("Copenhagen is the unexpected jewel — Nyhavn's candy-colored buildings framing the harbor, Christiania's counterculture whisper, the Little Mermaid watching it all. Here the design is intentional, the smørrebrød is an art form, and the air tastes like salt and bicycles and civilized rebellion."),
    P("Kristiansand and Oslo are Norway — the fjord-carved coastline, the Resistance legacy, the modern architecture that pays homage to ancient wood-working. In Oslo, you'll stand in the presence of Munch, of Viking ships, of a nation that has held its peace and its purpose for generations."),
    P("This is the story Scandinavia tells to those who arrive as witnesses: of light, endurance, craft, and the particular magic that happens when you travel with people you genuinely love."),
    DIV,
    H2("WHAT YOU'VE BOOKED"),
    P("You've secured the best of what Regent offers. Both you and Al have booked six shore excursions across the voyage — each included, each scheduled with care so you're exploring together. The lineup moves through history and landscape both: Stockholm's Swedish Nature Experience · Berlin's concentrated weight · Copenhagen's design and gardens · Oslo's World War II legacy. Al, you've also selected excursions with accessibility in mind, and Regent's teams are ready for that."),
    P(f"On specialty dining — Regent's most elegant culinary experiences — you've already claimed three of the signature restaurants. August 30 at {B('Pacific Rim')}. September 2 at {B('Chartreuse')}. September 4 at {B('Prime 7')}. These windows opened just recently, and you've secured them. The ship's Culinary Arts Kitchen Classes open May 1 if you'd like to book one of those onboard."),
    DIV,
    H2("TIMELINE & LOGISTICS"),
    P("Your flights leave Dallas on August 26 at 4:50 PM (American Airlines/Finnair, Business Class). You'll arrive in Helsinki August 27 morning and connect the same day to Stockholm, where you'll spend two nights at the At Six Stockholm (your arrangement). Regent picks you up from your hotel August 29 and delivers you to Suite embarkation."),
    P(f"Your suite assignments on Regent Grandeur are confirmed:{B('<br>John & Missy: Suite 827, Deck 8<br>Larry & Heidi: Suite 939, Deck 9<br>Al & Amy: Suite 961, Deck 9')}"),
    P("Online check-in opens August 8 — you can complete that on the Regent portal at your convenience. Excursions and specialty dining selections close August 22 (seven days out) — but you've already selected yours, so you're clear."),
    P("Return flights leave Oslo September 8 at 11:15 AM, connecting through London to Dallas at 6:35 PM the same day. Regent handles your transport from ship to airport."),
    DIV,
    H2("NEXT STEPS"),
    P("This is a lot of detail, so I wanted to lay it out clearly. If you have questions — about the restaurants, about your cabins, about what to expect in each port — reach out. I'm here for it."),
    P("In the meantime, when you're ready, you can log into rssc.com/myaccount with your booking confirmation and explore the Regent portal. Your guest registrations are live. The pre-voyage information builds out over the next weeks."),
    P("I'll be in touch in July with your final confirmation and any last details. For now, know that you're ready, your bookings are locked, and Scandinavia in August is something else entirely."),
    P("Thank you for letting me be part of this."),
    P("<br>Dani<br>Luxury AI Travel Concierge, Dreams2Memories Travel"),
]

ely_html = assemble(*ely_body)

# Write all three versions
(OUT / "Furlow_TP1.1_VoyagePreview.html").write_text(furlow_html, encoding="utf-8")
(OUT / "Nichols_TP1.1_VoyagePreview.html").write_text(nichols_html, encoding="utf-8")
(OUT / "Ely_Darrow_TP1.1_VoyagePreview.html").write_text(ely_html, encoding="utf-8")

print(f"✅ Three TP 1.1 Voyage Preview emails built to: {OUT}")
print(f"   - Furlow_TP1.1_VoyagePreview.html")
print(f"   - Nichols_TP1.1_VoyagePreview.html")
print(f"   - Ely_Darrow_TP1.1_VoyagePreview.html")
