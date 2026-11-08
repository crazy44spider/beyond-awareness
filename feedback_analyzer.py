"""
Participant feedback coding (EveryMind 988 survey).

Reads the survey Excel file, cleans it, translates Spanish comments, redacts
names, and tags both open-ended questions into themes (multi-label keyword
coding). Run `python feedback_coding.py` to print the summaries.
Importing this file does not print anything.

Do NOT commit the data/ folder (raw participant comments).
"""
import re
from string import capwords

import pandas as pd

NAMES_TO_REDACT = ["Athena", "Andrea", "Jennifer", "Laura", "Morales", "Sophia"]  # add any others you spot


# ---------- cleaning functions ----------
NON_ANSWERS = {"na", "n/a", "none", "no", "nope", "nothing", "nil",
               "no comment", "no comments", "nothing to add", "not applicable",
               "idk", "i dont know", "dont know",
               "no se", "no s", "no se / idk"}


def comment_key(x):
    return re.sub(r"[^a-z/ ]", "", str(x).lower().strip()).strip()


def clean_comment(x):
    if pd.isna(x):
        return None
    text = str(x).strip()
    key = comment_key(text)
    if key == "" or key in NON_ANSWERS:
        return None
    return text


def clean_county(x):
    if pd.isna(x):
        return None
    t = str(x).lower().replace("’", "'")
    t = " ".join(t.split())
    t = t.replace(" county", "").strip()
    if t.startswith("montgomery"):
        t = "montgomery"
    return capwords(t)


def clean_role(x):
    if pd.isna(x):
        return None
    parts = [p.strip() for p in str(x).split(";") if p.strip()]
    if len(parts) == 0:
        return None
    if len(parts) > 1:
        return "Multiple roles"
    return parts[0]


def redact(text):
    if pd.isna(text):
        return text
    for name in NAMES_TO_REDACT:
        text = re.sub(r"\b" + re.escape(name) + r"\b", "[name]", text, flags=re.IGNORECASE)
    return text


translations_learned = {
    34: "I love the information. I think all of us have a moment in our lives when we need support and can't always express it to our family or friends.",
    122: "[unclear] 911 or 988",
    123: "Paying more attention to our children at all times to prevent any situation.",
    124: "Knowing that there is help for my family and friends.",
    125: "Knowing how I can help my son, since he is going through a problem.",
    191: "That there are people who can help.",
    192: "Mental help.",
    193: "911 and 988 are not the same, but they work together.",
    194: "That 911 itself works together with 988.",
    195: "That students can get help.",
    196: "The 988.",
    198: "That there are people to help us.",
    200: "That I can call and receive professional help.",
    201: "Knowing that I can share it with my family.",
    202: "The 988.",
}

translations_improve = {
    33: "Everything is very good.",
    34: "I think it's perfect.",
    107: "Yes, I think it can be improved.",
    123: "We as parents have to support the institution so that they are always willing to keep offering the trainings.",
    124: "Help all the schools in the country.",
    125: "I think it is very complete. Thank you for bringing such a valuable tool!",
    192: "Helping others.",
    195: "Sharing it with the people who need it.",
    198: "Talking with others and trying to share it with those who need it.",
    200: "With more illustrations.",
    201: "Yes, I would like them to bring back the LGBTQ+ line.",
    202: "Everything was fine.",
}

