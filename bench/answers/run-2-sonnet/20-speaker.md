# Why we moved to Rust
Engineering talk
??? Welcome everyone. Today I explain why our team migrated the core service to Rust.

# Motivation
## Why Rust
- Memory safety without a garbage collector
- Predictable tail latency
- Strong tooling and ecosystem
??? Walk through each reason. Mention the GC pauses we saw in production.

# Results
> p99 latency fell 71% and memory 71%
```column {title="Before vs after" labels=on}
,p99 latency (ms),Memory (GB)
Before,120,2.1
After,35,0.6
```
??? Both metrics improved. Note the two metrics use different units.

# Lessons
> [!warn] Budget time for the learning curve: the first months were slower.
??? The main warning: do not underestimate onboarding cost for the team.
