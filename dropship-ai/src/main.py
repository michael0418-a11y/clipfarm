"""
Dropship AI — Main CLI orchestrator. $0 startup edition.

Usage:
    python main.py setup                  — $0 launch guide (start here!)
    python main.py dashboard              — Show operations dashboard
    python main.py brand <niche>          — Generate a brand bible
    python main.py rewrite                — Rewrite product descriptions (dry run)
    python main.py rewrite --live         — Push rewritten descriptions to store
    python main.py seo                    — Optimize all product SEO (dry run)
    python main.py seo --live             — Push SEO changes to store
    python main.py trends <niche>         — Analyze trending products
    python main.py competitors <niche> <url1> <url2> ...
    python main.py respond <email> <name> <message>
    python main.py organic                — Generate 10 free TikTok content ideas
    python main.py organic schedule       — 30-day organic posting schedule
    python main.py tiktok <product>       — Generate TikTok ad scripts (for later)
    python main.py calendar               — Generate 30-day content calendar
    python main.py emails <type>          — Generate email sequence
    python main.py emails all             — Generate all email sequences
    python main.py pricing                — AI pricing optimization (dry run)
"""
import sys
import json


def cmd_dashboard():
    from dashboard import show_dashboard
    show_dashboard()


def cmd_rewrite(live: bool = False):
    from description_rewriter import rewrite_all_products
    mode = "LIVE" if live else "DRY RUN"
    print(f"Product Description Rewriter [{mode}]\n{'='*50}")
    results = rewrite_all_products(dry_run=not live)
    print(f"\nProcessed {len(results)} products.")
    if not live:
        print("Run with --live to push changes to your store.")


def cmd_brand(niche: str):
    from brand_bible import generate_brand_bible
    print(f"Generating Brand Bible for: {niche}\n{'='*50}")
    bible = generate_brand_bible(niche)
    print(json.dumps(bible, indent=2))


def cmd_trends(niche: str):
    from trend_monitor import analyze_trends
    print(f"Trend Analysis for: {niche}\n{'='*50}")
    trends = analyze_trends(niche)
    for i, t in enumerate(trends, 1):
        print(f"\n{i}. {t.get('product_name', 'Unknown')}")
        print(f"   Why: {t.get('trend_reason', '?')}")
        print(f"   Price: {t.get('recommended_price', '?')}")
        print(f"   Risk: {t.get('risk_score', '?')}/10")
        print(f"   Supplier: {t.get('supplier_recommendation', '?')}")


def cmd_competitors(niche: str, urls: list[str]):
    from trend_monitor import analyze_competitors
    print(f"Competitor Analysis: {niche}\n{'='*50}")
    gaps = analyze_competitors(niche, urls)
    for i, g in enumerate(gaps, 1):
        print(f"\n{i}. Gap: {g.get('gap', '?')}")
        print(f"   Strategy: {g.get('strategy', '?')}")
        print(f"   Product: {g.get('product_recommendation', '?')}")


def cmd_respond(email: str, name: str, message: str):
    from customer_service import respond_to_customer
    print(f"Generating response for {name}...\n{'='*50}")
    response = respond_to_customer(email, name, message)
    print(response)


def cmd_organic(subcmd: str = "ideas"):
    from organic_tiktok import generate_content_ideas, generate_posting_schedule
    if subcmd == "schedule":
        print("30-Day Organic TikTok Schedule (FREE)\n" + "="*50)
        schedule = generate_posting_schedule()
        for day in schedule:
            batch = " [BATCH FILM DAY]" if day.get("batch_film_day") else ""
            print(f"\nDay {day.get('day', '?')}{batch}")
            for post in day.get("posts", []):
                sell = " $" if post.get("selling") else ""
                print(f"  {post.get('time', '?')} — {post.get('format', '?')}: "
                      f"{post.get('concept', '?')}{sell}")
    else:
        print("Organic TikTok Content Ideas (FREE)\n" + "="*50)
        ideas = generate_content_ideas(num_ideas=10)
        for i, idea in enumerate(ideas, 1):
            print(f"\n{'─'*50}")
            print(f"#{i} [{idea.get('format', '?')}] ({idea.get('difficulty', '?')})")
            print(f"  Hook: \"{idea.get('hook', '?')}\"")
            print(f"  Concept: {idea.get('concept', '?')}")
            print(f"  Audio: {idea.get('audio', '?')}")


def cmd_tiktok(product: str):
    from tiktok_ads import generate_ad_variations
    print(f"TikTok Ad Scripts for: {product}\n{'='*50}")
    scripts = generate_ad_variations(product_name=product)
    for i, script in enumerate(scripts, 1):
        print(f"\n{'─'*50}")
        print(f"Ad #{i}: {script.get('framework_used', '?')}")
        primary = script.get("primary_script", {})
        print(f"  Hook: \"{primary.get('hook', '?')}\"")
        print(f"  CTA: \"{primary.get('cta', '?')}\"")
        print(f"  Music: {primary.get('music_suggestion', '?')}")
        for j, alt in enumerate(script.get("alternative_hooks", []), 1):
            print(f"  Alt Hook {j}: \"{alt.get('hook', '?')}\"")


