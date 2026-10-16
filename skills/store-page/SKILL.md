---
name: store-page
description: Produce store-listing or landing-page material from the real product - description from real features, 3-5 real screenshots, a cover/feature graphic/hero image made from real assets and checked by an isolated critic, metadata suggestions, an honest AI-use disclosure and a credits block. Use on "/store-page", "make the store page", "write the listing", "make a cover and screenshots", "prepare the landing page assets", or when deploy-static's first-time setup offers it. NOT for publishing or changing store settings, and NOT for marketing strategy.
argument-hint: "[optional: target - itch, play, app-store, landing] [optional: part to update - description, screenshots, cover]"
---

# Store page material

The deploy step pushes the build; this skill produces the page content that a human pastes or uploads by hand. Everything lands in `promo/store/` and the text is also printed in chat. Product specifics come from the repo (README, spec, code, assets), never from imagination.

Why this shape: a listing written from memory promises features the app doesn't have, a generated cover that doesn't look like the product loses trust on the first screenshot, and an AI disclosure that looks evasive costs more than one extra checkbox.

## Preflight

- No runnable build and no source to read: print `SKIP: nothing to describe - build the product first` and stop.
- `promo/store/` already has a cover and a description: don't regenerate. Show the checklist from `promo/store/README.md` and offer to update one part (for example the description for the new version, printed in full in chat).
- Target unknown and not derivable from `.claude/deploy.json`: ask once ("Where will this page live?"). Sizes and limits per target: [reference.md](reference.md).

## Step 0: Know the product (don't guess)

Read and note:
- What it is, the core features, how it is used (README, spec, source, the running app).
- Platform (browser, download, phone) and orientation/aspect ratio (from viewport or canvas code).
- Where every visible asset came from (own drawings, third-party packs, icon sets, fonts, procedural code, model-generated). Needed for credits and the disclosure.
- Anything unclear: ask the product owner. Never fill a gap with a plausible-sounding feature.

## Step 1: Description

- English unless the owner says otherwise; written for the user, not the team. Every claim maps to a feature that exists in the current build.
- Structure: one-line hook; a short paragraph on what it is and why someone would use it; "How it works" (or "How to play") as 3-6 bullets of real actions; credits; optional privacy line ("no account, no ads, no tracking") only if true.
- Format per target (HTML fragment for itch and web pages, plain text with character limits for app stores): [reference.md](reference.md).
- Product copy speaks as the product: calm, concrete, no first person, no AI phrasing ("seamless", "unlock your potential", stacked adjectives).
- Save `promo/store/description.<html|txt>` AND print the full text in chat. Uploads are manual; the human needs the text, not a file path.

## Step 2: Screenshots

- 3-5 DIFFERENT screens from the real build: start, the core action, a result or success state, one detail screen. Orientation matches the product.
- Script the capture: serve the build, set the viewport, reach each screen (dev-only URL toggles help), save `promo/store/01-<name>.png`, `02-...`. Ask the human to reach screens that need real use.
- No browser tooling: headless Chrome or Edge, `--headless=new --window-size=W,H --virtual-time-budget=4000 --screenshot=out.png <url>`, on a copy of the page that injects the needed state.
- Commit the screenshot script, so screenshots can be regenerated for the next version.
- Never retouch a screenshot to show something the app doesn't do.

## Step 3: Cover / feature graphic / hero image - three phases

Hard rule: it must look like the product. Use real renders and real assets only (the app's own drawing code, its sprites or components, screenshots). No generated images, not even as a background.

1. **Discover.** Generate three truly random strings with a script (`python -c "import secrets; print([secrets.token_hex(6) for _ in range(3)])"`) and derive one direction from each: composition, title hierarchy, palette (from the product's own palette), tone. Why a script: a model picking "randomly" quietly picks what it likes. Write one paragraph per concept plus one sentence on how it is rendered from real assets. Show all three; the product owner picks or mixes. Don't render before the pick.
2. **Define.** Write the final brief to `promo/store/iter/brief.md`. Render it as a local HTML/canvas page exported to PNG at the target size; if the product exposes its own drawing functions or components, call them so the image always matches the current design. Run the `isolated-critic` skill with: the PNG; "<target> cover image for <what it is>, seen by <who, where>"; direction constraints = the chosen concept in two sentences + "must look like the product"; display condition from [reference.md](reference.md) (e.g. "readable at 210 px wide"); role "strict art director for store assets"; log to `promo/store/iter/critique.md`.
3. **Deliver.** Remove everything without a purpose. Last pass for AI tells: generic gradients, glow everywhere, symmetry for its own sake, a stock font. Save `promo/store/cover.png`. Commit the generator script (usage in its header comment) plus `brief.md` and `critique.md`; don't commit iteration PNGs.

Show the variants to the human on one local page: build `promo/store/iter/overview.html` that references the PNGs by relative path (enlarged and at real size), and give its path. Why: the human does not see images the agent opened itself.

## Step 4: Metadata suggestions (in chat)

Per target fields from [reference.md](reference.md): short description or tagline (in a code block for copying), category or genre, up to 10 lowercase tags from real features and mood, release status, embed or display settings where relevant.

**AI-use disclosure:** list everything visible by origin (own work, third-party asset, procedural code, model-generated). Recommend declaring every category that contains any model-made item, and mention AI-assisted code separately. The product owner decides. Why: platforms judge by origin, not format, and being seen as hiding it costs more than declaring it.

**Credits:** every third-party asset, font and sound with author, licence and link. Unknown origin: say "unknown - check before publishing", never invent an author.

## Step 5: `promo/store/README.md`

What each file is, the checklist of manual settings on the target, and the line "Uploads are manual - the deploy tool pushes only the build."

## Step 6: Report, in the order the store form asks

Image folder path; tagline; category and status; display/embed settings; the full description text; tags; credits; the disclosure question for the owner; cover score and rounds plus the overview page path.

Visibility lifecycle to remind the owner of: keep a new page private or in draft until the build is live and tested on the page itself, then make it public.

## Boundaries

- Does not create the store page, change its settings, upload anything, or publish.
- Does not decide the disclosure, price, visibility or age rating: proposes, the owner decides.
- Does not bump versions. Commits only its own files under `promo/store/` (and the scripts that generate them).
