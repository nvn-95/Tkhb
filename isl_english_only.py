"""
ISL Gloss Pipeline — English Only
==================================
English → ISL Gloss → BVH

Usage:
    python isl_english_only.py                        → mic input
    python isl_english_only.py --text "I like food"   → text input
    python isl_english_only.py --test                 → self-tests (no mic)

Install:
    pip install SpeechRecognition pyaudio
"""

import re
import json
import sys
import argparse

# ================================================================
# CONFIG
# ================================================================
BVH_FOLDER = "C:/ISL_Avatar_Project/bvh_signs/"

BVH_MAP = {
    # Pronouns
    "I":"i.bvh",           "YOU":"you.bvh",        "HE":"he.bvh",
    "SHE":"she.bvh",       "WE":"we.bvh",          "THEY":"they.bvh",
    "IT":"it.bvh",
    # Nouns
    "FOOD":"food.bvh",     "WATER":"water.bvh",    "SCHOOL":"school.bvh",
    "HOME":"home.bvh",     "NAME":"name.bvh",      "BOOK":"book.bvh",
    "MONEY":"money.bvh",   "WORK":"work.bvh",      "TIME":"time.bvh",
    "PLACE":"place.bvh",   "FAMILY":"family.bvh",  "FRIEND":"friend.bvh",
    "DOCTOR":"doctor.bvh", "HOSPITAL":"hospital.bvh","HOUSE":"house.bvh",
    "RICE":"rice.bvh",     "MOTHER":"mother.bvh",  "FATHER":"father.bvh",
    "CHILD":"child.bvh",   "CAR":"car.bvh",        "PHONE":"phone.bvh",
    "MARKET":"market.bvh", "CLOTHES":"clothes.bvh","TEACHER":"teacher.bvh",
    "STUDENT":"student.bvh","TEMPLE":"temple.bvh", "CHURCH":"church.bvh",
    "SHOP":"shop.bvh",     "ROAD":"road.bvh",      "VILLAGE":"village.bvh",
    "FISH":"fish.bvh",     "VEGETABLE":"vegetable.bvh","FRUIT":"fruit.bvh",
    "MAN":"man.bvh",       "WOMAN":"woman.bvh",    "BOY":"boy.bvh",
    "GIRL":"girl.bvh",     "GOD":"god.bvh",        "RAIN":"rain.bvh",
    "CITY":"city.bvh",
    # Verbs
    "LIKE":"like.bvh",     "GO":"go.bvh",          "COME":"come.bvh",
    "EAT":"eat.bvh",       "DRINK":"drink.bvh",    "WANT":"want.bvh",
    "NEED":"need.bvh",     "HAVE":"have.bvh",      "KNOW":"know.bvh",
    "THINK":"think.bvh",   "HELP":"help.bvh",      "SEE":"see.bvh",
    "UNDERSTAND":"understand.bvh","LEARN":"learn.bvh","STUDY":"study.bvh",
    "PLAY":"play.bvh",     "MEET":"meet.bvh",      "GIVE":"give.bvh",
    "TAKE":"take.bvh",     "SLEEP":"sleep.bvh",    "SPEAK":"speak.bvh",
    "WRITE":"write.bvh",   "READ":"read.bvh",      "COOK":"cook.bvh",
    "BUY":"buy.bvh",       "SELL":"sell.bvh",      "CALL":"call.bvh",
    "WAIT":"wait.bvh",     "LIVE":"live.bvh",      "FORGET":"forget.bvh",
    "LOVE":"love.bvh",     "PRAY":"pray.bvh",      "WALK":"walk.bvh",
    "RUN":"run.bvh",       "SIT":"sit.bvh",        "STAND":"stand.bvh",
    "OPEN":"open.bvh",     "CLOSE":"close.bvh",    "WASH":"wash.bvh",
    "HEAR":"hear.bvh",     "FEEL":"feel.bvh",      "REMEMBER":"remember.bvh",
    "FINISH":"finish.bvh", "START":"start.bvh",    "TELL":"tell.bvh",
    "ASK":"ask.bvh",
    # Custom Signs from User Videos
    "QUIET":"quiet.bvh",   "HAPPY":"happy.bvh",    "SAD":"sad.bvh",
    "BEAUTIFUL":"beautiful.bvh","UGLY":"ugly.bvh", "DEAF":"deaf.bvh",
    "BLIND":"blind.bvh",

    # Adjectives
    "GOOD":"good.bvh",     "BAD":"bad.bvh",        "BIG":"big.bvh",
    "SMALL":"small.bvh",   "HAPPY":"happy.bvh",    "SAD":"sad.bvh",
    "SICK":"sick.bvh",     "TIRED":"tired.bvh",    "HUNGRY":"hungry.bvh",
    "THIRSTY":"thirsty.bvh","BUSY":"busy.bvh",     "LATE":"late.bvh",
    "EARLY":"early.bvh",   "HOT":"hot.bvh",        "COLD":"cold.bvh",
    "NICE":"nice.bvh",     "BEAUTIFUL":"beautiful.bvh","OLD":"old.bvh",
    "NEW":"new.bvh",       "FAST":"fast.bvh",      "SLOW":"slow.bvh",
    "DIFFICULT":"difficult.bvh","EASY":"easy.bvh", "TALL":"tall.bvh",
    "SHORT":"short.bvh",   "RICH":"rich.bvh",      "POOR":"poor.bvh",
    "YOUNG":"young.bvh",   "CLEAN":"clean.bvh",    "DIRTY":"dirty.bvh",
    "STRONG":"strong.bvh", "WEAK":"weak.bvh",      "ANGRY":"angry.bvh",
    "SCARED":"scared.bvh", "IMPORTANT":"important.bvh",
    # Time markers
    "TODAY":"today.bvh",   "TOMORROW":"tomorrow.bvh","YESTERDAY":"yesterday.bvh",
    "NOW":"now.bvh",       "LATER":"later.bvh",    "MORNING":"morning.bvh",
    "EVENING":"evening.bvh","NIGHT":"night.bvh",   "ALWAYS":"always.bvh",
    "SOMETIMES":"sometimes.bvh","NEVER":"never.bvh","SOON":"soon.bvh",
    "ALREADY":"already.bvh","DAILY":"daily.bvh",   "WEEKLY":"weekly.bvh",
    "AGAIN":"again.bvh",
    # Negation
    "NO":"no.bvh",         "NOT":"not.bvh",
    # WH-words
    "WHAT":"what.bvh",     "WHERE":"where.bvh",    "WHO":"who.bvh",
    "WHEN":"when.bvh",     "WHY":"why.bvh",        "HOW":"how.bvh",
    "HOW_MUCH":"how_much.bvh","HOW_MANY":"how_many.bvh",
}