translations_learned.update({
    85: "That there is a resource to help people who are in a mental health crisis.",
    87: "I learned that 988 is not only for students but also for adults, and it is also free.",
    88: "The most valuable thing I learned is about 988, because it's knowing that someone can listen to what you feel.",
    89: "What I learned is that there is a 988 number to call so that they listen to us and help parents, children, and young people.",
    90: "We learned how to help someone.",
    91: "How I will be able to use that number, and that it is important to talk.",
    92: "How to detect a crisis and how to use the number.",
    93: "That there are people who listen to us and can help us.",
    94: "Knowing that there is help for my family and friends.",
    95: "This information is very important to keep in mind. It's important to dedicate time to our children to listen and be able to detect the problem in time.",
    101: "For me everything is very important, everything was very good.",
    102: "I was very interested in what the highly trained people did.",
    104: "How to reach out to ask for help.",
    105: "Caring about people's lives.",
    107: "Very important information.",
    108: "The importance of knowing that we can count on someone who can listen to us.",
    109: "The information.",
    110: "That there are therapies and trained people.",
    203: "For me, the valuable thing was that now I know how to tell when people may be in a crisis, and I know the number to call or text, 988.",
    205: "The statistics about suicide stood out.",
    209: "How to use 988.",
    213: "Paying more attention to children's warning signs.",
    215: "Everything.",
    216: "I liked it because I will know how to call 988 if there is a suicide emergency.",
    217: "The number to call to be able to talk with someone to seek help: 988.",
    218: "How to pay more attention to children when they need help.",
    219: "Paying more attention to children.",
    277: "That no matter what is going on, you can ask people for help.",
    473: "The most valuable thing I learned was when to use the hotline and how it works.",
    474: "The part about nicknames to feel more comfortable.",
    475: "That when I call 988 I will always get help.",
    476: "That they are available 24/7, every day.",
    477: "988 helps more than [unclear] because they can listen to you more.",
    478: "How to connect to 988.",
    479: "The most valuable thing I learned is that 988 can help with mental health.",
    480: "The most valuable thing I learned was when to call 988.",
    483: "The most valuable thing I learned during the training was how to use 988.",
    484: "The most valuable thing I learned was that you can communicate with 988 by call or message.",
    485: "How to use 988 and when to use it was the most valuable thing I learned during the training.",
    486: "I liked how it was explained.",
    487: "The most valuable thing was that students now understand what to do when they are going through a difficult time.",
    488: "The most valuable thing I learned during the training was that 988 is not only for emergencies but also for talking with someone.",
    489: "What I learned during the training was that it helps you pick yourself up when you are depressed.",
    490: "The best thing I learned was that it helps you pick yourself up when you are depressed or going through bad times.",
    491: "I thought this number was only for depression, but they told me I could use it even when I feel lonely or just want company.",
    492: "That the 988 line is available at all times.",
    493: "I think that in some cases I can talk freely, and if it is too urgent they will call 911.",
    494: "Everything was very impressive.",
    495: "What I learned was that when I have problems I can call 988.",
    496: "What I learned was that when I have problems I can call 988.",
    497: "The most valuable thing I learned during the training was understanding when someone has problems, being able to identify them and help them or recommend the 988 line to them, because it is safer.",
    498: "You can call 988, or text and chat.",
    499: "Knowing that I can count on someone to talk about my problems.",
    500: "I learned that 988 is only used for situations that could reach the point of death.",
})

translations_improve.update({
    85: "Sharing all the necessary information with all parents, to help parents with discipline. [garbled in original]",
    87: "I loved that there were donuts and coffee; also the reminders are important.",
    88: "It's important that we share the information with other people and know that help exists.",
    89: "That everyone knows there is a place to call or text to be listened to and to get advice on how to counsel our children and other people.",
    90: "By informing other classmates.",
    93: "By being able to reach the families who are going through this process.",
    94: "Help all the schools in the country.",
    95: "Calling 988 if necessary, both for myself or my family; being listened to is very important.",
    101: "Keep always giving these meetings; very good.",
    102: "How they work is very good.",
    104: "I understood well; I feel it was great.",
    108: "Bringing this information to more homes.",
    109: "All good.",
    110: "Giving the information to people who have these problems.",
    203: "Everyone practicing how important it is to recognize crises and to always know the 988 number.",
    205: "That students be at the training.",
    210: "It would be better if we went to a private place, one by one, to ask questions about this kind of help. I feel that when someone is going through things, they don't know how to act or respond in front of the public. Thank you for the good information.",
    215: "That more families come.",
    216: "Putting the training into practice by knowing what people's crises look like.",
    217: "Everything was good; I learned something new.",
    473: "It was very good, thank you, I learned a lot!",
    474: "More concrete instructions.",
    475: "Well, we can help the community more.",
    476: "Asking the others whether they had questions.",
    477: "We can talk with people who need it.",
    479: "With a video for the visual.",
    480: "More opportunities to win a prize.",
    483: "Everything was fine; there was nothing to change.",
    484: "Everything went well and I learned from this training.",
    485: "Everything went very well; there was nothing to change.",
    486: "By holding events like this so other students know about this!",
    487: "We can improve this by helping others who need our help.",
    489: "We can improve this training in the future by continuing to support people.",
    490: "That they keep supporting people who need it, always.",
    491: "I have no complaints; everything seemed very well explained.",
    492: "I liked it a lot and I think it's fine as it is.",
    493: "I really think that by having hope in yourself. [incomplete in original]",
    494: "By advising or talking with people.",
    497: "Honestly, everything is fine, but one idea to improve would be to have an in-person 988 representative; it would be an improved function.",
    498: "Recommending it to friends and family.",
    499: "By using 988 more.",
    500: "Nothing. I liked the presentation and learned a lot.",
})

