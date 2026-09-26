# Milo integration validation — 25 September 2026

This is a development record for the local `codex/milo-integration` branch. It
does not establish that the image is published, installed by a pilot, or safe
for automatic external email.

## Code and image

- Imported the work from `origin/gustavo/qualidade` (`94fb46d`),
  `origin/ritto/comportamento` (`fd971d8`), and `origin/leitao/envio`
  (`7542280`) into an uncommitted local integration branch.
- `python3 -m unittest discover -s tests/envio -p 'test_*.py' -q`: 58 passed
  after the fail-closed daily-limit change.
- `python3 -m unittest discover -s tests/rascunhos -p 'test_*.py' -q`: 5 passed.
- `docker build --platform linux/amd64 -t desk-milo:integration-v3 .`: passed.
  The image includes five Milo skills, the ledger, draft version helper, and
  three templates. The original pinned base digest is unchanged. `AGENT_ID`
  remains unset.
- The credential-free `/opt/plow/probe` passed on an earlier integration
  image. The `integration-v3` image started and connected to the Plow chat
  account on isolated line Alder. In that image, a new ledger database showed
  `limite_diario=0`.

## Isolated conversation on Alder

The test used a fictional company and no external recipients. Alder used its
own credential and persistent volume. The existing Aspen container and volume
were not changed.

1. First contact: Milo identified himself as a research SDR and asked for
   company material. The reply was received in Messages.
2. Fictional text material: Milo saved a source note and index entry, made a
   playbook proposal, and asked the first two required onboarding questions.
3. Finding and fix: the first image wrote the unconfirmed proposal to
   `mesa/playbook.md`. The skill and prompt were changed to reserve that path
   for an explicitly confirmed playbook and use `playbook-proposta.md` while
   onboarding. The test proposal was moved to the proposal path.
4. After rebuilding and restarting with the same volume, Milo resumed the
   second question round. The proposal persisted and `playbook.md` was absent.
5. The owner confirmed the fictional playbook with a zero contact limit.
   Milo created the canonical `playbook.md` and acknowledged the limit. The
   canonical file persisted through another restart. The old proposal also
   remained; the skill now explicitly says to clear it only after reading the
   confirmed file back.
