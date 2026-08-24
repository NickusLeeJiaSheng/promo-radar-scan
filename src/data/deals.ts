import fashionImg from "@/assets/deal-fashion.jpg";
import foodImg from "@/assets/deal-food.jpg";
import cafeImg from "@/assets/deal-cafe.jpg";
import hotelImg from "@/assets/deal-hotel.jpg";

export type CategoryId =
  | "food"
  | "shopping"
  | "beauty"
  | "entertainment"
  | "travel"
  | "hotels"
  | "electronics"
  | "fitness"
  | "services";

export type Category = {
  id: CategoryId;
  label: string;
  emoji: string;
};

export const categories: Category[] = [
  { id: "food", label: "Food & Dining", emoji: "🍔" },
  { id: "shopping", label: "Shopping", emoji: "🛍" },
  { id: "beauty", label: "Beauty", emoji: "💄" },
  { id: "entertainment", label: "Entertainment", emoji: "🎮" },
  { id: "travel", label: "Travel", emoji: "✈️" },
  { id: "hotels", label: "Hotels", emoji: "🏨" },
  { id: "electronics", label: "Electronics", emoji: "🎧" },
  { id: "fitness", label: "Fitness", emoji: "🏋️" },
  { id: "services", label: "Services", emoji: "🧰" },
];

export const categoryMap = Object.fromEntries(
  categories.map((c) => [c.id, c]),
) as Record<CategoryId, Category>;

export type Deal = {
  id: string;
  merchant: string;
  title: string;
  description: string;
  terms: string;
  offer: string;
  category: CategoryId;
  image?: string;
  location: string;
  address: string;
  distanceKm: number;
  expiry: string;
  expiresSoon?: boolean;
  scrapedAgo: string;
  channel: string;
  openingHours?: string;
  trending?: boolean;
  // Position on the stylised map, in percent
  map: { x: number; y: number };
  originalPost: string;
};

