---
name: brand-guard
description: Verify Amazon Brand Registry health — who really owns the brand, whose logins hold Administrator/Rights Owner, which seller accounts hold selling roles, and whether the USPTO record matches. Use when the user bought or sold a brand, asks "do I own my brand on Amazon", or before/after any brand transfer.
---

# Brand ownership verification (Brand Registry + USPTO)

Functional access and legal ownership are different things. A seller can have
every brand feature working while the trademark legally belongs to someone else
— common after buying a brand or store. This skill verifies both layers.

## Layer 1 — Functional evidence (API, no browser needed)
These are gated on Brand Registry, so a success IS evidence:
- A+ Content API works? `GET /aplus/2020-11-01/contentDocuments` — approved Brand
  Story / Premium A+ content ⇒ recognized rights owner.
- Search Query Performance data flows (or returns DATA_IN_PROGRESS rather than
  SELLER_NOT_ELIGIBLE) ⇒ Brand-Registered seller.
- Catalog `brand` attribute on the ASINs matches, and the seller's own listing
  contributions set it without brand-gating errors.

## Layer 2 — Brand Registry internals (browser; read-only)
brandregistry.amazon.com, with the user's session:
1. **Manage → Manage intellectual property**: which trademark(s) the brand is
   connected to — office, number, type, status. Record the registration number.
2. **Settings (gear) → User permissions**: EVERY connected login and its roles
   (Administrator / Rights Owner / Registered Agent). Red flags: previous owner
   still Administrator (they can remove YOUR roles), unknown emails, only one
   Administrator total (Amazon recommends ≥2).
3. **Manage → Manage selling roles**: every Seller/Vendor Central account with
   Brand Representative or Reseller roles. Red flag: seller accounts from a
   previous owner's network still holding Brand Representative (full listing +
   brand-benefits authority).
4. Check **Open invitations** and **Access requests** tabs on both pages.

## Layer 3 — USPTO truth (public, no login)
TSDR: `https://tsdr.uspto.gov/#caseNumber=<REG#>&caseType=US_REGISTRATION_NO&searchType=statusSearch`
- **Current Owner(s) Information**: the legal owner of record. Does it match the
  user's entity?
- **Assignment Abstract Of Title**: "None recorded" after a purchase means the
  assignment was NEVER filed — whatever the parties believe, the record still
  supports the seller's claim. Recordation is via USPTO ETAS (~$40, days).

## Transfer sequencing (after buying a brand)
1. Record the assignment at USPTO ETAS; wait for TSDR "Current Owner" to update
   (days–2 weeks).
2. THEN open a Brand Registry case ("Update your brand registration / trademark
   information") with the recordation reel/frame.
3. ONLY THEN clean up roles: demote/remove the previous owner's logins and
   decide their seller accounts' selling roles.
Never strip the previous owner's roles while USPTO still shows them as owner —
in a dispute, Amazon sides with the USPTO record.

## Output
A findings table (verified facts with sources), a red-flag list, and a sequenced
action checklist. This skill NEVER changes roles itself — role removal is a
business/legal decision the user executes.