# ================================================================
# ENGLISH LEXICON
# ================================================================
PRONOUNS = {
    "I","YOU","HE","SHE","WE","THEY","IT",
    "ME","HIM","HER","US","THEM","MY","YOUR",
    "HIS","THEIR","OUR","MINE","YOURS","HERS","OURS"
}
PRONOUN_NORMALIZE = {
    "ME":"I",   "MY":"I",    "MINE":"I",
    "HIM":"HE", "HIS":"HE",
    "HER":"SHE","HERS":"SHE",
    "US":"WE",  "OUR":"WE",  "OURS":"WE",
    "THEM":"THEY","THEIR":"THEY","THEIRS":"THEY",
    "YOUR":"YOU","YOURS":"YOU",
}

VERBS = {
    "LIKE","GO","COME","EAT","DRINK","WANT","NEED","HAVE","KNOW",
    "THINK","HELP","SEE","UNDERSTAND","LEARN","STUDY","PLAY","WORK",
    "MEET","GIVE","TAKE","SLEEP","SPEAK","WRITE","READ","COOK",
    "BUY","SELL","CALL","WAIT","LIVE","FORGET","LOVE","PRAY",
    "WALK","RUN","SIT","STAND","OPEN","CLOSE","WASH","HEAR",
    "FEEL","REMEMBER","FINISH","START","TELL","ASK",
    # conjugations
    "GOING","GOES","WENT",
    "EATING","ATE","EATS",
    "LIKING","LIKED","LIKES",
    "DRINKING","DRANK","DRINKS",
    "WANTING","WANTS","WANTED",
    "KNOWING","KNEW","KNOWS",
    "THINKING","THOUGHT","THINKS",
    "HELPING","HELPED","HELPS",
    "SEEING","SAW","SEES",
    "COMING","CAME","COMES",
    "GIVING","GAVE","GIVES",
    "TAKING","TOOK","TAKES",
    "SLEEPING","SLEPT","SLEEPS",
    "SPEAKING","SPOKE","SPEAKS",
    "WRITING","WROTE","WRITES",
    "READING","READS",
    "COOKING","COOKED","COOKS",
    "BUYING","BOUGHT","BUYS",
    "WORKING","WORKED","WORKS",
    "LOVING","LOVED","LOVES",
    "WALKING","WALKED","WALKS",
    "RUNNING","RAN","RUNS",
    "SITTING","SAT","SITS",
    "STANDING","STOOD","STANDS",
    "WASHING","WASHED","WASHES",
    "HEARING","HEARD","HEARS",
    "FEELING","FELT","FEELS",
    "REMEMBERING","REMEMBERED","REMEMBERS",
    "FINISHING","FINISHED","FINISHES",
    "STARTING","STARTED","STARTS",
    "TELLING","TOLD","TELLS",
    "ASKING","ASKED","ASKS",
    "MEETING","MET","MEETS",
    "PLAYING","PLAYED","PLAYS",
    "STUDYING","STUDIED","STUDIES",
    "LEARNING","LEARNED","LEARNS",
    "PRAYING","PRAYED","PRAYS",
    "SELLING","SOLD","SELLS",
    "CALLING","CALLED","CALLS",
    "WAITING","WAITED","WAITS",
    # HAS/HAD/HAVING — HAVE conjugations
    "HAS","HAD","HAVING",
}

