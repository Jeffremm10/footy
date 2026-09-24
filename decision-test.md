# Decision Test

A human-readable file for defining and tracking decision test cases.

## How to Use

Add test cases below. Each case describes a scenario, the expected decision, and optional notes.

---

## Test Cases

### Example: Match Result Prediction

**Scenario:** Home team is top of the table, away team is bottom, home advantage applies.

**Input:**
- Home team rank: 1
- Away team rank: 20
- Venue: Home

**Expected decision:** Home win

**Notes:** Baseline case; should always resolve to home win without ambiguity.

---

### Example: Draw Threshold

**Scenario:** Two evenly matched mid-table teams.

**Input:**
- Home team rank: 10
- Away team rank: 11
- Venue: Neutral

**Expected decision:** Draw

**Notes:** Edge case — model should not strongly favor either side.

---

## Adding New Cases

Copy the template below and fill it in:

```
### <Short name>

**Scenario:** <Describe the situation>

**Input:**
- Key: Value

**Expected decision:** <What should happen>

**Notes:** <Any caveats or context>
```
