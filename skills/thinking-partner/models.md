# Mental models for /thinking-partner

Pick two or three that fit the problem type. Each entry: what it is, and the question it forces.

## Fit table

| Problem type | Start with |
|---|---|
| What to build next, prioritization | Opportunity cost, Constraint, Pareto, Reversibility |
| Architecture, vendor, tooling | Reversibility, Second-order effects, Inversion, Base rates |
| Launch, pricing, growth | Jobs to be done, Base rates, Pre-mortem, Incentives |
| A plan that "can't fail" | Pre-mortem, Inversion, Assumption ladder |
| Stuck in a long debate | First principles, Reversibility, Cheapest test |
| Team or process change | Incentives, Second-order effects, Constraint |
| Continuing or killing a project | Sunk cost, Opportunity cost, Regret test |

## Catalog

- **Inversion** - Instead of "how do we succeed?", ask "what would guarantee failure?" and avoid those things. Question: what would make this definitely go wrong?
- **Pre-mortem** - Assume it is six months later and the plan failed; write the most likely reasons (Gary Klein, "Performing a Project Premortem", Harvard Business Review, 2007). Question: why did it fail, concretely, for us?
- **Second-order effects** - Every change has consequences of its consequences. Question: and then what happens - for users, for the codebase, for the team next quarter?
- **Reversibility (one-way vs two-way doors)** - Reversible decisions should be made fast; irreversible ones deserve the slow process (Jeff Bezos, Amazon 2015 letter to shareholders, https://www.sec.gov/Archives/edgar/data/1018724/000119312516530910/d168744dex991.htm). Question: what does it cost to undo this in three months?
- **Opportunity cost** - The real cost of doing X is the best thing you won't do instead. Question: what drops off the list if we do this?
- **First principles** - Break the problem down to what is known to be true and rebuild from there, ignoring "how it's usually done". Question: what do we actually know, and what are we copying?
- **Constraint (bottleneck)** - A system moves at the speed of its tightest constraint; improving anything else changes little (Eliyahu Goldratt, Theory of Constraints, "The Goal", 1984). Question: what is the one thing currently limiting progress?
- **Pareto** - A small share of causes usually drives most of the effect. Question: which 20% of the work delivers most of the value here?
- **Base rates** - Before judging this case, look at how similar cases usually turn out. Question: how often does this kind of project, feature or estimate succeed, in general?
- **Jobs to be done** - People "hire" a product to make progress in a situation. Question: what progress is the user trying to make, and what do they use for it today?
- **Incentives** - People respond to what they are rewarded for, not to what they are told. Question: who gains or loses if this happens, and how will they behave?
- **Sunk cost** - Effort already spent is gone either way and shouldn't decide what happens next. Question: knowing what we know now, would we start this today?
- **Regret test** - Imagine looking back in a year. Question: which choice would we regret more, and why?
- **Assumption ladder** - List what must be true for the plan to work, from riskiest to safest. Question: which assumption, if false, kills it, and how cheaply can we test it?
- **Cheapest test** - Most debates end faster with a small experiment than with more argument. Question: what could we try this week that would settle it?
