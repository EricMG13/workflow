# T1 fix round 2 brief (controller ruling on branch review M2, I1)

Replace exactly (each old text occurs once):
1. `.claude/skills/create-prove-it/SKILL.md` step 8, the sentence `A comparison over 5 minutes
   goes into \`HEAVY\` in \`cases/prove/affected_tests.py\`.` (it may be wrapped across lines; match ignoring the line break) becomes `A test-file comparison over 5 minutes goes into \`HEAVY\` in \`cases/prove/affected_tests.py\` (PR CI runs it under the \`heavy-tests\` label); a \`cases/prove/\` script is run by the controller, never by PR CI.` (M2)
2. `CLAUDE.md`: `builder (writes \`src/\` and \`tests/\`)` becomes `builder (writes \`src/\` and \`tests/\`, except the verifier tests \`tests/test_goldens_*.py\` and \`tests/test_prove_*.py\`)`. (I1)
