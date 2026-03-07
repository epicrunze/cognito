# Vikunja Filter Syntax

Filter expressions are passed as a single `filter` query parameter on task list endpoints.

## Syntax

```
field comparator value [combinator field comparator value ...]
```

## Comparators

| Operator | Meaning |
|----------|---------|
| `=` | Equals |
| `!=` | Not equals |
| `>` | Greater than |
| `>=` | Greater than or equal |
| `<` | Less than |
| `<=` | Less than or equal |
| `like` | Pattern match (use `%` as wildcard) |
| `in` | Value in list |
| `not in` | Value not in list |

## Combinators

| Operator | Meaning |
|----------|---------|
| `&&` | AND |
| `\|\|` | OR |
| `()` | Grouping / precedence |

## Filterable Fields

All task fields that appear in the sort_by parameter:

`id`, `title`, `description`, `done`, `done_at`, `due_date`, `created_by_id`,
`project_id`, `repeat_after`, `priority`, `start_date`, `end_date`, `hex_color`,
`percent_done`, `uid`, `created`, `updated`

Additional filterable fields: `labels`, `assignees`

## Date Math

Relative date expressions for date fields:

| Expression | Meaning |
|------------|---------|
| `now` | Current timestamp |
| `now+1d` | 1 day from now |
| `now-1w` | 1 week ago |
| `now+1m` | 1 month from now |
| `now+1y` | 1 year from now |

Supported units: `d` (day), `w` (week), `m` (month), `y` (year)

## Additional Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter_timezone` | string | Timezone for date comparisons (e.g., `America/New_York`) |
| `filter_include_nulls` | boolean | Include items where the filtered field is null |

## Examples

### Overdue undone tasks
```
done = false && due_date < now
```

### High priority this week
```
priority >= 3 && due_date <= now+1w && done = false
```

### Tasks in specific projects
```
project_id in [1, 3, 5]
```

### Title search
```
title like "%report%"
```

### Complex grouping
```
done = false && (priority >= 4 || due_date <= now+1d)
```

### Tasks with specific labels
```
labels in [1, 2]
```

### Tasks due today (undone)
```
done = false && due_date <= now+1d && due_date >= now
```

### Completed in last week
```
done = true && done_at >= now-1w
```

## Usage in API Calls

```python
# Python (httpx)
params = {
    "filter": "done = false && priority >= 3",
    "filter_timezone": "America/New_York",
    "sort_by": "due_date",
    "order_by": "asc",
}
response = await client.get("/api/v1/tasks", params=params)
```

```bash
# curl
curl -H "Authorization: Bearer $TOKEN" \
  "https://vikunja.example.com/api/v1/tasks?filter=done%20%3D%20false%20%26%26%20priority%20%3E%3D%203"
```