VERB_NORMALIZE = {
    "GOING":"GO","GOES":"GO","WENT":"GO",
    "EATING":"EAT","ATE":"EAT","EATS":"EAT",
    "LIKING":"LIKE","LIKED":"LIKE","LIKES":"LIKE",
    "DRINKING":"DRINK","DRANK":"DRINK","DRINKS":"DRINK",
    "WANTING":"WANT","WANTS":"WANT","WANTED":"WANT",
    "KNOWING":"KNOW","KNEW":"KNOW","KNOWS":"KNOW",
    "THINKING":"THINK","THOUGHT":"THINK","THINKS":"THINK",
    "HELPING":"HELP","HELPED":"HELP","HELPS":"HELP",
    "SEEING":"SEE","SAW":"SEE","SEES":"SEE",
    "COMING":"COME","CAME":"COME","COMES":"COME",
    "GIVING":"GIVE","GAVE":"GIVE","GIVES":"GIVE",
    "TAKING":"TAKE","TOOK":"TAKE","TAKES":"TAKE",
    "SLEEPING":"SLEEP","SLEPT":"SLEEP","SLEEPS":"SLEEP",
    "SPEAKING":"SPEAK","SPOKE":"SPEAK","SPEAKS":"SPEAK",
    "WRITING":"WRITE","WROTE":"WRITE","WRITES":"WRITE",
    "READING":"READ","READS":"READ",
    "COOKING":"COOK","COOKED":"COOK","COOKS":"COOK",
    "BUYING":"BUY","BOUGHT":"BUY","BUYS":"BUY",
    "WORKING":"WORK","WORKED":"WORK","WORKS":"WORK",
    "LOVING":"LOVE","LOVED":"LOVE","LOVES":"LOVE",
    "WALKING":"WALK","WALKED":"WALK","WALKS":"WALK",
    "RUNNING":"RUN","RAN":"RUN","RUNS":"RUN",
    "SITTING":"SIT","SAT":"SIT","SITS":"SIT",
    "STANDING":"STAND","STOOD":"STAND","STANDS":"STAND",
    "WASHING":"WASH","WASHED":"WASH","WASHES":"WASH",
    "HEARING":"HEAR","HEARD":"HEAR","HEARS":"HEAR",
    "FEELING":"FEEL","FELT":"FEEL","FEELS":"FEEL",
    "REMEMBERING":"REMEMBER","REMEMBERED":"REMEMBER","REMEMBERS":"REMEMBER",
    "FINISHING":"FINISH","FINISHED":"FINISH","FINISHES":"FINISH",
    "STARTING":"START","STARTED":"START","STARTS":"START",
    "TELLING":"TELL","TOLD":"TELL","TELLS":"TELL",
    "ASKING":"ASK","ASKED":"ASK","ASKS":"ASK",
    "MEETING":"MEET","MET":"MEET","MEETS":"MEET",
    "PLAYING":"PLAY","PLAYED":"PLAY","PLAYS":"PLAY",
    "STUDYING":"STUDY","STUDIED":"STUDY","STUDIES":"STUDY",
    "LEARNING":"LEARN","LEARNED":"LEARN","LEARNS":"LEARN",
    "PRAYING":"PRAY","PRAYED":"PRAY","PRAYS":"PRAY",
    "SELLING":"SELL","SOLD":"SELL","SELLS":"SELL",
    "CALLING":"CALL","CALLED":"CALL","CALLS":"CALL",
    "WAITING":"WAIT","WAITED":"WAIT","WAITS":"WAIT",
    # HAS/HAD/HAVING → HAVE
    "HAS":"HAVE","HAD":"HAVE","HAVING":"HAVE",
}