text_fixes = {
    "Fue excelente.": "It was excellent.",
    "Estubo bien.": "It was good.",
    "Informando desde temprana edad.": "Informing people from an early age.",
    "Ayudandonos entre amigos y familias de no caer en malos pasos.": "Helping each other, among friends and families, to avoid going down the wrong path.",
}

# ---------- themes: what participants found most valuable ----------
LEARNED_THEMES = {
    "When to call / what 988 is for": [
        "when to", "when you can", "when someone", "when i need", "when i feel",
        "when i have", "reasons", "what it is for", "what it was for",
        "what 988 is", "what 988 does", "what it does", "purpose",
        "what exactly", "how and when", "start with 988",
        "if there is a mental health",
        "used for", "when you should", "why you should", "how and why",
        "who can use", "in a crisis", "988 for help", "hurting yourself",
        "planning on", "when 988"],
    "Not just for suicide / any reason": [
        "not just", "not only", "isn't only", "isnt only", "isn't just",
        "isnt just", "is not just", "is not only", "not for suicide",
        "doesn't have to", "does not have to", "don't have", "dont have",
        "even if you're not", "even when not", "not suicidal", "just to talk",
        "anything", "any issue", "any problem", "any reason", "overwhelmed",
        "stress", "not in crisis", "not having a crisis", "for a lot of things",
        "variety", "many situations", "breadth", "bredth", "suicide may not be",
        "always call", "no matter", "immediate danger", "other than", "hesita",
        "different things", "doesn't matter", "does not matter", "all the stuff",
        "all your problems", "what situations", "different situations",
        "all situations", "not everybody", "not in active", "drug"],
    "911 vs 988": ["911"],
    "Availability (24/7, call/text)": [
        # removed "all the time": "I refer to students all the time" is not availability
        "24/7", "24 7", "available all the time", "available at all times",
        "any time", "anytime",
        "always available", "always open", "open all", "any day", "whenever",
        "text", "chat", "all times"],
    "Who can call / access": [
        # removed bare "everyone": "everyone experiences anxiety" is not about who can call
        "anyone", "any age", "all ages", "minor", "everyone can", "for everyone",
        "available to everyone", "everyone is welcome", "everyone has access",
        "all people",
        "anybody", "adults", "is free", "it is free", "its free", "no cost",
        "insurance", "personal id", "anywhere", "language", "asl", "spanish",
        "for friends", "for someone else", "for family", "for others",
        "open to all", "accessible", "any one", "all kinds of", "who can use"],
    "How to use / access 988": [
        "how to use", "how to access", "how to call", "how to contact",
        "how to reach", "how to connect", "how to text", "how i will be able",
        "use the number", "how and when", "trying it out", "try it out"],
    "Awareness that 988 / the resource exists": [
        "didn't know", "didnt know", "did not know", "never heard",
        "wasn't aware", "was not aware", "resource", "what 988 was",
        "what it was", "mental health line", "988 program", "988 exists",
        "i now know", "learning this", "understanding there is",
        "what the 988", "what 988 line"],
    "How the service works / what it offers": [
        "how it works", "how it worked", "how 988 works", "the way 988 works",
        "how the call", "how the process", "what happens", "what to expect",
        "what someone should expect", "when you call in", "process",
        "logistics", "caller", "call center", "counselor", "wait time",
        "confidential", "judg", "anonymous", "respectful", "trained",
        "connected", "range of services", "services", "expansive", "aspects",
        "different ways", "support services", "human", "priva", "real person",
        "daily", "team", "trust", "transfer", "comfort", "fake name",
        "your name", "nickname", "what they do", "during calls",
        "during a call", "line works", "try to find you", "push you",
        "boundaries", "consent"],
    "Helping others / spotting signs": [
        "help someone", "help others", "how to help", "signs", "warning",
        "loved one", "friend", "someone in", "observ", "empath",
        "attention", "recognize", "identify", "detect",
        "refer", "recommend", "how to talk", "talk to an individual",
        "explain to", "nervous", "individual in crisis", "check in", "my son",
        "my family", "communicat", "how someone", "what to do"],
    "Risk / protective factors / prevention": [
        # removed "to prevent": "To prevent suicide, call 988" is when-to-call
        "risk factor", "protective", "preventing"],
    "Help exists / not alone / okay to ask": [
        "not alone", "okay to", "ok to", "share your feelings", "ask for help",
        "seek help", "tell somebody", "tell someone", "reach out",
        "talk to someone", "talk with someone", "someone to talk", "stigma",
        "people who can help", "people who care", "people to help",
        "people who listen", "people out there", "can help us", "get help",
        "professional help", "someone can listen", "support for students",
        "hope", "care about", "caring", "matters",
        "here to help", "help is available", "help available", "need help",
        "speak up", "afraid", "always someone", "always people", "count on",
        "call for help", "support you", "helps you", "988 can help",
        "988 helps"],
    "LGBTQ+ support": ["lgbt", "trevor", "queer"],
    "Local info (EveryMind, Maryland)": [
        "everymind", "maryland", "montgomery", "county", "local", "state of",
        "warmline", "my location", "your area", "in my area"],
    "Funding / continued availability": [
        "funding", "climate", "cut ", "cuts", "federal"],
    "Statistics, data, effectiveness": [
        "statistic", "stats", "data", "rates", "how many", "research",
        "percent", "studies", "#1", "reason people call", "effective",
        "1 person", "1 death", "that 988 works", "reported", "self harm",
        "take their life"],
    "Training delivery": [
        "video", "story", "presenter", "trainer", "pace", "magnet", "slides",
        "activit", "game", "interactive", "pre and post", "donut", "snack",
        "explained", "presentation", "speaker", "website", "toolkit",
        "handout", "flyer", "socializing", "the room"],
    "General praise": [
        # "everything" must be the whole answer; "Everything can be a sign..." is not praise
        "=everything", "=every thing", "everything was", "everything is",
        "all of it was", "all the training",
        "amazing", "i loved", "loved it", "love the", "the information",
        "informative", "important information", "very important", "nice",
        "thank", "helpful", "interesting"],
    "988 is important / valuable": [
        "how important", "how useful", "save your life", "saves lives",
        "valuable place", "valuable resource", "valuable tool", "lifesaving"],
}


