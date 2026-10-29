# Six kinds of knowledge: definitions, overlaps, cautions

*Research note, 2026-10-29, web sources only. plato.stanford.edu, iep.utm.edu and en.wikipedia.org were not reachable from this session, so SEP/IEP/Wikipedia content is cited from search extracts, not the live pages.*

**Labels.** The asker's "deducted / inducted / abducted knowledge" are non-standard; the standard forms are *deduced / induced / abduced* (adjectives *deductive / inductive / abductive*). The rest of this note uses the standard terms.

| Asker's label | Standard term used here |
|---|---|
| asserted knowledge | asserted (testimonial) knowledge |
| deducted knowledge | deductive (deduced) knowledge |
| inducted knowledge | inductive (induced) knowledge |
| abducted knowledge | abductive (abduced) knowledge |
| tacit knowledge | tacit knowledge |
| tribal knowledge | tribal knowledge |

## 1. Framing

The first four terms classify a piece of knowledge by **how it is justified or arrived at**. Epistemology lists the sources of knowledge as perception, memory, reason (inference) and testimony [SEP-Test; Audi]; deduction, induction and abduction are Peirce's three "elementary kinds of reasoning" [SEP-Abd-P] and testimony (someone else's say-so) is the fourth source, so the four do share an axis. The literature refines the second half of the framing: *tacit* and *tribal* sit on two axes, not one. Nonaka's model has an **epistemological dimension** (tacit versus explicit: can it be articulated?) and a separate **ontological dimension** (held by an individual, a group, an organisation) [Nonaka94]. "Tacit" is a point on the first; "tribal" names a position on the second (group-held) plus an articulation status (not written down). So the honest picture is three axes: *justification* (asserted/deductive/inductive/abductive), *articulation* (tacit/explicit) and *social holding* (individual/team/organisation). Any one claim has a value on each.

## 2. Definitions

**Asserted knowledge.** Three distinct senses exist; only the first is a kind of knowledge.
(a) *Testimonial sense.* Knowledge a hearer acquires by accepting a speaker's assertion on the speaker's authority, without working it out independently. The question since Hume (trust needs inductive backing) and Reid (1764, "principle of credulity": a standing, defeasible entitlement to believe what we are told) is whether a speaker's word alone can justify belief [SEP-Test; 1000WP]. (b) *Speech-act sense.* An assertion is the act of stating that something is so; Williamson (1996; 2000, ch. 11) argued assertion is governed by the **knowledge norm**: "assert p only if you know p" [IEP-KN; Williamson96]. A norm on speakers rather than a kind of knowledge, but it is why an SME's sign-off carries weight: to assert is to represent oneself as knowing. (c) *Knowledge-base sense.* In ontologies and expert systems, **asserted** axioms or facts are those explicitly entered; **inferred** (or *derived*) ones are computed by a reasoner. Protégé shows asserted and inferred class hierarchies side by side [Protégé]; the OWL working group noted tools must keep the two apart [W3C-OWL]; AI textbooks call the split primitive versus derived knowledge [Poole]. *Example:* "The settlement cut-off is 16:00 CET because the ops lead says so" is asserted knowledge; it was never derived from the code.

**Deductive knowledge.** Knowledge obtained by an argument in which, if the premises are true, the conclusion cannot be false (validity) [IEP-DI]. Peirce (1878) illustrated it with his bean bag: *Rule* (all beans from this bag are white) + *Case* (these beans are from this bag) gives *Result* (these beans are white) [Peirce1878]. Deduction is truth-preserving and introduces no new idea: it "merely evolves the necessary consequences of a pure hypothesis" [SEP-Abd-P]. Certainty: as high as the premises. *Example:* reading `if amount > limit: reject()` and concluding that any amount above the limit is rejected — certain, given the code and the runtime semantics.

**Inductive knowledge.** Knowledge obtained by generalising from observed instances to a rule; the premises make the conclusion probable, not certain (strength, not validity) [IEP-DI]. Peirce's form: *Case* + *Result* gives *Rule* — "all the beans in the bag were white", "an inversion of the deductive syllogism" [Peirce1878]. Induction is ampliative (says more than the data) and so defeasible by the next observation. *Example:* 10,000 replayed transactions show that every rejected payment has a reason code; "rejections always carry a reason code" is inductive, and one counter-example in the archive breaks it.

