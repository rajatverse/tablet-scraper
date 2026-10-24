# TopTablets Agent Guidelines

Welcome to the **Tablet Scraper & WordPress/WooCommerce Publisher** workspace.

Whenever working on scraping, normalization, template generation, or WordPress publishing, all agents and contributors MUST adhere to the workspace SEO rules:
👉 [SEO Automation Rules](file:///c:/Users/praja/OneDrive/Documents/Projects/Tablet%20Scraper/.agents/rules/seo-automation-rules.md)

### Core Mandates:
1. **Never Output Thin Scraped Content**: Always augment raw specs with the Hardware Bento 4x2 matrix, practical user takeaways, and cross-store savings (No Geekbench/AnTuTu synthetic scores).
2. **Strict Grounding**: Specs must come from deterministic parsers (`parsers/spec_normalizer.py`). No AI hallucinations for specs or compatibility.
3. **Link Hygiene**: All outbound commercial links must include `rel="nofollow sponsored"`.
4. **Clean DOM**: Avoid duplicate DOM IDs. Ensure all components use semantic tags (`<section>`, `<dl>`, `<dt>`, `<dd>`).
5. **Dynamic Search-Intent Metadata**: Maintain SEO title formats (`{Model} Specs, Lowest Price & Review | TopTablets`) and 150-char meta descriptions.