def tag_comment(text, themes, improve=False):
    """Multi-label keyword tagger. Keywords match at the start of a word;
    keywords starting with '=' must match the whole comment."""
    if pd.isna(text):
        return []
    t = str(text).lower().replace("’", "'")
    whole = re.sub(r"[^a-z0-9 ]", "", t).strip()
    found = []
    for theme, keywords in themes.items():
        for k in keywords:
            if k.startswith("="):
                hit = (whole == k[1:])
            else:
                hit = re.search(r"\b" + re.escape(k), t) is not None
            if hit:
                found.append(theme)
                break
    # "Nothing, I loved the food" is praise, not a logistics request
    if (improve and found and not set(found) <= QUIET
            and NO_CHANGE_OPENER.match(t) and not HAS_REQUEST_WORD.search(t)):
        return ["Positive / nothing to change"]
    if found:
        return found
    if len(re.findall(r"[a-z0-9]+", t)) <= 4:
        return ["Too brief to code"]
    return ["Other"]



# ---------- themes: what participants want improved ----------
QUIET = {"Positive / nothing to change", "No further questions / nothing to add"}
NO_CHANGE_OPENER = re.compile(r"^\s*(nothing|none|no|n/a)\b[\s,.:;!-]")
HAS_REQUEST_WORD = re.compile(
    r"\b(but|except|however|more|should|could|would|maybe|wish|need|want|add|bring|include)\b")