**Abductive knowledge.** A candidate for knowledge, obtained by proposing a hypothesis that would explain a surprising observation. Peirce's 1903 schema: "The surprising fact, C, is observed; but if A were true, C would be a matter of course; hence there is reason to suspect that A is true" (CP 5.189) [SEP-Abd-P]. It is "the only logical operation which introduces any new idea" (CP 5.171) [SEP-Abd-P], and Peirce's form from 1878 is *Rule* + *Result* gives *Case*. Modern usage often merges it with inference to the best explanation, a phrase Peirce never used [SEP-Abd]. Certainty: lowest of the three; it yields a hypothesis to test. *Example:* a legacy batch job skips records dated 29 February; the reverse engineer proposes "an upstream mainframe date library could not handle leap days" — plausible, explanatory, unproven.

**Tacit knowledge.** Michael Polanyi's term (*Personal Knowledge*, 1958; *The Tacit Dimension*, 1966): "we can know more than we can tell" [Polanyi66, p. 4]. His examples are recognising a face, riding a bicycle, a scientist's nose for a promising problem: skilled performance guided by particulars the performer attends *from*, not *to*, and so cannot fully specify. Nonaka (1994) and Nonaka and Takeuchi (1995) imported the term into management as one pole of the tacit/explicit pair and claimed it can be "externalised" through metaphor, analogy and models [Nonaka94; N&T95]. *Example:* a settlements operator who knows a reconciliation break "looks wrong" before any rule fires, or picks the right exception queue without being able to state the criteria.

**Tribal knowledge.** An informal industry term: "unwritten information that is not commonly known by others within a company" [Wiki-TK]; iSixSigma's definition adds that it is held only in employees' heads and assumed factual without data to verify it [iSixSigma via iConnect]. The name is an analogy with anthropology's tribes, popularised by the Six Sigma community, and sometimes considered derogatory [Wiki-TK]. There is no canonical academic source; the nearest scholarly concepts are *organisational memory* (Walsh and Ungson 1991: "stored information from an organization's history that can be brought to bear on present decisions") [W&U91] and Naur's *theory* of a program, which lives in the team and dies when the team disbands [Naur85]. *Example:* "never run the end-of-day job before the FX feed is confirmed, because of the 2014 incident" — known to the team, in no runbook.

## 3. Comparison table

| Term | Axis | Arrived at / held | Writable as is? | Typical failure mode | Validated by |
|---|---|---|---|---|---|
| Asserted (testimonial) | Justification | Taken on a speaker's word | Yes, as a sourced statement | Trusting an unreliable or outdated source; hearsay chains | Checking the source's competence and sincerity; corroboration [SEP-Test] |
| Deductive | Justification | Necessary consequence of premises | Yes, with premises | True of the code, false of the business (wrong premises) | Re-derivation; checking premises |
| Inductive | Justification | Generalisation from cases | Yes, with sample and confidence | Over-generalisation; unseen counter-examples | More cases; search for counter-examples [IEP-DI] |
| Abductive | Justification | Hypothesis that would explain an observation | Yes, *as a hypothesis* | Mistaking a plausible story for a fact; rival explanations ignored [SEP-Abd] | Test, or an authority confirms it |
| Tacit | Articulation | Embodied skill or judgement, used without stating | Only partly, and with loss [Polanyi66; Tsoukas03] | Lost with the person; cannot be audited | Observed performance; apprenticeship; SME review of drafts |
| Tribal | Social holding + articulation | Shared informally within a team | Yes in principle (it is often sayable), but nobody has | Lost with turnover [Rigby16; Nassif17]; believed without evidence | Writing down, then checking against system and authority |

## 4. Overlap and complementarity

**Orthogonal pairs.** Each justification term is independent of the tacit/explicit and individual/group axes: a deduction can be explicit and personal, an abductive hunch tacit, a testimonial claim tribal. Tacit and tribal are also orthogonal in principle: much tribal knowledge is articulable but unwritten (a deployment ritual), whereas Polanyi's tacit knowledge resists articulation even by its holder.

**Nested or overlapping pairs.** Tacit knowledge often *consists of* inductively acquired pattern recognition: the operator's "this looks wrong" is a classifier trained on cases, held without the rule being stated. Tribal knowledge is *frequently* asserted knowledge: it propagates by testimony ("the old hands say..."), which is why iSixSigma flags it as assumed factual with no data behind it. Explicit knowledge (Nonaka) results from *externalising* tacit knowledge; on Nonaka's two dimensions, "tribal" is roughly *group-level, not-yet-explicit* knowledge, which may be tacit or merely unwritten.

