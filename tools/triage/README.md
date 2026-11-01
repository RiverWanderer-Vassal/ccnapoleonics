# Issue triage

- `vassal_extract.py`: summarises a VASSAL `.vsav` / `.vlog` (or one renamed to `.zip`, or a `.zip` of them): module and VASSAL versions, the save comment, error/alert lines and the last chat/report lines. Usable on its own: `python3 tools/triage/vassal_extract.py game.vlog --lines 40`.
- `.github/workflows/issue-triage.yml`: when an issue is opened, downloads its attachments, runs the extractor, and asks Claude to post one triage comment (summary, versions, likely module area, possible duplicates, what's missing).

## Setup (repository owner)
1. Create an API key in the Anthropic Console and add it as repository secret `ANTHROPIC_API_KEY` (Settings > Secrets and variables > Actions).
2. Optional: repository variable `TRIAGE_MODE` = `label` to let triage add labels too. Default is `comment` (comment only).
3. To re-run triage on an issue, add the label `triage`, or run the workflow by hand from the Actions tab.

Reporters need only a GitHub account. Issues opened by the maintainer are not triaged automatically.
