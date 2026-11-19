# 🎧 Model Card: VibeFinder Agent

> Final-project model card. It covers the extended **VibeFinder Agent**
> system and includes my graded responsible-AI reflection (Section 10):
> how I collaborated with AI, one suggestion I accepted and one I revised,
> the system's biases, and its limitations.

---

## 1. Model Name

**VibeFinder Agent** — a self-checking, natural-language music recommender.
It extends my Module 3 **Music Recommender Simulation** (VibeFinder 1.0).

---

## 2. Intended Use

A classroom demonstration of an applied-AI *system*: it turns a plain-English
request ("chill lofi for studying") into a ranked playlist with reasons, a
confidence score, and a self-check. It is for learning how an agent plans,
acts, and verifies its own work — not a production music service. It assumes
a small, hand-authored catalog and a user who can describe a vibe in words.

---

## 3. How the Model Works

There are two ways to start a request: typing one, or pointing the system
at an **Apple Music library export** (`Library.xml` from the Music app),
which the connector parses locally with `plistlib` and turns into a profile
weighted by how often you actually play each genre — no API key or paid
developer account required.

From there a request flows through a four-step loop. First a **planner**
(for text) or the **profile builder** (for a library) fills in a taste
profile (genre, mood, energy, acoustic). Then the
**Module 3 recommender** scores and ranks the catalog against that profile
(+2 for a genre match, +1 for mood, up to +1.5 for how close a song's energy
is, +0.5 for acoustic when asked). An **evaluator** then checks the result
and scores its own confidence; if confidence is too low, the agent **revises**
the plan (for example, re-centering the target energy onto the real songs
when the user gave no energy cue) and tries again, up to three times.

The change from the starter logic is the whole loop around the scoring
core: natural-language input, a confidence number, a self-correcting retry,
logging, and graceful handling of bad input.

---

## 4. Data

The catalog is a hand-authored CSV of **22 songs** across pop, indie pop,
lofi, rock, metal, hip hop, jazz, r&b, country, ambient, and synthwave, each
with genre, mood, and five 0–1 audio features. No real audio or listening
history is used; the feature values are invented. Many genres have only one
or two songs, so the catalog is not a balanced sample of musical taste.

---

## 5. Strengths

- Handles messy, real-world phrasing instead of a hand-built profile object.
- Clear requests get intuitive top picks with a transparent reason per song.
- **Knows when it's unsure:** the confidence score and advisory flag weak
  matches instead of hiding them.
- Fails safe: empty or nonsense input returns a neutral mix with a note,
  never a crash.
- Fully reproducible and free to run — no API key, no network.

---

## 6. Limitations and Bias

- **Fixed planner vocabulary.** A synonym the planner doesn't know
  ("hype music", "bangers") is silently missed, defaulting toward a neutral
  profile. This can quietly disadvantage users who phrase requests
  differently than the built-in keyword list expects.
- **Catalog imbalance drives bias.** Genres with only one song (metal,
  synthwave, country) can rarely fill a good top-5, so fans of
  underrepresented genres get worse results — a dataset bias, not a user
  problem.
- **Exact-match genre/mood.** "indie pop" and "pop" are unrelated tokens;
  the model has no sense of genre adjacency.
- **Popularity/filter-bubble risk.** Because genre is the heaviest term, a
  strong genre preference yields a homogeneous list, the same narrowing
  effect real recommenders are criticized for.
- **Confidence is a heuristic**, not a probability — it measures closeness
  to a perfect feature match, not real user satisfaction.
- **Apple Music profiles are genre-driven.** The library export carries only
  genre and play count, not mood or energy, so a library-built profile
  leans on genre and an inferred energy; mood is left unspecified. Genre
  labels are mapped through a fixed table, so an unusual label (e.g. a niche
  sub-genre) falls through and is ignored.

---

## 7. Evaluation / Testing Results

- **Automated tests:** `pytest` → **22/22 passing** across the scoring core,
  the planner, the evaluator, the agent (including the retry-based
  self-correction, empty-input handling, and the retry cap), and the Apple
  Music connector (parsing, genre mapping, profile building, empty library).
- **Reliability harness:** `python -m src.evaluate` runs **8 requests**
  (clear requests plus empty and nonsense edge cases) and grades each
  against an expectation → **8/8 handled correctly**, **1 solved only after
  a self-correcting retry**, **average confidence 0.74** (excluding empty
  input). The parseable report is in `assets/evaluation_report.md`.
- **What the testing showed:** the agent is reliable on clear requests and
  degrades honestly on vague ones. The retry meaningfully rescued the "some
  jazz" case (confidence 0.63 → 0.69 after re-centering energy). The main
  weakness surfaced by testing is vocabulary coverage, which the confidence
  score keeps visible.

---

## 8. Future Work

- Replace exact keyword matching with fuzzy or embedding-based intent
  parsing so unknown phrasings still work.
- Add genre-adjacency so near-genres earn partial credit.
- Add a diversity guardrail so the top-5 isn't a single genre.
- Grow and balance the catalog so every genre has a fair number of songs.

---

## 9. Personal Reflection

The most useful lesson was that turning a working function into a
trustworthy *system* is mostly defensive engineering: most of the new code
exists so the program can notice when it might be wrong and say so out loud.
Designing an honest confidence score — one that admits "you didn't tell me
much, so I'm not sure" — was harder and more valuable than the
recommendations themselves.

---

## 10. Responsible-AI Reflection (graded)

**How I collaborated with AI.** I used an AI coding assistant throughout:
to scaffold the planner/evaluator/agent modules, to draft the test suite,
and as a sounding board for the confidence design. I reviewed and ran every
change myself, kept the Module 3 scoring core under my own control, and
verified behavior with the tests and the reliability harness rather than
trusting the generated code on sight.

**One suggestion I accepted.** The idea to make the agent's retry a
*re-centering of target energy* onto the mean energy of the matching songs
(when the user gave no energy cue). It's a small, explainable fix that
turns the loop into a genuine plan-act-check-revise cycle, and the logs show
it rescuing the "some jazz" case. I accepted it because it was bounded,
transparent, and easy to test.

**One suggestion I revised/rejected.** The first confidence design
normalized the top score against *only the dimensions the user specified*.
I rejected that: it made a vague one-word request look highly confident
(it had almost nothing to satisfy), which is exactly backwards. I revised it
to measure confidence against a **fixed full-match ceiling**, so a request
that leaves out genre or mood honestly scores lower. Testing the edge cases
is what exposed the problem.

**System limitations (responsible use).** This agent should not be mistaken
for a real recommender: the catalog and features are invented, the planner
understands only a fixed vocabulary, and "confidence" is a feature-match
heuristic, not a measure of whether a listener will actually like the song.
Its genre weighting can reinforce filter bubbles, and its dataset imbalance
disadvantages underrepresented genres — both documented in Section 6 so the
behavior is visible rather than hidden.
