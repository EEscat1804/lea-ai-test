"""Rule data — trigger regexes, response templates, tactic/risk dictionaries.

Pure data, no logic. The router (`router.py`) consumes everything from here.
Authored by Aaron Wang; ported from `evaluator.py` v2 with no changes to the
trigger patterns or response text — only restructured for module boundaries.

Spec reference: `lea_ai_guardrails_spec.html` — 20 rules G-01..G-20 across
Crisis & safety, Trauma-informed response, Mode controls, Hard refusals,
and Privacy & safety design.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CLINICAL TERMS — G-12 expert mode pairs each with a plain-language decoding
# ---------------------------------------------------------------------------

CLINICAL_TERMS: dict[str, str] = {
    "DARVO": (
        "Deny, Attack, Reverse Victim and Offender — a pattern where the abuser denies the "
        "behavior, attacks the person confronting them, and claims to be the real victim"
    ),
    "trauma bonding": (
        "a psychological attachment that forms through cycles of abuse and intermittent reward, "
        "making it hard to leave even when you want to"
    ),
    "coercive control": (
        "a pattern of behavior used to take away someone's freedom — through isolation, monitoring, "
        "financial control, or threats"
    ),
    "gaslighting": (
        "a tactic where someone causes you to question your own memory or perception of events"
    ),
    "hoovering": (
        "when an abuser tries to pull someone back into the relationship, often by acting loving "
        "or remorseful"
    ),
    "love-bombing": "overwhelming someone with affection and attention in order to gain control",
    "intermittent reinforcement": (
        "unpredictable cycles of reward and punishment that create a powerful psychological attachment"
    ),
    "Power and Control Wheel": (
        "a framework developed by domestic violence researchers that maps out the tactics abusers "
        "use to maintain dominance"
    ),
    "lethality": "the likelihood that violence will escalate to a life-threatening level",
}


# ---------------------------------------------------------------------------
# G-14 risk-scoring weights — see `router.compute_risk_level`
# ---------------------------------------------------------------------------

RISK_FACTOR_TRIGGERS: dict[str, tuple[str, int]] = {
    "strangulation": (r"choked|strangled|hands around.{0,10}throat|couldn.t breathe", 3),
    "weapon_access": (r"\b(gun|knife|weapon|firearm)\b", 2),
    "kill_threat": (r"kill me|kill (her|him|them)|going to (hurt|kill)", 3),
    "escalation": (r"getting worse|more frequent|more severe|escalat", 2),
    "isolation": (r"took my phone|cut me off|monitors (everything|my|all)", 2),
    "immigration": (r"deport|visa|undocumented|immigration status", 1),
    "financial": (r"controls.{0,15}money|no access.{0,15}account|can.t afford", 1),
    "leaving": (r"planning to leave|just left|in a shelter|moved out", 1),
    "child_witness": (r"kids (saw|heard|watched)|children.{0,10}(witness|scared|hurt)", 2),
}


# ---------------------------------------------------------------------------
# G-13 tactic patterns — used by `/analyze` flows + future ML training data
# ---------------------------------------------------------------------------

TACTIC_PATTERNS: dict[str, str] = {
    "love-bombing": (
        r"(suddenly.{0,20}(sweet|nice|loving)|bought me|overwhelm.{0,15}gift|said all the right)"
    ),
    "DARVO": (
        r"(turned it around|made me the villain|claims he.s the victim|flipped it|blamed me for)"
    ),
    "gaslighting": (
        r"(never happened|you.re imagin|you.re too sensitive|making it up|crazy|losing your mind)"
    ),
    "guilt induction": r"(look what you made|if you hadn.t|you drove me|your fault|made me do)",
    "false apologies": r"(sorry.{0,20}but|apologize.{0,20}if|sorry you feel|i.m sorry you)",
    "hoovering": (
        r"(reached out again|showed up with|promised to change|begged me back|"
        r"said it.ll be different)"
    ),
    "minimization": (
        r"(just a (push|shove|grab)|didn.t mean|wasn.t that bad|overreact|made a big deal)"
    ),
    "isolation": (
        r"(cut me off from|stopped me.{0,10}seeing|monitors.{0,10}(calls|texts|location)|"
        r"took my phone)"
    ),
    "financial coercion": (
        r"(controls.{0,15}money|gives me an allowance|checks receipts|won.t let me work|took my card)"
    ),
    "immigration threats": (
        r"(threaten.{0,15}deport|report me.{0,15}immigration|take the kids.{0,15}back to|"
        r"lose my visa)"
    ),
}


# ---------------------------------------------------------------------------
# G-01..G-20 trigger lists
# ---------------------------------------------------------------------------

# G-01: Imminent danger triggers — comprehensive coverage
G01_TRIGGERS: list[str] = [
    r"he.s here",
    r"he found me",
    r"can.t get out",
    r"held against my will",
    r"coming home soon.{0,30}(scared|afraid|terrified)",
    r"(going to|gonna|will).{0,15}(kill|hurt|shoot|stab) me",
    r"has a (gun|knife|weapon)",
    r"watches my every move",
    r"he.s (outside|downstairs|in the building)",
    r"i.m (trapped|locked in|locked up)",
    r"threatening (to kill|to hurt|me with)",
    r"(scared|afraid) (he.ll|he will) (kill|hurt|shoot)",
]

# G-02: Suicidal ideation triggers — natural phrasing included
G02_TRIGGERS: list[str] = [
    r"\bsuicid",
    r"want to die",
    r"ending it( all)?",
    r"don.t (want to|see the point of) (live|living|go on)",
    r"not (worth|worth it) (living|being alive|anymore)",
    r"rather (be dead|not be here|not exist)",
    r"self.?harm",
    r"hurt myself",
    r"no (point|reason) (in|to) (living|being here|going on)",
    r"(feel|feels) hopeless",
    r"can.t (take|do) this anymore",
]

# G-03: Child safety triggers — broader coverage
G03_TRIGGERS: list[str] = [
    r"(kids?|children?|my (son|daughter)).{0,30}(hurt|harm|danger|scared|terrified|in danger)",
    r"(hit|hurt|struck|pushed).{0,20}(kids?|children?|my (son|daughter))",
    r"(kids?|children?).{0,30}(witness(ed|ing)?|saw|watched).{0,20}(fight|hit|hurt|abuse|violence)",
    r"(kids?|children?).{0,10}(in immediate danger|not safe|with him.{0,20}drunk|"
    r"with him.{0,20}high)",
    r"(child|kids?).{0,20}(in a shelter|hiding|locked)",
    r"harming (the )?(kids?|children?)",
]

# G-04: Strangulation triggers
G04_TRIGGERS: list[str] = [
    r"choked?",
    r"strangled?",
    r"hands?.{0,10}(around|on).{0,10}(my|her).{0,5}throat",
    r"couldn.t breathe",
    r"cut.{0,10}off.{0,10}(air|breath|breathing)",
    r"\b(er|emergency room|hospital)\b",
]

# G-05: User self-doubt — validate immediately
G05_TRIGGERS: list[str] = [
    r"maybe i.m (overreacting|too sensitive|wrong|imagining)",
    r"maybe he (didn.t mean|meant well|was just)",
    r"am i (overreacting|being too sensitive|wrong|crazy)",
    r"i (probably|might be) (overreact|imagin|exaggerat)",
    r"it.s (probably|maybe) (my fault|not that bad|nothing)",
    r"i keep (making excuses|defending him|going back)",
    r"(maybe|perhaps) both sides",
]

# G-08: Verbatim disclosure — partial coverage; quoted-speech detection lives in router
G08_TRIGGERS: list[str] = [
    r"(his|her) exact words",
    r"(he|she) (told|said|called) me",
    r"(he|she) said ['\"]",
    r"texted me",
    r"(left|sent).{0,10}(voicemail|message|note)",
]

# G-09: Trauma bonding — broader triggers
G09_TRIGGERS: list[str] = [
    r"(went|go|keep going) back to (him|her)",
    r"still love (him|her)",
    r"miss (him|her)",
    r"(keep|can.t stop) making excuses",
    r"feel (stupid|weak|pathetic) for.{0,20}(staying|going back|loving)",
    r"(provoke|deserve|caused) (him|her|it|this)",
    r"why (do i|did i) defend (him|her)",
    r"feel like i.m overreacting",
    r"(better|good|loving).{0,10}(wife|husband|partner)",
]

# G-10: User's own minimizing language
G10_TRIGGERS: list[str] = [
    r"\b(just a|only a).{0,20}(misunderstanding|rough patch|bad day|fight)",
    r"communication (issue|problem|breakdown)",
    r"(both|two) sides",
    r"(didn.t mean|never means) to",
    r"in his (defense|favour|favor)",
    r"to be fair (to him|to her)",
    r"relationships? (are|can be) complicated",
    r"nobody.s perfect",
    r"rough patch",
    r"not that bad",
]

# G-16: Couples therapy / mediation — hard block
G16_TRIGGERS: list[str] = [
    r"(work on|fix|save) (the|our|this) relationship",
    r"couples?.{0,10}(therapy|counseling|counselling)",
    r"relationship.{0,10}(counselor|therapist)",
    r"\bmediation\b",
    r"sat?.{0,10}down together",
    r"(talk|sit) it out (together|with him|with her)",
]

# G-17: Abuser inner-life speculation — hard block
G17_TRIGGERS: list[str] = [
    r"(his|her) inner life",
    r"abuser.s (trauma|past|childhood)",
    r"why is (he|she) like this",
    r"acting out of (his|her) (own )?trauma",
    r"(feels?|is) insecure",
    r"(had a hard|difficult) (childhood|life|past)",
    r"(he|she).{0,20}(trauma|abused|neglected).{0,20}(growing up|as a child|when young)",
]

# G-18: Burden-shifting "have you tried X" — hard block
G18_TRIGGERS: list[str] = [
    r"have you tried.{0,30}(bound|limit|calm|talk|approach|communicat)",
    r"(respond|react).{0,10}differently",
    r"if you (didn.t|don.t) react",
    r"telling (him|her) calmly",
    r"set (clearer|better|firm) limits?",
    r"what (could|can) you do differently",
    r"(give|giving) (him|her) space",
    r"approach (him|her) differently",
    r"(have|did) you (try|tried).{0,20}(de.escalat|calm|different)",
]

# G-20: Monitoring / stalkerware triggers
G20_TRIGGERS: list[str] = [
    r"monitor(s|ing)? (everything|my|all)",
    r"reads? my (texts?|messages?|emails?)",
    r"spyware",
    r"stalkerware",
    r"delete (our|this|the) (conversation|chat|history)",
    r"tracking my (phone|location|device)",
    r"keylogger",
    r"(shared|his|her) (device|computer|phone)",
]


# ---------------------------------------------------------------------------
# RESPONSE TEMPLATES
# ---------------------------------------------------------------------------

RESP: dict[str, str] = {
    "G01": (
        "I hear you. Before anything else — are you safe to talk right now, or do you need to go? "
        "If you need help in this moment: National DV Hotline 1-800-799-7233 (24/7), "
        "text START to 88788, or thehotline.org for live chat. "
        "Call 911 if you are in immediate danger. I am here whenever you come back."
    ),
    "G02": (
        "What you just shared matters more than anything else right now. "
        "Please reach out to 988 (call or text, 24/7) — they are trained for exactly this "
        "and will not judge you. Are you safe to talk right now?"
    ),
    "G03_ack": (
        "What you just shared about your children matters enormously, and I want to address it "
        "separately before anything else. "
        "If they are in immediate danger right now, please call 911 and ask for an emergency "
        "welfare check. "
        "For specialized support: Childhelp National Child Abuse Hotline 1-800-422-4453 (24/7). "
        "Children who witness abuse are also experiencing harm — that is not your fault, "
        "and there is support specifically for them."
    ),
    "G04": (
        "SAFETY WARNING: Strangulation is considered a life-threatening assault. "
        "Research shows it is one of the strongest indicators that violence may become fatal. "
        "Please seek medical evaluation even if you feel fine right now — internal injuries from "
        "strangulation are not always immediately visible. "
        "Help is available 24/7: 1-800-799-7233. Are you safe to talk right now?"
    ),
    "G05_validation": (
        "What you experienced is real. Your perception of what happened is valid. "
        "Questioning yourself — wondering if you're overreacting — is an extremely common response "
        "to sustained pressure to doubt your own experience. It does not mean you were wrong."
    ),
    "G06_block": (
        "The decision about what to do next is yours, and yours alone. "
        "There are options and resources available when you are ready — "
        "including safety planning, housing support, and legal pathways. "
        "Would you like me to show you what's available in your area, at your own pace?"
    ),
    "G09_validation": (
        "What you're feeling makes complete sense given what you've been through. "
        "The pull to go back, or to still care about someone who's hurt you, "
        "is a well-documented psychological response to cycles of harm and relief — "
        "it is not weakness, and it is not your fault."
    ),
    "G09_education": (
        "This is sometimes called trauma bonding — a survival mechanism that forms through "
        "intermittent cycles of tension and relief. Understanding it can help explain "
        "why leaving feels so complicated, even when part of you wants to. "
        "Would you like me to share some gentle informational materials on how this works?"
    ),
    "G10_reframe": (
        "I want to gently reflect something back: the way you described that — "
        "as a misunderstanding, or a rough patch — is language that tends to minimize "
        "what's actually happening. What you've described to me is a pattern of behavior, "
        "not a communication problem. Would it be okay if we used more precise language "
        "when we document this on your forms? It matters for how the court reads it."
    ),
    "G11_activate": (
        "Got it. I'll keep things conversational from here — no lists, no jargon. "
        "Just talk to me like you would a trusted friend who happens to know this process well. "
        "What's on your mind?"
    ),
    "G12_activate": (
        "Switching to a more detailed mode. I'll use the clinical frameworks where they're relevant "
        "and explain each one as we go. What would you like to look at first?"
    ),
    "G15_activate": (
        "Language coach mode — I'll give you actual sentences you can use, not just general advice. "
        "Tell me the specific situation: who are you talking to (police, a clerk, a judge, him), "
        "and what do you need to communicate?"
    ),
    "G16_block": (
        "Couples therapy and mediation are not appropriate frameworks when coercive control "
        "is present — they assume both parties have equal power, which is not the case here, "
        "and they can create serious risks. "
        "I can help you with the legal and support options that are designed for your situation. "
        "Want me to walk through what those look like in your county?"
    ),
    "G17_block": (
        "Understanding why someone behaves abusively does not make the behavior acceptable or safe "
        "— and speculating about it is not something I can do helpfully here. "
        "What I can do is help you document what happened and map out your options. "
        "Want to return to that?"
    ),
    "G18_block": (
        "The responsibility for this behavior belongs entirely to the person causing harm — "
        "not to how you respond, or what you say, or how you approach it. "
        "I won't suggest ways you could change your behavior to manage his. "
        "What I can help with is documenting what's happened and finding support. "
        "Want to keep working on that?"
    ),
    "G19_frontend_note": (
        "[FRONTEND SIGNAL] Quick-exit button must be visible and functional on this screen. "
        "Escape key (×2) should redirect to neutral page. This is a required UI element."
    ),
    "G20_security": (
        "ACTION NEEDED — SECURITY NOTICE: Monitoring software, stalkerware, and keyloggers "
        "can capture your screen before our encryption takes effect. "
        "Stop using this device for sensitive planning. "
        "Access help through an unmonitored alternative — a library workstation, "
        "public computer, or a trusted friend's phone. "
        "If using a browser: use private/incognito mode and clear your history manually. "
        "Want me to save our session here while you switch to a safer device?"
    ),
    "G_predict_block": (
        "I cannot predict legal outcomes or tell you whether you have a strong case — "
        "that would require a licensed attorney reviewing your specific situation. "
        "What I can do is help you document the incidents as clearly and completely as possible, "
        "which is what matters most for how the court reads your petition."
    ),
    "G_third_party_block": (
        "Conversations in this system are private and encrypted. "
        "Session content is not accessible to outside parties."
    ),
    "G_default": "I'm here to support you at your own pace. What would you like to work on?",
}


# ---------------------------------------------------------------------------
# G-15 LANGUAGE COACH SCRIPTS
# ---------------------------------------------------------------------------

LANGUAGE_COACH_SCRIPTS: dict[str, str] = {
    "police": (
        "Here are sentences you can use when speaking to police:\n"
        "• 'I have a restraining order against [name]. He violated it by [what happened].'\n"
        "• 'I need this documented as a violation of a protective order, not just a disturbance.'\n"
        "• 'I would like to make a report and receive a copy of the report number.'\n"
        "• If they dismiss you: 'I understand, but I want this on record. "
        "Can you tell me the report number?'\n"
        "Do NOT say: 'I'm not sure if it counts' or 'maybe I'm overreacting' — "
        "state the facts plainly and let the officer decide."
    ),
    "clerk": (
        "Here are sentences for speaking to the court clerk:\n"
        "• 'I'm here to file a petition for a domestic violence restraining order.'\n"
        "• 'I need to know if there's a fee waiver application — I qualify based on income.'\n"
        "• 'Can you tell me where I go after I file this, and what to expect today?'\n"
        "• If you need an interpreter: 'I need an interpreter for [language]. Is one available?'"
    ),
    "judge": (
        "Here are sentences for your court appearance:\n"
        "• When asked to describe the incident: State the date, what he did, and what you feared. "
        "Keep it factual: 'On [date], he [specific action]. I was afraid because [reason].'\n"
        "• If he denies it: You do not have to argue. Say: 'That is not what happened.'\n"
        "• If you need a moment: 'Your Honor, may I have a moment?' — you are allowed to pause.\n"
        "• Do not apologize for being there. You have a right to be heard."
    ),
}