def cmd_calendar():
    from tiktok_ads import generate_content_calendar
    print("30-Day Content Calendar\n" + "="*50)
    calendar = generate_content_calendar()
    for day in calendar:
        print(f"Day {day.get('day', '?'):>2} [{day.get('content_type', '?'):>7}] "
              f"{day.get('concept', '?')}")


def cmd_emails(seq_type: str):
    from email_sequences import generate_email_sequence, generate_all_sequences, SEQUENCES
    if seq_type == "all":
        print("Generating all email sequences...\n")
        all_seqs = generate_all_sequences()
        for name, emails in all_seqs.items():
            print(f"\n{'='*50}")
            print(f"{SEQUENCES[name]['name']} — {len(emails)} emails")
            for email in emails:
                print(f"  {email.get('email_number', '?')}. {email.get('subject_line', '?')}")
    else:
        seq_name = SEQUENCES.get(seq_type, {}).get("name", seq_type)
        print(f"Generating {seq_name} sequence...\n{'='*50}")
        emails = generate_email_sequence(sequence_type=seq_type)
        for email in emails:
            print(f"\nEmail #{email.get('email_number', '?')}")
            print(f"  Subject: {email.get('subject_line', '?')}")
            print(f"  Timing: {email.get('send_timing', '?')}")
            print(f"  CTA: {email.get('cta_text', '?')}")


def cmd_seo(live: bool = False):
    from seo_optimizer import optimize_all_products
    mode = "LIVE" if live else "DRY RUN"
    print(f"SEO Optimization [{mode}]\n{'='*50}")
    results = optimize_all_products(dry_run=not live)
    print(f"\nOptimized {len(results)} products.")
    if not live:
        print("Run with --live to push changes to your store.")


def cmd_setup():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║        DROPSHIP AI — $0 STARTUP LAUNCH GUIDE                 ║
║        Everything below is 100% free                         ║
╚═══════════════════════════════════════════════════════════════╝

═══ THE $0 STACK ═══════════════════════════════════════════════

  Store:      TikTok Shop (FREE) or Square Online (FREE)
  Supplier:   CJDropshipping (FREE — pay per order only)
  Marketing:  Organic TikTok + Instagram Reels (FREE)
  Email:      Mailchimp (FREE up to 500 contacts)
  AI:         Claude Code (you already have it)
  Design:     Canva Free + Google Fonts
  Analytics:  TikTok Analytics + Google Analytics (FREE)
  ─────────────────────────────────────────────────────
  Total:      $0/month until your first sale

═══ PHASE 1: SET UP YOUR FREE STORE (Day 1) ═══════════════════

  OPTION A — TikTok Shop (RECOMMENDED for $0)
  ─────────────────────────────────────────────
  Why: Built-in audience of 1.5B users. Algorithm pushes new
  creators. Customers buy WITHOUT leaving TikTok.

  1. Download TikTok → Create account (or use existing)
  2. Go to Settings → Account → Switch to Business Account
  3. Go to seller-us.tiktok.com → Register as a seller
  4. You need:
     - SSN or EIN (for US sellers)
     - Bank account for payouts
     - Phone number
  5. Once approved, you can list products directly

  OPTION B — Square Online (FREE website)
  ────────────────────────────────────────
  Why: Free forever plan. Real .com store. Only pay when you sell.

  1. Go to squareup.com/online-store
  2. Sign up (free, no credit card)
  3. Pick a template → Customize with your brand colors
  4. You pay: 2.9% + $0.30 per transaction (only when you sell)

  OPTION C — WooCommerce (FREE, technical)
  ─────────────────────────────────────────
  If you already have web hosting, WooCommerce is 100% free.
  Needs: PHP hosting (some providers offer free tiers)

═══ PHASE 2: CONNECT FREE SUPPLIER (Day 1) ════════════════════

  CJDropshipping — 100% FREE
  ───────────────────────────
  1. Go to cjdropshipping.com → Create free account
  2. NO subscription. NO monthly fees. NO credit card needed.
  3. You pay ONLY when a customer orders:
     - Product cost (wholesale price)
     - Shipping ($2-8 depending on product/speed)
  4. They have US warehouses (3-7 day shipping)
  5. Connect to TikTok Shop or your store
  6. Browse products → List the ones you want to sell

  Alternative: EPROLO (also 100% free)
  ─────────────────────────────────────
  - Free app for TikTok Shop and Shopify
  - Free branding (your logo on packaging)
  - Pay per order only

