# Deal Drop

Website Design Prompt

I want to build a modern web application that aggregates promotional deals scraped from Telegram promotion channels. The website should help users quickly discover discounts, promotions, sales, and special offers, especially those available near their current location.

The website should feel like a modern deals-discovery platform, rather than looking like a Telegram scraper or a generic admin dashboard.

Overall Design

Use a clean, modern, premium UI with a strong focus on discoverability.

Think of the visual experience as a combination of:

A modern deal/coupon marketplace

Google Maps for the "Near Me" feature

A social-media-style discovery feed

A lightweight SaaS/product interface

The design should be visually appealing and suitable for a portfolio project.

Use plenty of whitespace, rounded cards, subtle shadows/borders, clear typography, and polished micro-interactions.

Avoid making the website look overly corporate or like an internal dashboard.

Main Navigation

The top navigation should contain:

Logo / website name

Discover

Near Me

Categories

Search

Optional saved/favourite deals

Location indicator

Example:

[ DEALHUB ]     Discover    Near Me    Categories       🔍 Search    📍 Singapore


The navigation should remain simple and uncluttered.

Homepage

The homepage should focus on discovering interesting deals.

At the top, have a large heading such as:

Discover the best deals around you.

Below it, have a prominent search bar:

🔍 Search for deals, restaurants, shops, brands...

Under the search bar, display category chips:

🔥 Trending
📍 Near Me
🍔 Food
🛍 Shopping
🎮 Entertainment
💄 Beauty
✈️ Travel
🏨 Hotels


The category chips should be horizontally scrollable on mobile.

Deal Cards

The main content should consist of visually attractive promotion cards.

Each card should contain:

Promotion image if available

Merchant/store name

Promotion title

Short description

Discount amount or promotional offer

Location

Distance from the user

Expiry date

Category

Time since the promotion was scraped

Original Telegram source

Example:

┌─────────────────────────────────────┐
│                                     │
│          PROMOTION IMAGE            │
│                                     │
├─────────────────────────────────────┤
│ UNIQLO                         🛍️   │
│                                     │
│ 30% OFF Selected Items              │
│                                     │
│ Save 30% on selected products.      │
│                                     │
│ 📍 VivoCity · 1.2 km                │
│ ⏰ Ends 31 Aug                      │
│                                     │
│ Telegram · 2 hours ago              │
│                                     │
│              [ View Deal → ]        │
└─────────────────────────────────────┘


Cards should have subtle hover animations.

For example:

Slightly lift the card

Increase shadow

Make the "View Deal" button more prominent

Do not overload cards with too much information.

Featured / Trending Section

Near the top of the homepage, include a horizontal "Trending Deals" section.

Example:

🔥 Trending Deals

[ Deal Card ] [ Deal Card ] [ Deal Card ] [ Deal Card ]


These should highlight promotions that are:

Recently posted

Popular

High discount

Expiring soon

Use visually prominent discount badges such as:

30% OFF
$10 OFF
BUY 1 GET 1
50% OFF


Near Me Feature

"Near Me" should be one of the main features of the website.

Create a dedicated page accessible from the main navigation.

The page should use a map-first interface.

Example:

┌────────────────────────────────────────────────────┐
│ ← Near Me                              🔍 Search   │
├────────────────────────────────────────────────────┤
│                                                    │
│                  MAP                               │
│                                                    │
│          📍        🏷️                             │
│                                                    │
│                    📍                              │
│                              🏷️                    │
│                                                    │
│       📍                                            │
│                                                    │
├────────────────────────────────────────────────────┤
│ Deals near you                                    │
│                                                    │
│ [Deal]                                             │
│ [Deal]                                             │
│ [Deal]                                             │
└────────────────────────────────────────────────────┘


The map should display promotion markers based on the merchant's location.

Different categories can optionally have different marker icons.

For example:

🍔 Food

🛍 Shopping

🎮 Entertainment

💄 Beauty

🏨 Hotels

When the user clicks a map marker, display a small deal preview card.

Example:

┌──────────────────────────────┐
│ UNIQLO                       │
│                              │
│ 30% OFF Selected Items       │
│ 📍 350m away                 │
│ ⏰ Ends today                │
│                              │
│ [ View Deal ]                │
└──────────────────────────────┘


The user should also be able to switch between:

[ Map ] [ List ]


Deal Detail Page

When a user clicks a promotion, open a dedicated deal detail page.

The page should contain:

Large promotion image

Merchant name

Promotion title

Discount

Full description

Location

Map

Opening hours if available

Expiry date

Terms and conditions

Original Telegram post

Date/time scraped

Button to visit the original promotion

Example structure:

← Back

┌─────────────────────────────────────┐
│                                     │
│         PROMOTION IMAGE             │
│                                     │
└─────────────────────────────────────┘

30% OFF Selected Items

UNIQLO

🔥 30% OFF

Save 30% on selected items...

📍 VivoCity
📏 1.2 km away
⏰ Ends 31 Aug

[ View Original Promotion ]

─────────────────────────────────────

📍 Location

              MAP

─────────────────────────────────────

Source
Telegram · Posted 2 hours ago


Search

The search experience should be prominent and fast.

Users should be able to search by:

Merchant

Brand

Promotion

Category

Location

Keywords

For example:

Search: "Nike"

Results

Nike
────────────────────────────

30% OFF Shoes
📍 Orchard · 2.1 km

20% OFF Members Sale
📍 Jewel · 4.8 km

$50 OFF Selected Products
📍 VivoCity · 5.2 km


Include filters such as:

Distance
Category
Discount
Expiry
Newest


Categories

Create a category browsing page.

Categories could include:

Food & Dining

Shopping

Beauty

Entertainment

Travel

Hotels

Electronics

Fitness

Services

Other

Each category should have an icon and attractive visual treatment.

Visual Style

The website should feel modern and polished.

Use:

Large rounded cards

Soft shadows

Subtle borders

Generous whitespace

Modern sans-serif typography

Large, readable headings

Clear hierarchy

Subtle animations

Smooth hover states

Responsive design

Avoid:

Dense tables

Excessive gradients

Too many colours

Old-fashioned coupon-site aesthetics

Excessive Telegram branding

Generic Bootstrap-looking components

The website should feel like a real consumer-facing product, not a prototype.

Colour Direction

Use a mostly neutral background with one strong accent colour for important actions and discount information.

The accent colour should be used for:

Buttons

Active navigation

Deal badges

Map markers

Important links

Keep the rest of the interface relatively neutral so that the promotion cards and discount values stand out.

Responsive Design

The website must work well on:

Desktop

Use a spacious layout with multiple deal cards per row.

Example:

[ Deal ] [ Deal ] [ Deal ] [ Deal ]


Tablet

[ Deal ] [ Deal ] [ Deal ]


Mobile

Use a single-column feed:

[ Deal ]

[ Deal ]

[ Deal ]


The mobile version should have a bottom navigation bar:

🏠 Home     📍 Near Me     🔍 Search     ❤️ Saved


The "Near Me" feature should be especially easy to access on mobile.

Important Product Concept

The key value proposition is:

Find promotions from Telegram channels without having to browse through Telegram manually.

The website should transform messy Telegram promotion messages into clean, searchable, location-aware deal cards.

The experience should therefore prioritise:

Discovering deals

Finding deals nearby

Searching for specific promotions

Seeing whether a deal is still valid

Quickly accessing the original promotion

The final design should feel like a polished "deal discovery engine for Singapore", where the unique selling point is that promotions are automatically collected from Telegram and organised into a useful location-aware interface.

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://promo-radar-scan.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/e281a63f-a125-43d8-8490-0510b853b97b).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