# Modal/auxiliary verbs — when preceding a main verb, they are dropped.
# ISL uses only the final/main content verb.
MODAL_VERBS = {
    "WANT","NEED","LIKE","GOING",
}

NOUNS = {
    "FOOD","WATER","SCHOOL","HOME","NAME","BOOK","MONEY","WORK","TIME",
    "PLACE","FAMILY","FRIEND","DOCTOR","HOSPITAL","HOUSE","RICE","MOTHER",
    "FATHER","CHILD","CAR","PHONE","MARKET","CLOTHES","TEACHER","STUDENT",
    "TEMPLE","CHURCH","SHOP","ROAD","VILLAGE","FISH","VEGETABLE","FRUIT",
    "MAN","WOMAN","BOY","GIRL","GOD","RAIN","CITY",
}

ADJECTIVES = {
    "GOOD","BAD","BIG","SMALL","HAPPY","SAD","SICK","TIRED","HUNGRY",
    "THIRSTY","BUSY","LATE","EARLY","HOT","COLD","NICE","BEAUTIFUL",
    "OLD","NEW","FAST","SLOW","DIFFICULT","EASY","TALL","SHORT","RICH",
    "POOR","YOUNG","CLEAN","DIRTY","STRONG","WEAK","ANGRY","SCARED","IMPORTANT",
    "QUIET","UGLY","DEAF","BLIND",
}

TIME_MARKERS = {
    "TODAY","TOMORROW","YESTERDAY","NOW","LATER","MORNING","EVENING","NIGHT",
    "ALWAYS","SOMETIMES","NEVER","SOON","ALREADY","DAILY","WEEKLY","AGAIN",
}

WH_WORDS  = {"WHAT","WHERE","WHO","WHEN","WHY","HOW"}
NEG_WORDS = {"NOT","NO","NEVER","NOTHING","NOBODY","NOWHERE"}

NEG_CONTRACTIONS = {
    "DONT":"NO",    "DON'T":"NO",
    "DOESN'T":"NO", "DOESNT":"NO",
    "DIDN'T":"NO",  "DIDNT":"NO",
    "WON'T":"NO",   "WONT":"NO",
    "CAN'T":"NO",   "CANT":"NO",   "CANNOT":"NO",
    "ISN'T":"NO",   "ISNT":"NO",
    "AREN'T":"NO",  "ARENT":"NO",
    "WASN'T":"NO",  "WASNT":"NO",
    "WEREN'T":"NO", "WERENT":"NO",
    "HAVEN'T":"NO", "HAVENT":"NO",
    "HASN'T":"NO",  "HASNT":"NO",
    "HADN'T":"NO",  "HADNT":"NO",
    "SHOULDN'T":"NO","SHOULDNT":"NO",
    "COULDN'T":"NO","COULDNT":"NO",
    "WOULDN'T":"NO","WOULDNT":"NO",
    "MUSTN'T":"NO", "MUSTNT":"NO",
    "NEEDN'T":"NO", "NEEDNT":"NO",
}