═══ PHASE 3: BRAND IDENTITY (Day 1-2) ═════════════════════════

  Step 1: Generate your brand (FREE via Claude Code)
          python main.py brand "LED/Red Light Therapy"

  Step 2: Create free logo
          - Canva.com (free) → Search "minimalist logo"
          - OR use your brand name in Cormorant Garamond font
            (that's literally what luxury brands do)

  Step 3: Brand colors from your Brand Bible
          Novara palette: #1A1A2E, #F5F0EB, #C4956A

═══ PHASE 4: LIST PRODUCTS (Day 2-3) ══════════════════════════

  1. On CJDropshipping, search: "LED face mask" or "red light therapy"
  2. Pick 5-10 products to start (don't overload)
  3. Import to your TikTok Shop / Square store
  4. Use Claude Code to rewrite descriptions:
     python main.py rewrite

  Pricing rule: Supplier cost x 2.5 to 3x = your price
  Example: $70 LED mask → sell for $179-$209

═══ PHASE 5: ORGANIC TIKTOK GROWTH (Day 3+) ═══════════════════

  THIS IS WHERE YOU MAKE MONEY WITH $0

  1. Generate content ideas (FREE):
     python main.py organic

  2. Generate 30-day posting schedule (FREE):
     python main.py organic schedule

  3. Filming setup (FREE):
     - Use your phone (that's it)
     - Film near a window for natural light
     - Film 10+ videos in one session (batch filming)

  4. Posting strategy:
     - Post 2-3x per day (consistency > quality at first)
     - Best times: 7AM, 12PM, 7PM (your timezone)
     - Use trending sounds (check TikTok's Sound Library)
     - First 3 seconds = everything (use the hooks we generate)

  5. Content that works with $0:
     - "I tested this $200 LED mask for 30 days" (document journey)
     - Skincare routine videos featuring the product
     - Myth-busting: "This is what red light actually does to your skin"
     - ASMR unboxing and product demos
     - Stitch/Duet viral skincare videos

  6. DO NOT hard-sell. TikTok suppresses ads.
     Instead: provide value → build trust → link in bio

═══ PHASE 6: FREE EMAIL LIST (When you get traffic) ═══════════

  1. Mailchimp.com — FREE up to 500 contacts
  2. Create a simple landing page (free with Mailchimp)
  3. Offer: "Free LED Therapy Guide" in exchange for email
  4. Generate email sequences:
     python main.py emails abandoned_cart
     python main.py emails welcome

═══ WHEN TO START SPENDING MONEY ═══════════════════════════════

  Don't spend $1 until you've validated with organic sales:

  Milestone 1: First 1,000 TikTok followers → Keep posting free
  Milestone 2: First 5 organic sales → Consider TikTok ads ($20/day)
  Milestone 3: First $1,000 revenue → Upgrade to Shopify ($39/mo)
  Milestone 4: First $5,000 revenue → Scale ads to $50-100/day
  Milestone 5: First $10,000 revenue → Hire a VA ($5/hr on Fiverr)

═══ THE MATH ═══════════════════════════════════════════════════

  LED Face Mask example:
  - CJ cost: $70 (product + shipping)
  - Your price: $199
  - TikTok Shop fee: ~5% ($10)
  - Profit per sale: $119

  To make $1,000/month: sell 9 masks
  To make $10,000/month: sell 84 masks (3/day)
  To make $100,000/month: sell 840 masks (28/day)

  28 sales/day is very achievable once you have
  50K+ TikTok followers and consistent content.

═══ QUICK COMMANDS ═════════════════════════════════════════════

  python main.py brand "LED/Red Light Therapy"   # Brand identity
  python main.py organic                         # Free content ideas
  python main.py organic schedule                # 30-day free plan
  python main.py trends "LED Therapy"            # Find products
  python main.py rewrite                         # Upgrade descriptions
  python main.py emails abandoned_cart           # Email sequences
  python main.py respond email name "message"    # Customer service

Start now: python main.py organic
""")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    match command:
        case "dashboard":
            cmd_dashboard()
        case "rewrite":
            cmd_rewrite(live="--live" in sys.argv)
        case "brand":
            niche = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "LED/Red Light Therapy"
            cmd_brand(niche)
        case "trends":
            niche = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "LED/Red Light Therapy"
            cmd_trends(niche)
        case "competitors":
            niche = sys.argv[2] if len(sys.argv) > 2 else "LED Therapy"
            urls = sys.argv[3:] if len(sys.argv) > 3 else []
            cmd_competitors(niche, urls)
        case "respond":
            if len(sys.argv) < 5:
                print("Usage: python main.py respond <email> <name> <message>")
                return
            cmd_respond(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
        case "organic":
            subcmd = sys.argv[2] if len(sys.argv) > 2 else "ideas"
            cmd_organic(subcmd)
        case "tiktok":
            product = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Professional LED Face Mask"
            cmd_tiktok(product)
        case "calendar":
            cmd_calendar()
        case "emails":
            seq_type = sys.argv[2] if len(sys.argv) > 2 else "abandoned_cart"
            cmd_emails(seq_type)
        case "seo":
            cmd_seo(live="--live" in sys.argv)
        case "pricing":
            print("Pricing optimizer requires a cost map. Use in Python:\n"
                  "  from pricing_optimizer import optimize_store_prices\n"
                  "  optimize_store_prices({product_id: cost}, target_margin=40)")
        case "setup":
            cmd_setup()
        case _:
            print(f"Unknown command: {command}")
            print(__doc__)


if __name__ == "__main__":
    main()
