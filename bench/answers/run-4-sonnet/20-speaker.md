# Why we moved to Rust
Engineering talk
??? Welcome; introduce the topic and agenda.

# Motivation
> Reliability and performance drove the move
- Unpredictable tail latency
- High memory use
- Runtime crashes in production
??? Explain the pain points that triggered the migration.

# Results
> p99 latency fell 70% and memory 71%
```column {title="Before vs After" labels=on}
,p99 latency (ms),Memory (GB)
Before,120,2.1
After,35,0.6
```
??? Walk through both metrics; note that numbers are from production.

# Lessons
> [!warn] The learning curve is steep: budget time for training
??? Close with lessons and invite questions.
