# Local integration patches

- `skill_registry.patch`: apply to `LDlornd/skill_registry` at `97015e3d182d83c6297c609cc55160d49ff12b44`.
- `rsi-flow-spring-boot.patch`: apply to `ymxiong/rsi-flow-spring-boot` at `11b418d3068343d0430e46a58650f97d189159d5`.

From each checkout, run `git apply --check <patch>` and then `git apply <patch>`.
These patches contain source code and configuration only. They do not contain SkillsBench skill files, workbooks, traces, secrets, or model usage records. The upstream repositories are not pushed by this delivery.
