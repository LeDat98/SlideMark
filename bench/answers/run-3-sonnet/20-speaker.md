# Why we moved to Rust
Engineering talk
??? Welcome; introduce the topic and the team.

# Motivation
- Memory-safety bugs in production
- Unpredictable latency spikes
- Hard to maintain concurrency
??? Explain the incidents that triggered the move.

# Results
```column {title="Before vs after" labels=on}
,p99 latency (ms),Memory (GB)
Before,120,2.1
After,35,0.6
```
??? p99 fell from 120ms to 35ms; memory from 2.1GB to 0.6GB.

# Lessons
> [!warn] Budget time for the learning curve; the first months are slower.
??? Stress hiring and training; recommend incremental migration.
