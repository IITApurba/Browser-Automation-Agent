# Selector Repair Prompt

A selector used to locate an element on the page failed. Propose a single
replacement CSS selector based on the DOM snapshot below.

## Target element description
{description}

## DOM snapshot
{dom_snapshot}

## Output format

Respond with ONLY a JSON object (no prose, no markdown fences):

```json
{"selector": "css selector string or null if none found"}
```
