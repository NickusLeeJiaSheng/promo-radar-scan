export interface DbLocation {
  name: string;
  lat: number | null;
  lng: number | null;
}

export interface DbDeal {
  channel: string;
  channel_title: string;
  message_id: number;
  posted_at: string;
  posted_date: string;
  raw_input: string;
  merchant: string;
  category: string;
  offer: string;
  price: string | null;
  original_price: string | null;
  discount: string | null;
  valid_from: string | null;
  valid_to: string | null;
  time: string | null;
  locations: DbLocation[];
  redemption_method: string | null;
  restrictions: string[];
  promo_code: string | null;
  more_info: string | null;
}