IMPROVE_THEMES = {
    "Positive / nothing to change": [
        "awesome", "excellent", "amazing", "perfect", "very complete",
        "was great", "were great", "is great", "great training", "was good",
        "very good", "so good", "all good", "it's good", "its good",
        "everything was", "everything went", "everything is", "went very well",
        "went well", "was fine", "no complaints", "nothing to improve",
        "nothing to change", "nothing needed", "nothing really", "no suggestions",
        "no changes", "not much to improve", "don't think there",
        "dont think there", "i don't think", "can't think", "cant think",
        "keep it up", "keep doing", "as it is", "as is", "just fine", "loved",
        "thank you for", "well explained", "well organized", "well put together",
        "was presented", "informative", "very helpful", "very well", "good job",
        "great job", "well done", "it was nice"],
    "No further questions / nothing to add": [
        "don't have any", "dont have any", "no questions", "all of my questions",
        "questions were covered", "answered everything", "i dont.", "i don't.",
        "nothing more", "not really sure", "not sure right now",
        "understand all", "everything i need"],
    "What calls are like / real stories": [
        "calls are like", "call is like", "what it's like", "what its like",
        "what happens during", "during calls", "during a call", "open up",
        "first call", "someone saved", "saved by", "received services",
        "real stor", "personal stor", "testimon", "lived experience",
        "people who have used", "bring someone", "example call",
        "listen to a call", "sample call", "call dialogue", "dialogue",
        "youth explaining", "their experience", "mobile crisis",
        "how the help is provided", "how do counselors", "how they can help",
        "how long does the call", "call take", "what to say"],
    "Privacy and confidentiality": [
        "phone bill", "see if you called", "recording", "recorded",
        "confidential", "private", "privacy", "anonymous", "who can see",
        "who sees", "tracked", "trace", "parents find", "tell my parents",
        "tell our parents", "police", "report threat", "report to",
        "reported to", "shared with", "know you in real life", "in real life",
        "in secrecy", "secrecy"],
    "Practical call questions (cost, countries, who answers)": [
        "a fee", "any fee", "cost", "countries", "canada", "mexico",
        "internet", "wifi", "young kids", "years old", "age limit",
        "number of times", "pick up", "picks up", "immediately", "wait",
        "who answers", "answers the phone", "answer my calls", "type of people",
        "certain person", "specific person", "specific counselor",
        "same counselor", "same person", "call back", "connect me",
        "everywhere", "be able to use", "can i call", "can you call",
        "can someone call", "allowed to call", "call for them",
        "call for someone", "how is it 24"],
    "Usage statistics (how many / how often)": [
        "how many", "how often do", "per day", "per year", "each year",
        "a day", "most callers", "has the most", "highest", "have been helped"],
    "988 history and how it operates": [
        "why is it called", "when was it", "was formed", "how 988 was made",
        "was created", "history", "founded", "who started", "who runs",
        "who funds", "funded by", "operat", "behind the scenes",
        "how it works in"],
    "Handling difficult situations / understanding crisis": [
        "what if", "what happens if", "what would happen", "what happens when",
        "what do i do", "what should i do", "refuse", "deescalat",
        "de-escalat", "ready to die", "disconnected", "power goes out",
        "why do people", "what motivates", "causes", "how to identify",
        "harming", "self-harm", "self harm", "suicidal", "how to safely",
        "how to handle", "how to respond", "not feel good", "how i would know",
        "how do you know", "know when someone", "how you can help",
        "explain 988", "troubled", "depression", "will they call 911"],
    "More depth / content / practice": [
        "more lessons", "more information", "more info", "further detail",
        "more detail", "more emphasis", "emphasis", "more topics",
        "more content", "go deeper", "deeper", "beyond just", "more examples",
        "give examples", "more scenarios", "difficult situation", "nationwide",
        "how to be better", "help my friends", "more resources", "additional",
        "what else", "other ways", "less suicide data"],
    "Interactive / hands-on activities": [
        "activit", "role play", "roleplay", "role-play", "game", "kahoot",
        "interactive", "hands-on", "hands on", "engage", "speak rather",
        "allow participants", "participation", "discussion", "and discuss",
        "breakout", "more practice", "practice with", "practice using",
        "scenario", "quiz", "poll", "more questions", "mock",
        "letting students"],
    "Length, pacing, and follow-up": [
        "too long", "too short", "longer", "more time", "length of time",
        "speed", "rushed", "too fast", "too slow", "not sufficient",
        "too much information", "not enough time", "shorter", "time limit",
        "extend", "more sessions", "follow-up", "follow up", "refresher",
        "pressed for time", "one hour", "an hour", "for time", "more than one"],
    "Logistics and setting (food, in-person, registration)": [
        "food", "snack", "lunch", "pizza", "drink", "registration",
        "in-person", "in person", "virtual", "online", "zoom", "assembly",
        "asembly", "prize", "schedule", "microphone", "audio", "seating",
        "tech issues", "technical"],
    "Visuals, video, and media": [
        "video", "visual", "illustration", "picture", "graphic",
        "social media", "tiktok", "instagram", "poster", "short clip",
        "30 sec", "font", "couldn't see", "couldnt see"],
    "Materials and take-aways (slides, notes, resources)": [
        "copy of", "slides", "handout", "ppt", "powerpoint", "brief note",
        "note should", "materials", "literature", "resource list",
        "take home", "take-home", "pamphlet", "brochure", "reference"],
    "Reach: more people, students, settings": [
        "more people", "everyone hears", "everyone knows", "more students",
        "all students", "all schools", "other schools", "schools in",
        "more families", "families", "parents", "more homes", "community",
        "spread", "share with", "sharing", "share it", "share the information",
        "informing", "giving the information", "telling others", "tell others",
        "to others", "with others", "awareness", "adding students",
        "students also", "include students", "students be",
        "be at the training", "teachers", "other classes", "get more people",
        "wider audience", "more audiences", "in spanish", "spanish",
        "other languages", "more languages", "word out", "promote", "advertis",
        "participate", "incorporate", "ra training", "other training",
        "how can more people"],
    "Local resources / relevance to the county": [
        "my county", "our county", "pg county", "prince george",
        "county resources", "local resources", "resources for our",
        "do not apply", "apply to us", "our area", "our community",
        "near us", "where we live"],
    "Careers: working at 988 / becoming a counselor": [
        "this job", "the job", "a job", "get a job", "become a counselor",
        "how to become", "how can you become", "how could you become",
        "qualif", "education", "degree", "volunteer", "internship", "hired",
        "hiring", "career", "mandated reporting", "work for", "work at",
        "salary"],
    "Specialized populations (LGBTQ+, etc.)": [
        # removed "disab": it matched "what mental disability has the highest attempted rate?"
        "lgbt", "queer", "transgender", "veteran", "deaf", "with disabilit",
        "disabled", "wheelchair", "autis",
        "neurodiver", "immigrant", "undocumented", "foster"],
    "Tailor to the audience": [
        "who is in the room", "who's in the room", "ask the group", "tailor",
        "age appropriate", "age-appropriate", "for kids", "for younger",
        "for older", "grade level", "relevant to us", "relevant to them",
        "know your audience", "different groups", "each group"],
}


