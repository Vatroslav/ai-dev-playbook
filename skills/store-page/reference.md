# store-page: per-target reference

Purpose: formats, sizes and fields per target, so the main skill stays generic.
Read when: the store-page skill needs a size, a text limit or a field list.

**Sizes and limits change.** Before producing final assets, open the target's current asset-spec page and check the numbers below. If they differ, the spec page wins; update this file.

## Targets

| Target | Description format | Cover / feature image | Screenshots | Notes |
|---|---|---|---|---|
| itch.io | HTML fragment (template below) | Cover 630x500 (shown small in listings: check readability at about 210 px wide) | 3-5, any size, orientation of the app | Embed size must match orientation (e.g. portrait 450x800); fullscreen button on; mobile friendly only if it really works on phones. |
| Google Play | Plain text: short description + full description, both with character limits | Feature graphic 1024x500 | Phone (and tablet if supported) screenshots in the required aspect ratios | Check the store's policy on AI-generated content and its data-safety form. |
| Apple App Store | Plain text: subtitle, promotional text, description, keywords, each with limits | No cover; the first screenshots and app preview act as the cover | Required device sizes per current spec | Check the current screenshot size table; it changes with new devices. |
| Landing page | HTML/Markdown sections | Hero image at the layout's width (provide 1x and 2x) | 3-5 in context | Add Open Graph image (`og:image`) and title/description meta. |

## itch.io description template (HTML fragment)

```html
<p><em>One-line hook.</em></p>
<p>Short paragraph: what it is and why someone would use or play it.</p>
<p><strong>How it works</strong></p>
<ul>
  <li><strong>Action</strong> &mdash; plain-language control or step</li>
</ul>
<p><strong>Credits</strong></p>
<ul>
  <li><a href="https://example.com" target="_blank" rel="noopener">Author / pack name</a> (licence)</li>
</ul>
```

## App-store text template (plain text)

```
Short description / subtitle (one line, within the limit):
<what it does for whom>

Full description:
<hook sentence>

<2-3 short paragraphs: the problem, what the app does, what makes it different>

Features:
- <real feature>
- <real feature>

<privacy line, only if true: no account, no ads, no tracking>
```

## Metadata fields to propose

- **Tagline / short description:** one line, concrete benefit, no superlatives.
- **Category / genre:** one primary.
- **Tags / keywords:** up to 10, lowercase, from real features and mood; no competitor names.
- **Release status:** released, early access, in development.
- **Display settings (web embeds):** orientation-matched size, fullscreen on, autostart off, scrollbars off.

## AI-use disclosure checklist

List every visible element with its origin:

| Element | Origin | Counts as generative AI? |
|---|---|---|
| Characters, icons, illustrations | own / third-party pack / model-generated | only if model-generated |
| Fonts | licensed font / drawn in code / model-generated | a font drawn in code from model output still counts as graphics |
| Sounds and music | own / library / synthesised in code / model-generated | only if model-generated |
| Text and copy | own / model-drafted | follow the platform's definition |
| Code | own / AI-assisted | usually a separate question; declare honestly if asked |
| Cover composited by a script from real assets | script + real assets | no |

Recommend declaring every category that contains any model-made item. The product owner decides.