STOP_WORDS = {
    "AM","IS","ARE","WAS","WERE","BE","BEEN","BEING",
    "THE","A","AN","TO","OF","IN","ON","AT","BY","FOR","WITH",
    "THAT","THIS","THESE","THOSE","AND","BUT","OR","SO",
    "VERY","JUST","REALLY","PLEASE","ALSO","DO","DOES","DID",
    "WILL","WOULD","COULD","SHOULD","SHALL","MAY","MIGHT","MUST",
    "UP","DOWN","OUT","ABOUT","OVER","AFTER","BEFORE","THEN",
    "FROM","INTO","ONTO","THROUGH","DURING","UNTIL","SOME","ANY",
    "GOING",
}

# ================================================================
# VOICE TO TEXT
# ================================================================
def _best_microphone_index():
    try:
        import speech_recognition as sr
        names = sr.Microphone.list_microphone_names()
        skip = {"virtual", "loopback", "stereo mix", "wave out", "what u hear"}
        for i, name in enumerate(names):
            if not any(s in name.lower() for s in skip):
                print(f"[MIC] Using mic [{i}]: {name}")
                return i
    except Exception:
        pass
    return None


def _capture_audio():
    try:
        import speech_recognition as sr
    except ImportError:
        print("❌  SpeechRecognition not installed.")
        print("    Run:  pip install SpeechRecognition pyaudio")
        return None

    mic_index = _best_microphone_index()
    r = sr.Recognizer()
    r.energy_threshold         = 200
    r.dynamic_energy_threshold = True
    r.pause_threshold          = 1.0

    for attempt in range(1, 4):
        print(f"\n[MIC] [{attempt}/3] Speak in English (waiting up to 10s)...")
        try:
            mic_kwargs = {} if mic_index is None else {"device_index": mic_index}
            with sr.Microphone(**mic_kwargs) as source:
                calibrate_secs = 1.5 if attempt == 1 else 0.5
                print(f"    [WAIT] Calibrating microphone ({calibrate_secs}s)…")
                r.adjust_for_ambient_noise(source, duration=calibrate_secs)
                print("    [OK] Ready — speak now!")
                audio = r.listen(source, timeout=10, phrase_time_limit=15)
            return audio
        except sr.WaitTimeoutError:
            print(f"    [WARN] No speech heard (attempt {attempt}/3).")
        except OSError as e:
            print(f"    ⚠️  Microphone error: {e}")
            break

    print("[ERROR] Could not capture audio after 3 attempts.")
    return None


def voice_to_text():
    try:
        import speech_recognition as sr
    except ImportError:
        print("[ERROR] SpeechRecognition not installed.")
        return ""

    audio = _capture_audio()
    if audio is None:
        return ""

    r = sr.Recognizer()
    try:
        text = r.recognize_google(audio, language="en-IN")
        print(f"[TEXT] Recognized: {text}")
        return text
    except sr.UnknownValueError:
        print("[WARN] Speech heard but could not be understood.")
        print("    Tips: speak clearly, closer to mic, reduce background noise.")
        return ""
    except sr.RequestError as e:
        print(f"[WARN] Google STT API error: {e}")
        print("    Check your internet connection.")
        return ""


# ================================================================
# ISL GLOSS ENGINE
# ================================================================
def normalize_word(word):
    """Returns (category_hint, normalized_form)."""
    if word in NEG_CONTRACTIONS:  return ("NEG",     NEG_CONTRACTIONS[word])
    if word in VERB_NORMALIZE:    return ("VERB",    VERB_NORMALIZE[word])
    if word in PRONOUN_NORMALIZE: return ("PRONOUN", PRONOUN_NORMALIZE[word])
    return (None, word)


def classify_word(word):
    """Classify an uppercase word into its ISL grammatical role."""
    hint, norm = normalize_word(word)
    if hint in ("NEG", "VERB", "PRONOUN"):
        return (hint, norm)
    w = norm
    if w in STOP_WORDS:    return ("STOP",      w)
    if w in NEG_WORDS:     return ("NEG",       "NO")
    if w in TIME_MARKERS:  return ("TIME",      w)
    if w in WH_WORDS:      return ("WH",        w)
    if w in PRONOUNS:      return ("PRONOUN",   w)
    if w in VERBS:         return ("VERB",      w)
    if w in NOUNS:         return ("NOUN",      w)
    if w in ADJECTIVES:    return ("ADJECTIVE", w)
    return ("UNKNOWN", w)