**Stages of one process.** For the reverse-engineering plus LLM-drafting plus SME-validation pipeline, the four justification terms line up as stages:
1. *Observation* and *deduction* from code give what the system demonstrably does — the method document's **observed** claims.
2. *Induction* over traces and data gives generalised rules with confidence; *abduction* gives proposed explanations for quirks. Both are **inferred** claims. Brooks's model of program comprehension is exactly this hypothesis-and-beacon loop [Brooks83], and debugging literature calls abduction the only move that generates a candidate cause [Vinju19; HypoDeduce26].
3. An SME's confirmation converts an inferred claim into an **asserted** one in the testimonial sense (the SME vouches for it, under the knowledge norm of assertion), and, if the SME is the responsible authority, into an **intended** claim. In knowledge-base terms the claim moves from *inferred* to *asserted* provenance [Protégé; W3C-OWL].

This matches the method document's rule that an implementer's guess is "a gap hypothesis, not recovered tacit knowledge": a guess is abductive and unconfirmed, whereas recovered tacit knowledge is a claim about what a practitioner actually does, which only observed practice or the practitioner's confirmation can supply. The pipeline as a whole externalises tacit and tribal knowledge into explicit, asserted statements: Nonaka's externalisation step, and precisely the move Tsoukas calls lossy [Tsoukas03]; SME validation is the control on that loss.

## 5. Terminology cautions

- **"Deducted / inducted / abducted"** are not used in logic or epistemology; "deducted" means subtracted and "abducted" means kidnapped. Use *deduced/inferred by deduction*, *induced*, *abduced*, or the adjectives *deductive/inductive/abductive knowledge*.
- **"Asserted knowledge"** is not a fixed term either; it borrows from three literatures. Say which sense is meant; for the pipeline the knowledge-base sense (entered by an authority, not derived) is the most useful.
- **"Tribal knowledge"** is an industry colloquialism with no canonical academic source; it was popularised by the Six Sigma community and is sometimes felt to be derogatory [Wiki-TK]. Academic alternatives: *organisational memory* [W&U91], *organisational* or *institutional knowledge*, Naur's *theory of the program* [Naur85], and the software-engineering literature on *turnover-induced knowledge loss* [Rigby16; Nassif17].
- **"Tacit"** has a strong and a weak sense. Polanyi's strong sense: knowledge that cannot be fully told even by its holder. The knowledge-management sense (Nonaka): knowledge not yet written down but convertible. Tsoukas (2003) argues the second misreads the first: tacit knowledge "cannot be 'captured', 'translated', or 'converted' but only displayed and manifested in what we do" [Tsoukas03]. A deck on *preserving* tacit knowledge should say which sense it means; most of what the pipeline recovers is tacit in the weak sense, and the strong-sense residue is what SME validation and apprenticeship exist for.

## 6. References

