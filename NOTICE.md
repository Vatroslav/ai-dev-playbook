# Notices and credits

The playbook as a whole is licensed under [MIT with the Commons Clause](LICENSE): use, copy and change it freely, but don't sell it or a service built substantially on it. The files and ideas below come from other people and keep their own terms.

## Third-party files

### Reviewer agents (Apache License 2.0)

`agents/logic-reviewer.md`, `agents/quality-reviewer.md` and `agents/security-reviewer.md` are adapted from the anvil reviewer agents in [SenteLabsAI/OpenExecutive](https://github.com/SenteLabsAI/OpenExecutive/tree/69c0ae33eaeab05575a11eda7829bf7cc9ae3d08/.claude/agents).

- Copyright 2025 Open Executive Contributors.
- Licensed under the Apache License, Version 2.0; full text in [licenses/Apache-2.0.txt](licenses/Apache-2.0.txt).
- Each of the three files was modified for this playbook and says so at the top. These three files are distributed under the Apache License 2.0; the Commons Clause does not apply to them.

### Humanizer patterns (MIT License)

`skills/humanizer/SKILL.md` follows several patterns and the two-pass process of [blader/humanizer](https://github.com/blader/humanizer), which is based on Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) guide. The text was rewritten for this playbook.

```
MIT License

Copyright (c) 2025 Siqi Chen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Ideas and references

No text is copied from these sources; they are credited because the work builds on their ideas or data.

- `skills/evidence-first/`: the workflow shape (task sizing, verification ledger, adversarial review on another model, evidence bundle) is inspired by Burke Holland's [Anvil](https://github.com/burkeholland/anvil). The skill text and `scripts/ledger.py` are written independently.
- `skills/new-web-app/scripts/palette-check.py`: OKLab conversion matrices from Bjorn Ottosson, [A perceptual color space for image processing](https://bottosson.github.io/posts/oklab/); example colours from Sasha Trubetskoy's [List of 20 Simple, Distinct Colors](https://sashamaps.net/docs/resources/20-colors/).
- `skills/thinking-partner/models.md`: models with a clear originator are credited inline.
- `skills/validate-idea/4-point-test.md`: compiled from several product-management courses and books.