def text_to_gloss(english_text):
    """
    Converts English text to ISL Gloss using 8 grammar rules:
      Rule 1 — TIME FIRST      : time markers → sentence start
      Rule 2 — SOV ORDER       : Subject → Object → Verb
      Rule 3 — NEG BEFORE VERB : NO placed just before verb
                                  (before adjective when no verb present)
      Rule 4 — WH WORDS LAST   : WH question word → sentence end
      Rule 5 — DROP AUXILIARIES: is/are/do/will/did removed
      Rule 6 — ADJ AFTER NOUN  : adjective follows its noun
      Rule 7 — DROP STOP WORDS : articles/prepositions removed
      Rule 8 — KEEP MAIN VERB  : when multiple verbs appear (e.g. "want to go"),
                                  keep only the final/main content verb
    """
    if not english_text.strip():
        return []

    # Tokenize — keep apostrophes so DON'T stays intact
    words = re.findall(r"[A-Z']+", english_text.upper())
    if not words:
        return []

    classified = []
    for w in words:
        cat, norm = classify_word(w)
        if cat != "STOP":
            classified.append((cat, norm))

    # ── Slot accumulators ──────────────────────────────────────────
    time_slot       = []
    subject_slot    = []
    noun_adj_pairs  = []
    adj_standalone  = []
    verb_slot       = []
    neg_slot        = []
    wh_slot         = []
    last_noun_group = None
    pending_adjs    = []   # pre-noun adjectives held until noun appears

    for cat, norm in classified:
        if cat == "TIME":
            time_slot.append(norm)

        elif cat == "PRONOUN":
            subject_slot.append(norm)

        elif cat in ("NOUN", "UNKNOWN"):
            if last_noun_group is not None:
                noun_adj_pairs.append(last_noun_group)
            last_noun_group = [norm] + pending_adjs
            pending_adjs = []

        elif cat == "ADJECTIVE":
            if last_noun_group is not None:
                last_noun_group.append(norm)
            else:
                pending_adjs.append(norm)

        elif cat == "VERB":
            verb_slot.append(norm)

        elif cat == "NEG":
            neg_slot.append("NO")

        elif cat == "WH":
            wh_slot.append(norm)

    if last_noun_group is not None:
        noun_adj_pairs.append(last_noun_group)

    adj_standalone.extend(pending_adjs)

    # Rule 8 — "want to go", "need to eat": keep only the final/main verb
    if len(verb_slot) >= 2:
        verb_slot = [verb_slot[-1]]

    # Flatten noun+adj pairs
    noun_seq = [t for group in noun_adj_pairs for t in group]

    # Rule 3 — NEG placement:
    #   • If there IS a verb  → NEG just before verb  (SOV + NEG + V)
    #   • If NO verb          → NEG just before standalone adjective
    if neg_slot:
        if verb_slot:
            gloss = time_slot + subject_slot + noun_seq + adj_standalone + neg_slot + verb_slot + wh_slot
        elif adj_standalone:
            # e.g. "I am not hungry" → I NO HUNGRY
            gloss = time_slot + subject_slot + noun_seq + neg_slot + adj_standalone + wh_slot
        else:
            # e.g. "He is not a good doctor" → HE DOCTOR GOOD NO
            gloss = time_slot + subject_slot + noun_seq + neg_slot + wh_slot
    else:
        gloss = time_slot + subject_slot + noun_seq + adj_standalone + verb_slot + wh_slot

    # Remove adjacent duplicates
    deduped = []
    for t in gloss:
        if not deduped or deduped[-1] != t:
            deduped.append(t)

    print(f"[GLOSS] ISL Gloss  : {deduped}")
    return deduped