- [SEP-Abd] Douven, I., "Abduction", *Stanford Encyclopedia of Philosophy* (2011, rev.). https://plato.stanford.edu/entries/abduction/
- [SEP-Abd-P] "Peirce on Abduction", supplement to the above. https://plato.stanford.edu/entries/abduction/peirce.html
- [Peirce1878] Peirce, C. S., "Deduction, Induction, and Hypothesis", *Popular Science Monthly* 13 (Aug. 1878). https://en.wikisource.org/wiki/Popular_Science_Monthly/Volume_13/August_1878/Illustrations_of_the_Logic_of_Science_VI
- [IEP-DI] Shanahan, T., "Deductive and Inductive Arguments", *Internet Encyclopedia of Philosophy* (2022). https://iep.utm.edu/deductive-inductive-arguments/
- [SEP-Test] Adler, J., "Epistemological Problems of Testimony", *SEP* (2006, rev. 2012). https://plato.stanford.edu/entries/testimony-episprob/
- [1000WP] "Take My Word for It: On Testimony", *1000-Word Philosophy* (2014). https://1000wordphilosophy.com/2014/01/27/take-my-word-for-it-on-testimony/
- [SEP-Assert] Pagin, P. and Marsili, N., "Assertion", *SEP*. https://plato.stanford.edu/entries/assertion/
- [IEP-KN] Benton, M., "Knowledge Norms", *IEP*. https://iep.utm.edu/kn-norms/
- [Williamson96] Williamson, T., "Knowing and Asserting", *Philosophical Review* 105(4), 1996, 489–523; and *Knowledge and its Limits* (OUP, 2000), ch. 11.
- [Protégé] Protégé documentation, "Class Hierarchy" (asserted vs inferred views). https://protegeproject.github.io/protege/views/class-hierarchy
- [W3C-OWL] OWL Working Group list, Jan. 2009, on distinguishing asserted from inferred axioms. https://lists.w3.org/Archives/Public/public-owl-wg/2009Jan/0105.html
- [Poole] Poole, D. and Mackworth, A., *Artificial Intelligence: Foundations of Computational Agents*, §14.2 (primitive vs derived knowledge). https://artint.info/2e/html2e/ArtInt2e.Ch14.S2.SS3.html
- [Polanyi66] Polanyi, M., *The Tacit Dimension* (Doubleday, 1966), p. 4; *Personal Knowledge* (Chicago, 1958). Commentary: https://infed.org/dir/michael-polanyi-and-tacit-knowledge/
- [Nonaka94] Nonaka, I., "A Dynamic Theory of Organizational Knowledge Creation", *Organization Science* 5(1), 1994, 14–37. https://econpapers.repec.org/RePEc:inm:ororsc:v:5:y:1994:i:1:p:14-37
- [N&T95] Nonaka, I. and Takeuchi, H., *The Knowledge-Creating Company* (OUP, 1995). Summary of SECI: https://www.open.edu/openlearn/money-business/making-creativity-and-innovation-happen/content-section-7.1
- [Tsoukas03] Tsoukas, H., "Do we really understand tacit knowledge?", in Easterby-Smith and Lyles (eds), *Blackwell Handbook of Organizational Learning and Knowledge Management* (2003). https://mba.eci.ufmg.br/downloads/dowereally.pdf
- [Wiki-TK] "Tribal knowledge", *Wikipedia*. https://en.wikipedia.org/wiki/Tribal_knowledge
- [iSixSigma via iConnect] Shaughnessy, A., "Tribal Knowledge: Friend or Foe?", iConnect007 (quoting the iSixSigma dictionary). https://iconnect007.com/article/135500/the-shaughnessy-report-tribal-knowledgefriend-or-foe/135503/design
- [W&U91] Walsh, J. P. and Ungson, G. R., "Organizational Memory", *Academy of Management Review* 16(1), 1991, 57–91. Summary: https://kmt.helpjuice.com/organizational-memory-and-knowledge
- [Naur85] Naur, P., "Programming as Theory Building", *Microprocessing and Microprogramming* 15 (1985), 253–261. Notes: https://www.ratfactor.com/papers/naur1
- [Rigby16] Rigby, P. C., Zhu, Y. C., Donadelli, S. M. and Mockus, A., "Quantifying and Mitigating Turnover-Induced Knowledge Loss", *ICSE 2016*, 1006–1016.
- [Nassif17] Nassif, M. and Robillard, M., "Revisiting Turnover-Induced Knowledge Loss in Software Projects", *ICSME 2017*. https://www.cs.mcgill.ca/~martin/papers/icsme2017.pdf
- [Brooks83] Brooks, R., "Towards a theory of the comprehension of computer programs", *Int. J. Man-Machine Studies* 18 (1983), 543–554. Discussion: https://www.cs.kent.edu/~jmaletic/Prog-Comp/Papers/OBrien01.pdf
- [Chikofsky90] Chikofsky, E. J. and Cross, J. H., "Reverse Engineering and Design Recovery: A Taxonomy", *IEEE Software* 7(1), 1990, 13–17. https://program-transformation.org/Transform/ReverseAndReengineeringTaxonomy
- [Vinju19] Vinju, J., "Unroll: three ways of reasoning while debugging" (2019). https://homepages.cwi.nl/~jurgenv/2019/03/07/debugging-methods-of-reasoning.html
- [HypoDeduce26] "Abductive Reasoning for Neurosymbolic Fault Localization", *ICSE 2026 NIER*. https://conf.researchr.org/details/icse-2026/icse-2026-nier/38/Abductive-Reasoning-for-Neurosymbolic-Fault-Localization
- [Audi] Audi, R., *Epistemology: A Contemporary Introduction* (Routledge), on the standard sources of knowledge.