def add_kw(themes, theme, words):
    themes[theme] = themes.get(theme, []) + words


def drop_kw(themes, theme, words):
    themes[theme] = [k for k in themes[theme] if k not in words]


T = IMPROVE_THEMES

drop_kw(T, "Reach: more people, students, settings",
        ["in spanish", "spanish", "other languages", "more languages"])

T["Language access / translation"] = [
    "translator", "traslator", "interpret", "translat", "their language",
    "in spanish", "spanish", "other languages", "more languages", "bilingual"]

T["Answered about helping others / self (not the training)"] = [
    "helping others", "help others", "support people", "supporting people",
    "keep supporting", "talk with people", "talking with people", "advising",
    "need our help", "who need it", "someone to talk to", "asking for help",
    "improve your mental health", "in tune", "i feel bad", "help a friend",
    "helpa friend", "being better at it", "calling 988 if necessary",
    "being listened to"]

add_kw(T, "Positive / nothing to change", [
    "=great", "=good", "=fine", "=ok", "=okay", "=nice",
    "it's great", "its great", "great presentation", "doing well", "doing great",
    "did really good", "did great", "10/10", "i liked", "learned a lot",
    "already good", "already great", "good enough", "no need", "no improve",
    "nothing should", "nothing improve", "it's fine", "its fine", "fine how",
    "dont need", "don't need", "very organized", "was organized"])

