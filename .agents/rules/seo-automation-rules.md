# 🤖 TopTablets Automated SEO & Content Quality Rules

These rules govern the scraping, parsing, template generation, and WordPress publishing pipelines for **TopTablets.in**. They enforce compliance with Google Search Central guidelines (Core Search, Quality Evaluator Guidelines, Scaled Content Abuse prevention, and Generative AI Search / RAG optimization).

---

## 1. Outbound & Internal Link Hygiene
* **Rule 1.1 (Mandatory Sponsored Tags):** Every external affiliate link (Amazon, Flipkart, etc.) MUST have `rel="nofollow sponsored"` and `target="_blank"`. Never output raw un-attributed commercial links.
* **Rule 1.2 (Descriptive Internal Links):** Never use generic anchor text like *"click here"* or *"read more"*. Always use descriptive anchors (e.g., *"Compare {Model A} vs {Model B}"*, *"View Full Hardware Specifications"*).

---

## 2. Content Quality & Anti-Clustering Rules (Beating Thin Affiliate Flags)
* **Rule 2.1 (Non-Commodity Data Layer):** Never publish raw scraped specs without adding proprietary data layers:
  1. Live Cross-Store Price Matrix with calculated savings (`₹ Savings` and `% OFF`).
  2. Silicon & Architecture Context (Fabrication node, memory architecture, AI engines; no synthetic benchmark scores).
  3. Hardware Bento Matrix (Display lamination, stylus latency, PWM, charging wattage).
* **Rule 2.2 (No Repetitive Boilerplate Fallbacks):** Never allow generic fallback text (e.g., *"A well-rounded tablet for students..."*) across multiple products. Model-specific verdicts, pros/cons, and target audiences must be populated in `TABLET_AUGMENTED_SPECS`.
* **Rule 2.3 (Factual Grounding):** All hardware specifications must originate from deterministic regex normalization (`spec_normalizer.py`). Generative AI or LLMs must NEVER be allowed to hallucinate or invent specs, battery speeds, or stylus compatibility.

---

## 3. Technical SEO & Crawl Budget Rules
* **Rule 3.1 (Server-Side Rendered Critical Data):** All primary specs, price cards, editorial takeaways, and verdicts must be present in the initial server-rendered HTML string. Never defer critical text behind client-side-only JavaScript or AJAX.
* **Rule 3.2 (Clean DOM & Unique IDs):** Every generated HTML template must maintain strictly unique DOM IDs (`#tt-deals`, `#tt-verdict`, `#hardware-bento`, `#tt-specs`). Duplicate IDs break Googlebot rendering and autonomous AI shopping agents.
* **Rule 3.3 (Clean Permalinks & Canonicalization):** Keep product slugs concise (e.g., `/product/apple-ipad-mini-7th-gen/`). Strip messy retailer variant suffixes (`8-3-inch-128gb-wifi`). Consolidate variants into one master product page with dynamic chips.
* **Rule 3.4 (Permanent Redirects):** Any migrated or altered URL must return an HTTP `301` permanent redirect.
* **Rule 3.5 (No Soft 404s):** Out-of-stock products must either remain useful comparison pages or return true `404` / `410 Gone`. Never return `HTTP 200 OK` on empty query results.
* **Rule 3.6 (Faceted Crawl Filter in robots.txt):** Prevent crawl budget waste by disallowing query strings (`/*?*filter_*`, `/*?*orderby=*`, `/?s=`) and transaction endpoints (`/cart/`, `/checkout/`).

---

## 4. Metadata & Structured Data (SERP Appearance)
* **Rule 4.1 (Dynamic Search-Intent Titles):** Format product titles around buyer search intent:
  `{Brand} {Model} Price in India, Full Specs & Comparison | TopTablets`
* **Rule 4.2 (High-Converting Meta Descriptions):** Auto-generate 150–160 character meta descriptions summarizing lowest live price, key processor/display specs, and verified deal status.
* **Rule 4.3 (JSON-LD Product Schema):** Output valid Schema.org `Product` with `AggregateOffer` (lowPrice, highPrice, priceCurrency "INR", inStock). Ensure schema pricing strictly matches on-page visible pricing.
* **Rule 4.4 (Image Alt Tags & Layout Shift):** All product images must include descriptive `alt` tags (`{brand} {model} {color} view`) and explicit `width` and `height` attributes to maintain zero Cumulative Layout Shift (CLS).

---

## 5. Transparency & E-E-A-T Disclosures
* **Rule 5.1 (Visible Affiliate Disclosure):** Maintain an editorial and affiliate disclosure banner (`.tt-editorial-disclosure`) explaining automated price tracking and commission links.
* **Rule 5.2 (Methodology Sourcing):** Link directly to `/how-we-evaluate-tablets/` explaining hardware evaluation standards and pricing algorithms.
