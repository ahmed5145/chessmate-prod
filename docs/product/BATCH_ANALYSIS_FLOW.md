# Batch Analysis User Flow

## Goal
Turn a set of imported games into one combined coaching report with a clear next action.

## Primary Flow
1. User opens Batch Analysis.
2. User sees imported games and a shortcut for "most recent N games."
3. User either multi-selects games manually or uses the shortcut.
4. UI shows the selected game count and a short description of what will happen.
5. User starts batch analysis.
6. System queues one combined analysis job.
7. UI shows progress and allows the user to stay on the page.
8. When the job finishes, UI renders one combined report.
9. Report highlights the top recurring weakness, top strength, phase trends, critical moments, and action plan.
10. User can save the report or start another batch.

## Selection Rules
- Manual selection should use the games the user already imported.
- The recent-N shortcut should default to the newest completed games.
- If the user has fewer than N imported games, select all available games.
- The UI should clearly show how many games are included before analysis begins.

## Report Rules
- Return one combined report for the batch in the MVP.
- Prefer recurring patterns over isolated outliers.
- Explain the biggest issue first.
- Keep the tone coach-like and direct.
- Avoid a report that reads like copied template text.

## Progress Rules
- The user should never wonder whether the request was accepted.
- If analysis takes longer, the UI should stay informative instead of silent.
- Later, if a job is long-running, the app can tell the user they may close the tab and receive email when it finishes.

## Failure Rules
- If some games fail, the UI should tell the user how many were included successfully.
- If the batch cannot be completed, the user should be able to retry.
- Partial data should still produce a report when enough games succeed.

## Future Extension
- Add email completion for long jobs.
- Let users compare one batch against another.
- Let users pin a repeated weakness and track it across future batches.