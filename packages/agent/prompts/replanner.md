# Replanner Prompt

The agent hit an error while executing its plan and needs a revised plan for
the remaining subtasks.

## Task goal
{task_goal}

## Extraction schema
{extraction_schema}

## Error encountered
{error}

## Scratchpad (prior context/memory)
{scratchpad}

## Remaining plan (from current index onward)
{remaining_plan}

## DOM snapshot at time of failure
{dom_snapshot}

## Output format

Respond with ONLY a JSON object (no prose, no markdown fences), same shape as
the planner output:

```json
{
  "subtasks": [
    {
      "type": "navigate|click|type_text|extract|wait_for_selector",
      "description": "...",
      "params": {"...": "..."}
    }
  ]
}
```

Produce subtasks that replace the remaining plan starting at the current
index, working around the error (e.g. alternate selectors, added waits).