add_kw(T, "No further questions / nothing to add", [
    "don't have questions", "dont have questions", "no further", "nothing else",
    "no thank", "none at", "no notes", "no idea", "not sure", "unsure",
    "every thing i need", "everything that i need", "know everything", "no more",
    "i understand"])

add_kw(T, "What calls are like / real stories", ["real example"])

add_kw(T, "Practical call questions (cost, countries, who answers)", [
    "if i can call", "if you can call", "how to call", "how to text", "method",
    "world wide", "worldwide", "world-wide"])

add_kw(T, "Usage statistics (how many / how often)", [
    "how often", "where do most", "most suicides",
    "how effective", "is this helping", "does it work"])

add_kw(T, "988 history and how it operates", [
    "warmline", "difference between", "influence", "organization of", "trevor",
    "how it started", "how did this", "how it began", "fully works",
    "how did 988", "how 988 start"])

add_kw(T, "More depth / content / practice", [
    "learn more", "learning more", "want to learn", "like to learn",
    "want to know", "like to know", "more about", "about more", "more suicide",
    "into detail", "concrete", "instructions", "including examples",
    "examples on", "examples of",
    "real life", "real-life", "more mental health", "how it works",
    "how 988 works", "when to use", "when to call", "when to reach out"])

add_kw(T, "Interactive / hands-on activities", [
    "engag", "interaction", "participating", "more fun", "make it fun",
    "making it fun", "something to do", "each other", "eachother",
    "into practice", "asking the others", "ask the others"])

add_kw(T, "Length, pacing, and follow-up", [
    "time management", "more classes", "breath", "heavy topic", "a break", "breaks"])

add_kw(T, "Visuals, video, and media", ["enlarge", "the print", "image"])

add_kw(T, "Reach: more people, students, settings", [
    "events like", "recommend it", "recommending it", "friends and family",
    "flier", "flyer", "notice", "email", "broadcast", "brodcast", "news",
    "young people", "get access", "let people know", "let others know"])

add_kw(T, "Careers: working at 988 / becoming a counselor", [
    "counselors trained", "counselor training"])


# Only treat as a question when it has a "?" or opens with a question word
# ("What I liked was..." is a statement, not a question)
QUESTION_STARTS = ("how ", "what ", "why ", "when ", "who ", "where ", "can ")
STATEMENT_OPENER = re.compile(r"^(what|how) (i|we|a|much i)\b")


