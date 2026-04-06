# MichaWeb Workflow — Who Does What

---

## What YOU do

1. **Find leads** — Search Google Maps for businesses without websites
2. **Make contact** — Walk in, email, DM, or call with the demo link
3. **Collect info from the client** (text, call, or in person):
   - Business name (exact spelling)
   - Phone number
   - Address
   - Hours
   - Services they offer (with prices if they have them)
   - Any photos (have them text you pics)
   - What they want customers to do (call, book, walk in)
4. **Send revisions back** — When client says "change X," tell Claude
5. **Collect payment** — $499 upfront via Venmo/Zelle/CashApp/PayPal
6. **Set up recurring $49/mo** — PayPal subscription or monthly Venmo invoice
7. **Buy the domain** — Client pays $10-15/year on Namecheap (their cost)
8. **Ask for referrals** — "Know anyone else who needs a site?"

---

## What you send to CLAUDE

When you get a new client, paste this:

```
New client:
- Business: [name]
- Type: [barber, restaurant, lawn care, etc.]
- Phone: [number]
- Address: [full address]
- Hours: [their hours]
- Services: [list what they offer, with prices if they have them]
- CTA: [what should customers do — call, book, walk in]
- Notes: [anything else — colors they like, vibe, etc.]
```

For revisions:

```
Client [name] wants these changes:
- [change 1]
- [change 2]
```

---

## What CLAUDE does

1. **Builds the site** — Full custom site based on the info you provide
2. **Deploys to Netlify** — Gives you a live URL to share with the client
3. **Makes revisions** — You relay client feedback, Claude edits and redeploys
4. **Points domain** — When client buys a domain, Claude sets up the DNS on Netlify
5. **Monthly updates** — You tell Claude what the client wants changed, Claude does it

---

## The flow for each client

```
You find lead
    ↓
You contact them (show demo)
    ↓
They say yes
    ↓
You collect their info
    ↓
You paste info to Claude → Claude builds site → gives you live link
    ↓
You send link to client
    ↓
Client wants changes → You tell Claude → Claude fixes → new link
    ↓
Client approves → You collect $499
    ↓
Claude deploys final version with their domain
    ↓
Client pays $49/mo → You tell Claude if anything needs updating
```