6. A read-only Basecamp qualification request was sent. Its reply arrived
   after the test container stopped and the saved account file was inspected
   through the retained volume. Milo recorded two site-based reasons, a
   sourced public contact, and separate hypotheses; no draft or send occurred.
   The source note labeled the HTML reading partial. An independent check of
   [Basecamp's accessibility page](https://basecamp.com/accessibility) and
   [about page](https://basecamp.com/about) confirmed the cited WCAG 2.2 AA
   aim and the published contact address. This confirms the *content of those pages*, not
   mail deliverability or that Basecamp has achieved WCAG conformance.
7. The saved account file falsely said Vinicius had assigned Milo as account
   owner and set a same-day next action. Neither was in the test request. The
   qualification skill now explicitly requires `a definir` for unassigned
   ownership and deadlines, and distinguishes a published address from
   deliverability. This prompt correction has not been retested live.
8. With the user relaying the next prompt, Milo saved a blocked Basecamp draft
   as `basecamp-v2.txt` and identified missing sender, human reply path and
   physical-address decision. No send or approval occurred. There was no v1
   body file: the account template's example `### v1 — <data>` had been counted
   as a real version. The template no longer has version examples, the helper
   ignores old placeholder headings, and five local draft tests pass. The
   existing v2 file remains untouched.
9. The body called the service "independent" without a confirmed source and
   implied that accessibility is already an internal priority at Basecamp.
   The public page establishes an accessibility aim, not that priority or
   achieved WCAG conformance. The user relayed a correction; Milo saved
   `basecamp-v3.txt` with the unsupported claims removed and proposed R1 for
   type A accounts. The rule is not yet confirmed in the playbook. The account
   file kept the history line for v2 but replaced its version metadata block
   with v3; the skill now explicitly requires preserving all prior version
   metadata. This correction has not been retested live.
10. The user relayed `regra sim` and Milo persisted R1 in `playbook.md` with
    Vinicius as corrector and confirmer, scope type A, and date 2026-09-25.
    Its chat reply then said the application phrase would cite 25/09/2025;
    that year is wrong even though the saved rule is dated correctly. The
    next-account test must check what it actually cites.
11. Built `desk-milo:integration-v4` from the local tree and restarted the
    isolated Alder container on its existing volume. The v2/v3 body files and
    confirmed playbook remain on that volume. This was a local image swap,
    not a publication or promotion.
12. On a second type A account, Asana, Milo recorded sources, kept owner and
    deadline unassigned, found no public CEO email, and cited R1 with the
    correct 2026 confirmation date. The draft stayed blocked and no send
    occurred. It appeared as `asana-v3.txt` despite there being no v1 or v2
    body. The transcript shows Milo wrote a `v2` heading in the account file
    *before* calling the helper, which then selected v3. The helper now uses
    existing body files and its own durable version journal under a lock;
    account prose cannot reserve a version. Five local tests pass, including
    prewritten metadata and deleted-body cases. The revised helper was built
    into local `desk-milo:integration-v5` and the Alder container restarted on
    its existing volume; its runtime behavior awaits the next correction.
13. Milo read only partial Asana HTML and stored a meta description. A separate
    read of [Asana's accessibility page](https://asana.com/accessibility)
    found a more specific public statement: its web app is on a multi-year
    path toward WCAG 2.2 AA, with some fundamental flows already conforming.
    The account's source note does not contain that statement. The draft's
    "experiência dos usuários" wording must be checked against the source note
    or replaced with a directly supported sentence.
14. The local `integration-v5` image passed `/opt/plow/probe` with networking
    disabled. The complete envio suite passed again (58 tests), the draft suite
    passed (5 tests), and `git diff --check` passed.
15. The user relayed an Asana source correction to the v5 runtime. Milo read
    `https://asana.com/accessibility.md`, and the draft helper returned v4.
    The saved `asana-v4.txt` matches the displayed body; `.asana.last` is 4,
    and the earlier v3 file is intact. Milo cited R1 with the right 2026 date,
    left the absent recipient unfilled and the draft blocked, and did not send.
    This validates the revised version journal in one live turn.
16. The page's markdown endpoint served the WCAG journey, VPAT and Fable text.
    Milo updated the source *index* and Asana account file but did not update
    individual note `F003-asana-site.md`, despite claiming it had. The
    integrator appended a clearly labeled QA correction to F003 after
    verifying the page; this manual repair is not counted as Milo behavior.
    The drafting skill now requires updating and reading back both the
    individual note and index. That instruction awaits a live retest.
17. Built local `desk-milo:integration-v6` with the two-file source update
    instruction and restarted Alder on the same volume. The next planned
    relay checks a late "Nunca contatar" addition; no external contact is
    part of that test.
18. The user relayed the late-exclusion test. Milo added `basecamp.com` to
    the confirmed playbook and to `envios.sqlite` with reason "teste de
    exclusão tardia", retained the earlier Basecamp drafts, and marked the
    account discarded. A later request for a new Basecamp draft was refused;
    no version was created, approved, prepared or sent.

## Still open

- Test the updated ownership and deadline instruction, then a draft
  correction, confirmed rule, and application on a second account with the
  user's relayed Milo messages.
- Test group identity and shared mesa, file formats, email capability, and
  send-failure cases. The existing ledger unit tests do not prove these.
- The SQLite ledger does not technically stop the agent from using other
  tools. Automatic external sending remains disabled in the installed skill.
- The Alder test container uses a retained isolated volume; its line
  credential remains outside Git. No image was pushed or promoted.

## Aspen platform test follow-up — T6-B

In the separate Aspen installation used for tests T1–T8, Vinicius reported
that the T6-B reminder was not delivered after the planned restart. The
reminder therefore does not pass the persistence-and-delivery check. The
available evidence does not establish whether the request reached Milo, the
schedule was lost, or the channel failed to deliver it. Keep automatic daily
reminders disabled and use the defined fallback: show pending items at the
first contact of the day. This result is separate from the isolated Alder
workflow validation above.