def comment_type(text, themes):
    if pd.isna(text):
        return None
    t = str(text).strip().lower()
    quiet = set(themes) <= QUIET
    if "?" in t or (t.startswith(QUESTION_STARTS) and not STATEMENT_OPENER.match(t) and not quiet):
        return "Question / information request"
    if quiet:
        return "Positive / nothing to add"
    if set(themes) <= {"Other", "Too brief to code",
                       "Answered about helping others / self (not the training)"}:
        return "Unclear / other"
    return "Suggestion / request"




# ---------- reusable analysis (safe to import; no workbook is read) ----------
def analyze_feedback(clean_df: pd.DataFrame) -> dict:
    """Tag the currently selected survey responses.

    Expects Person 1's cleaned column names. Returns aggregate theme counts
    plus redacted, tagged rows for private in-app exploration. No file I/O.
    """
    required = {"id", "valuable_feedback", "improvement_feedback"}
    missing = required - set(clean_df.columns)
    if missing:
        raise ValueError("Missing required survey columns: " + ", ".join(sorted(missing)))
    df = clean_df.copy(deep=True)
    df["learned"] = df["valuable_feedback"]
    df["improve"] = df["improvement_feedback"]
    df["county"] = df.get("county", pd.Series(index=df.index, dtype=object))
    df["role"] = df.get("participant_type", pd.Series(index=df.index, dtype=object))

    # The original translations are keyed to IDs from the source workbook.
    # Do not apply them to an unrelated upload that happens to reuse IDs.
    # Translation lookup is opt-in and should be validated against source text.
    # ---------- create the cleaned columns (BEFORE anything uses them) ----------
    df["learned_clean"] = df["learned"].apply(clean_comment)
    df["improve_clean"] = df["improve"].apply(clean_comment)
    df["county_clean"] = df["county"].apply(clean_county)
    df["role_clean"] = df["role"].apply(clean_role)
    
    # explicit "none / nothing / n/a" answers: dropped from commenter counts above,
    # but kept here so "nothing to change" can be reported separately
    df["improve_explicit_none"] = df["improve"].notna() & df["improve_clean"].isna()

    df["learned_en"] = df["learned_clean"]
    df["improve_en"] = df["improve_clean"]

    df["improve_en"] = df["improve_en"].replace(text_fixes)
    
    # Redact names BEFORE tagging or printing anything (previously done at the end)
    df["learned_en"] = df["learned_en"].apply(redact)
    df["improve_en"] = df["improve_en"].apply(redact)

    df["learned_themes"] = df["learned_en"].apply(lambda x: tag_comment(x, LEARNED_THEMES))

    df["improve_themes"] = df["improve_en"].apply(lambda x: tag_comment(x, IMPROVE_THEMES, improve=True))

    df["improve_type"] = [comment_type(t, th) for t, th in zip(df["improve_en"], df["improve_themes"])]
    return {
        "data": df,
        "learned_counts": df["learned_themes"].explode().value_counts(),
        "improve_counts": df["improve_themes"].explode().value_counts(),
        "improve_type_counts": df["improve_type"].value_counts(),
    }


if __name__ == "__main__":
    from pathlib import Path
    from cleaning import clean_survey

    workbook = Path(__file__).resolve().parent / "survey_data.xlsx"
    if not workbook.is_file():
        raise SystemExit("No local survey_data.xlsx found. Use the dashboard upload instead.")
    raw = pd.read_excel(workbook)
    cleaned, _ = clean_survey(raw)
    result = analyze_feedback(cleaned)
    print("===== WHAT PARTICIPANTS VALUED =====")
    print(result["learned_counts"].to_string())
    print("\n===== WHAT PARTICIPANTS WANT IMPROVED =====")
    print(result["improve_counts"].to_string())
    print("\n===== COMMENT TYPES =====")
    print(result["improve_type_counts"].to_string())