def gloss_to_bvh(gloss):
    bvh_list, missing = [], []
    for token in gloss:
        if token in BVH_MAP:
            bvh_list.append(BVH_FOLDER + BVH_MAP[token])
        else:
            missing.append(token)
    if missing:
        print(f"  [WARN] No BVH for: {missing}")
    print(f"[FILES] BVH Files  : {bvh_list}")
    return bvh_list


# ================================================================
# MAIN PIPELINE
# ================================================================
def run_pipeline(input_text):
    print("\n" + "━"*55)
    print(f"  INPUT  : {input_text}")
    print("━"*55)

    print(f"[ENG] English   : {input_text}")

    gloss     = text_to_gloss(input_text)
    bvh_files = gloss_to_bvh(gloss)

    output = {
        "original_text": input_text,
        "isl_gloss":     gloss,
        "bvh_sequence":  bvh_files,
    }

    with open("bvh_sequence.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n[OK] Saved → bvh_sequence.json")
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return output


# ================================================================
# SELF-TESTS
# ================================================================
def run_tests():
    tests = [
        ("I like food",                     "I FOOD LIKE"),
        ("I don't like food",               "I FOOD NO LIKE"),
        ("Where are you going?",            "YOU GO WHERE"),
        ("Do you like food?",               "YOU FOOD LIKE"),
        ("I will eat food tomorrow",        "TOMORROW I FOOD EAT"),
        ("She is sick",                     "SHE SICK"),
        ("I want to go home",               "I HOME GO"),
        ("He has a big book",               "HE BOOK BIG HAVE"),
        ("Today I eat food",                "TODAY I FOOD EAT"),
        ("What do you want?",               "YOU WANT WHAT"),
        ("Who are you?",                    "YOU WHO"),
        ("I don't want to go to school",    "I SCHOOL NO GO"),
        ("I am not hungry",                 "I NO HUNGRY"),
        ("She is a good teacher",           "SHE TEACHER GOOD"),
        ("I need water now",                "NOW I WATER NEED"),
        ("We are happy",                    "WE HAPPY"),
        ("My mother is sick",               "I MOTHER SICK"),
        ("Give me water please",            "I WATER GIVE"),
        ("I can't go to school today",      "TODAY I SCHOOL NO GO"),
        ("He is not a good doctor",         "HE DOCTOR GOOD NO"),
        ("I need to eat food",              "I FOOD EAT"),
        ("She wants to drink water",        "SHE WATER DRINK"),
        ("I like to study",                 "I STUDY"),
        ("He had a big book",               "HE BOOK BIG HAVE"),
    ]

    print("\n" + "="*65)
    print("    ENGLISH GLOSS TESTS")
    print("="*65)
    pass_count = 0
    for sentence, expected in tests:
        gloss  = text_to_gloss(sentence)
        result = " ".join(gloss)
        ok     = result == expected
        if ok:
            pass_count += 1
        icon = "[PASS]" if ok else "[FAIL]"
        print(f"\n{icon} IN : {sentence}")
        if not ok:
            print(f"   EXP: {expected}")
            print(f"   GOT: {result}")
        else:
            print(f"   OUT: {result}")

    print(f"\n{'='*65}")
    print(f"  RESULT: {pass_count}/{len(tests)} passed")
    print("="*65 + "\n")


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ISL Gloss Pipeline — English Only")
    parser.add_argument("--text", type=str, default=None, help="Input English sentence")
    parser.add_argument("--test", action="store_true",    help="Run self-tests (no mic)")
    args = parser.parse_args()

    if args.test:
        run_tests()
        sys.exit(0)

    input_text = ""

    # ── 1. Text passed directly via --text ────────────────────────
    if args.text:
        input_text = args.text.strip()

    # ── 2. Microphone input ───────────────────────────────────────
    else:
        input_text = voice_to_text()

    # ── 3. Mic failed → ask user to type instead ──────────────────
    if not input_text:
        print("\n[WARN] Microphone input failed or produced no result.")
        print("─" * 50)
        try:
            typed = input("[TYPE] Type your English sentence here (or press Enter to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            typed = ""

        if typed:
            input_text = typed
        else:
            print("[INFO] No input provided. Exiting.")
            sys.exit(0)

    # ── 4. Run the pipeline ───────────────────────────────────────
    run_pipeline(input_text)
