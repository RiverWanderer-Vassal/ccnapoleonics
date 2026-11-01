# Issue triage

- `vassal_extract.py`: summarises a VASSAL `.vsav` / `.vlog` (or one renamed to `.zip`, or a `.zip` of them): module and VASSAL versions, the save comment, error/alert lines and the last chat/report lines. Usable on its own: `python3 tools/triage/vassal_extract.py game.vlog --lines 40`.
- `triage.py`: sends the issue, the attachment summaries and the list of existing issue titles to the Claude API and posts one triage comment (summary, versions, likely module area, possible duplicates, what's missing). `--dry-run` prints instead of posting.
- `.github/workflows/issue-triage.yml`: when an issue is opened, downloads its attachments, runs the extractor, then `triage.py`.

## Setup (repository owner)
1. Authentication is workload identity federation; no API key is stored. In the Claude Console (Settings > Workload identity) a GitHub Actions rule for this organisation and `refs/heads/main` maps runs to a service account. Its IDs are defaults in the workflow; repository or organisation variables of the same name override them: `ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`, `ANTHROPIC_SERVICE_ACCOUNT_ID`, `ANTHROPIC_WORKSPACE_ID` (Settings > Secrets and variables > Actions > Variables). Do not add an `ANTHROPIC_API_KEY` secret.
   Optional variables: `TRIAGE_PRODUCT` (the module name used in the prompt) and `TRIAGE_MODEL`.
2. Optional: repository variable `TRIAGE_MODE` = `label` to let triage add labels too. Default is `comment` (comment only).
3. To re-run triage on an issue, add the label `triage`, or run the workflow by hand from the Actions tab.

Reporters need only a GitHub account. Issues opened by the maintainer are not triaged automatically.