export const deals: Deal[] = [
  {
    id: "uniqlo-30-off",
    merchant: "UNIQLO",
    title: "30% OFF Selected Items",
    description:
      "Save 30% on selected AIRism, HEATTECH and denim styles in-store and online. Members get an extra $5 voucher on spends above $80.",
    terms:
      "Valid on selected items only. Not combinable with other vouchers. While stocks last.",
    offer: "30% OFF",
    category: "shopping",
    image: fashionImg,
    location: "VivoCity",
    address: "1 HarbourFront Walk, #01-14, Singapore 098585",
    distanceKm: 1.2,
    expiry: "31 Aug",
    scrapedAgo: "2 hours ago",
    channel: "@sgpromocodes",
    openingHours: "10:00 – 22:00 daily",
    trending: true,
    map: { x: 24, y: 68 },
    originalPost:
      "🔥 UNIQLO 30% OFF selected items until 31 Aug! VivoCity + online. Extra $5 voucher for members spending $80+",
  },
  {
    id: "ramen-1for1",
    merchant: "Ippudo",
    title: "1-for-1 Signature Ramen",
    description:
      "Buy one Shiromaru Motoaji and get one free, weekdays from 2pm to 5pm. Dine-in only, perfect for a late lunch.",
    terms: "Weekdays 2–5pm. Dine-in only. Cheaper bowl goes free.",
    offer: "BUY 1 GET 1",
    category: "food",
    image: foodImg,
    location: "Mandarin Gallery",
    address: "333A Orchard Rd, #04-02/03, Singapore 238897",
    distanceKm: 2.1,
    expiry: "Ends today",
    expiresSoon: true,
    scrapedAgo: "45 minutes ago",
    channel: "@sgfooddeals",
    openingHours: "11:00 – 21:30 daily",
    trending: true,
    map: { x: 52, y: 30 },
    originalPost: "1-for-1 ramen at Ippudo Mandarin Gallery, weekdays 2-5pm only 🍜",
  },
  {
    id: "coffee-50-off",
    merchant: "Bacha Coffee",
    title: "50% OFF Iced Coffee After 4pm",
    description:
      "Half price on all iced coffees from 4pm to closing. Show the deal at the counter to redeem.",
    terms: "One redemption per customer per day. Takeaway cups only.",
    offer: "50% OFF",
    category: "food",
    image: cafeImg,
    location: "Jewel Changi",
    address: "78 Airport Blvd, #01-227, Singapore 819666",
    distanceKm: 4.8,
    expiry: "15 Sep",
    scrapedAgo: "5 hours ago",
    channel: "@sgcafehunt",
    openingHours: "09:00 – 22:00 daily",
    trending: true,
    map: { x: 80, y: 22 },
    originalPost: "☕ 50% off iced coffee after 4pm at Jewel — all week",
  },
  {
    id: "hotel-staycation",
    merchant: "Marina Bay Suites",
    title: "$120 OFF Weekend Staycation",
    description:
      "Skyline view rooms with breakfast for two, now $120 off on Friday and Saturday nights booked before end of month.",
    terms: "Subject to availability. Blackout dates apply on public holidays.",
    offer: "$120 OFF",
    category: "hotels",
    image: hotelImg,
    location: "Marina Bay",
    address: "10 Bayfront Ave, Singapore 018956",
    distanceKm: 3.4,
    expiry: "30 Sep",
    scrapedAgo: "1 day ago",
    channel: "@staycationsg",
    openingHours: "Check-in from 15:00",
    trending: true,
    map: { x: 63, y: 55 },
    originalPost: "Staycation alert: $120 off weekend skyline rooms 🏙️",
  },
  {
    id: "sephora-20",
    merchant: "Sephora",
    title: "20% OFF Beauty Pass Members",
    description:
      "Beauty Pass members enjoy 20% off almost everything, including new arrivals from cult skincare labels.",
    terms: "Members only. Exclusions apply on selected brands.",
    offer: "20% OFF",
    category: "beauty",
    location: "ION Orchard",
    address: "2 Orchard Turn, #B2-08, Singapore 238801",
    distanceKm: 2.4,
    expiry: "28 Aug",
    expiresSoon: true,
    scrapedAgo: "3 hours ago",
    channel: "@beautydealssg",
    map: { x: 46, y: 36 },
    originalPost: "Sephora Beauty Pass 20% off sitewide 💄",
  },
  {
    id: "golden-village",
    merchant: "Golden Village",
    title: "$8 Movie Tickets All Day Tuesday",
    description:
      "Flat $8 tickets for any 2D screening every Tuesday, including new releases.",
    terms: "Tuesdays only. Excludes Gold Class and IMAX.",
    offer: "$8 TICKETS",
    category: "entertainment",
    location: "Bugis+",
    address: "201 Victoria St, #04-01, Singapore 188067",
    distanceKm: 3.9,
    expiry: "31 Dec",
    scrapedAgo: "8 hours ago",
    channel: "@sgpromocodes",
    map: { x: 58, y: 44 },
    originalPost: "$8 movie tickets every Tuesday at GV 🎬",
  },
  {
    id: "nike-members",
    merchant: "Nike",
    title: "30% OFF Running Shoes",
    description:
      "Selected Pegasus and Invincible styles at 30% off for members, in-store at Orchard.",
    terms: "Members only. While stocks last.",
    offer: "30% OFF",
    category: "shopping",
    location: "Orchard",
    address: "277 Orchard Rd, #01-01, Singapore 238858",
    distanceKm: 2.1,
    expiry: "5 Sep",
    scrapedAgo: "6 hours ago",
    channel: "@sneakerdealssg",
    map: { x: 42, y: 28 },
    originalPost: "Nike 30% off running shoes for members 👟",
  },
  {
    id: "anytime-fitness",
    merchant: "Anytime Fitness",
    title: "First Month Free + No Sign-Up Fee",
    description:
      "New members get their first month free and the $180 joining fee waived across all outlets.",
    terms: "12-month commitment required. New members only.",
    offer: "1 MONTH FREE",
    category: "fitness",
    location: "Tanjong Pagar",
    address: "7 Wallich St, Singapore 078884",
    distanceKm: 1.9,
    expiry: "10 Sep",
    scrapedAgo: "12 hours ago",
    channel: "@fitdealssg",
    map: { x: 36, y: 60 },
    originalPost: "First month free at Anytime Fitness + no joining fee 💪",
  },
  {
    id: "challenger-audio",
    merchant: "Challenger",
    title: "$60 OFF Wireless Earbuds",
    description:
      "Storewide audio clearance with $60 off popular ANC earbuds and $100 off selected headphones.",
    terms: "While stocks last. One unit per customer.",
    offer: "$60 OFF",
    category: "electronics",
    location: "Funan",
    address: "107 North Bridge Rd, #03-08, Singapore 179105",
    distanceKm: 3.1,
    expiry: "2 Sep",
    scrapedAgo: "1 day ago",
    channel: "@techdealssg",
    map: { x: 55, y: 52 },
    originalPost: "$60 off ANC earbuds at Challenger Funan 🎧",
  },
  {
    id: "scoot-fares",
    merchant: "Scoot",
    title: "Fares from $58 to Bangkok",
    description:
      "Two-day flash sale on regional routes including Bangkok, Penang and Ho Chi Minh City.",
    terms: "Travel period Oct–Dec. Baggage not included.",
    offer: "FROM $58",
    category: "travel",
    location: "Online",
    address: "Changi Airport Terminal 1",
    distanceKm: 17.4,
    expiry: "26 Aug",
    expiresSoon: true,
    scrapedAgo: "20 minutes ago",
    channel: "@flightdealssg",
    map: { x: 88, y: 34 },
    originalPost: "✈️ Scoot flash sale — Bangkok from $58 one way",
  },
  {
    id: "kbowl-lunch",
    merchant: "Seoul Table",
    title: "$9.90 Lunch Sets",
    description:
      "Korean lunch sets with soup and banchan at $9.90 from Monday to Friday before 2pm.",
    terms: "Weekday lunch only. Dine-in.",
    offer: "$9.90 SET",
    category: "food",
    location: "Raffles Place",
    address: "6 Raffles Quay, #01-05, Singapore 048580",
    distanceKm: 2.7,
    expiry: "20 Sep",
    scrapedAgo: "9 hours ago",
    channel: "@sgfooddeals",
    map: { x: 50, y: 62 },
    originalPost: "$9.90 Korean lunch sets weekdays 🍚",
  },
  {
    id: "carwash-service",
    merchant: "ShineLab",
    title: "40% OFF Full Car Grooming",
    description:
      "Interior and exterior grooming package with ceramic top-up, 40% off for first-time bookings.",
    terms: "By appointment. First-time customers only.",
    offer: "40% OFF",
    category: "services",
    location: "Kallang",
    address: "51 Kallang Bahru, Singapore 339351",
    distanceKm: 5.6,
    expiry: "18 Sep",
    scrapedAgo: "2 days ago",
    channel: "@sgservicedeals",
    map: { x: 70, y: 68 },
    originalPost: "40% off full car grooming at ShineLab 🚗",
  },
];

export function getDeal(id: string) {
  return deals.find((d) => d.id === id);
}

export function matchesQuery(deal: Deal, query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [
    deal.merchant,
    deal.title,
    deal.description,
    deal.location,
    deal.offer,
    categoryMap[deal.category].label,
  ]
    .join(" ")
    .toLowerCase()
    .includes(q);
}
