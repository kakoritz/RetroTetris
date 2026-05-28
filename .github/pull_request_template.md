## Summary
<!-- What changed and why -->


## Docs updated on development branch
- [ ] `RELEASE_NOTES.md` — changelog entry with version bump
- [ ] `README.md` — features / controls / scoring tables current
- [ ] `DESIGN.md` — design intent updated for any new systems
- [ ] `CLAUDE_REVIEW.md` — honest review of the change + rating update
- [ ] `CLAUDE.md` — updated if protocol changed

## QA checklist
- [ ] `python3 -m pytest tests/ -q` — all tests pass
- [ ] Game runs: `python3 main.py`
- [ ] Feature tested in-game (golden path)
- [ ] No regressions in adjacent features
- [ ] CI green on this PR
