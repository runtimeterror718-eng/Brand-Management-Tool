// =============================================================================
// OVAL — Mock Data for Physics Wallah Intelligence Dashboard
// =============================================================================

// --- Interfaces ---

export interface GeoMention {
  state: string;
  stateCode: string;
  lat: number;
  lng: number;
  totalMentions: number;
  negativeMentions: number;
  negativePct: number;
  topIssue: string;
  platforms: { reddit: number; instagram: number; twitter: number };
}

export interface BrandHealth {
  score: number;
  label: string;
  color: string;
  trend: number;
  trendLabel: string;
}

export interface MarketMood {
  title: string;
  body: string;
}

export interface WeeklyBrief {
  label: string;
  body: string;
}

export interface ActiveRisk {
  title: string;
  tags: { label: string; color: "red" | "amber" | "green" }[];
  body: string;
}

export interface AutocompleteSuggestion {
  text: string;
  highlight: string;
  sentiment: "neutral" | "negative" | "warning";
}

export interface PlatformSplit {
  platform: string;
  color: string;
  bgTint: string;
  sentiment: string;
  quote: string;
  stat: string;
}

export interface StockCorrelationPoint {
  month: string;
  healthScore: number;
  stockPrice: number;
}

export interface FounderLetter {
  label: string;
  body: string;
}

export interface PerceptionGap {
  claim: string;
  brandPush: number;
  marketAgreement: number;
  status: string;
  statusColor: "red" | "amber" | "green";
  insight: string;
  sources: { reddit: number; youtube: number; google: number };
}

export interface RedditMention {
  subreddit: string;
  title: string;
  snippet: string;
  upvotes: number;
  comments: number;
  sentiment: "positive" | "negative" | "mixed";
}

export interface SentimentDataPoint {
  week: string;
  score: number;
}

export interface InstagramHashtag {
  tag: string;
  posts: number;
  sentiment: "positive" | "mixed" | "negative";
  quote: string;
  likes: number;
}

export interface Competitor {
  name: string;
  shareOfVoice: number;
  color: string;
}

export interface HeadToHead {
  opponent: string;
  pwWin: number;
  opponentWin: number;
}

export interface Signal {
  title: string;
  description: string;
  trend: "up" | "down" | "stable";
  severity: "red" | "amber" | "green";
}

export interface ContagionNode {
  label: string;
  color: string;
  timestamp: string;
}

export interface NarrativeEvent {
  title: string;
  velocity: number;
  velocityLabel: string;
  severity: "red" | "amber" | "green";
  age: string;
}

export interface CounterStrategy {
  name: string;
  borderColor: string;
  successRate: number;
  action: string;
  reactions: { platform: string; prediction: string }[];
  risk: string;
}

// --- Data ---

export const brandHealth: BrandHealth = {
  score: 64,
  label: "Needs attention",
  color: "#BA7517",
  trend: -6,
  trendLabel: "-6 from last month",
};

export const marketMood: MarketMood = {
  title: "Mixed feelings",
  body: "Students love the teaching but are increasingly frustrated with the app, customer support, and a string of recent controversies. The 'affordable education' promise is being questioned as offline centres scale to Allen-level pricing.",
};

export const weeklyBrief: WeeklyBrief = {
  label: "This week",
  body: "A faculty member was suspended for a casteist slur during a live class. The video went viral on X, reached mainstream news within 48 hours, and demands for an FIR under the SC/ST Act are trending. PW responded with an immediate suspension. Separately, a consumer court in Baramulla ordered PW to refund fees and pay ₹50K compensation for denying a student class access — PW didn't even appear in court. Stock is at ₹89, down 45% from the IPO listing high of ₹162. On the positive side, Q3 revenue grew 34% YoY, online enrollments crossed 3.96M, and the company expanded to 318 offline centres.",
};

export const activeRisk: ActiveRisk = {
  title: "Faculty casteist slur — viral incident",
  tags: [
    { label: "Spreading fast", color: "red" },
    { label: "Reached mainstream news", color: "red" },
    { label: "Autocomplete affected", color: "amber" },
  ],
  body: "Started on X via @ambedkariteIND on March 21. Picked up by DNA India within hours. PW suspended the teacher immediately — response was fast, but narrative is in Google search results. Impact: 2-4 weeks. Long-term: becomes reference point in future 'PW controversy' compilations.",
};

export const autocompleteSuggestions: AutocompleteSuggestion[] = [
  { text: "Physics Wallah", highlight: "app", sentiment: "neutral" },
  { text: "Physics Wallah", highlight: "controversy", sentiment: "negative" },
  { text: "Physics Wallah", highlight: "teacher suspended", sentiment: "negative" },
  { text: "Physics Wallah", highlight: "share price", sentiment: "neutral" },
  { text: "Physics Wallah", highlight: "refund", sentiment: "warning" },
  { text: "Physics Wallah", highlight: "IPO", sentiment: "neutral" },
];

export const platformSplits: PlatformSplit[] = [
  {
    platform: "Instagram",
    color: "#639922",
    bgTint: "bg-[#EAF3DE] dark:bg-green-950/30",
    sentiment: "Positive",
    quote: "Day 45 of PW Lakshya prep. These notes are saving my life.",
    stat: "12,400 posts under #PhysicsWallah",
  },
  {
    platform: "Reddit",
    color: "#D85A30",
    bgTint: "bg-[#FCEBEB] dark:bg-red-950/30",
    sentiment: "Negative",
    quote: "Is PW becoming the next BYJU'S? 300+ centres charging Allen prices.",
    stat: "1,847 mentions this week",
  },
];

export const stockCorrelation: StockCorrelationPoint[] = [
  { month: "Nov 2025", healthScore: 78, stockPrice: 156 },
  { month: "Dec 2025", healthScore: 75, stockPrice: 140 },
  { month: "Jan 2026", healthScore: 72, stockPrice: 121 },
  { month: "Feb 2026", healthScore: 68, stockPrice: 117 },
  { month: "Mar 2026", healthScore: 64, stockPrice: 89 },
];

export const founderLetter: FounderLetter = {
  label: "If you had to hear one thing",
  body: "Your biggest risk isn't any single controversy — it's the widening gap between your 'student-first, affordable education' story and what students actually experience. Faculty attrition hit 40% in one year. The brand was built on Alakh Pandey's authenticity and affordability — every decision that moves away from that origin story costs you more credibility than it gains in revenue. Allen is winning 58% of direct comparisons. Your stock and social sentiment have a 0.87 correlation, and both are declining. The single highest-impact action: publish transparent faculty retention data and JEE/NEET selection rates. Silence lets the market write its own narrative.",
};

export const perceptionGaps: PerceptionGap[] = [
  {
    claim: "Affordable education for all",
    brandPush: 88,
    marketAgreement: 52,
    status: "Gap widening",
    statusColor: "amber",
    insight: "Online courses still ₹2-5K but offline Vidyapeeth centres ₹40-80K — comparable to Allen. 'Affordable' works online, breaks down offline.",
    sources: { reddit: 342, youtube: 128, google: 89 },
  },
  {
    claim: "Best teachers in the industry",
    brandPush: 94,
    marketAgreement: 38,
    status: "Credibility risk",
    statusColor: "red",
    insight: "Faculty attrition 40.4% in FY24. Reddit says 'good teachers left.' Sankalp controversy still resurfaces. Recent casteist slur adds another data point. You're pushing a claim 62% of your audience disputes.",
    sources: { reddit: 567, youtube: 234, google: 156 },
  },
  {
    claim: "Student-first approach",
    brandPush: 82,
    marketAgreement: 30,
    status: "Breaking down",
    statusColor: "red",
    insight: "PissedConsumer 2.2/5 rating. Consumer court found PW guilty of 'unfair trade practice.' Students blocked from doubt sections. No-refund policy is a recurring pain.",
    sources: { reddit: 423, youtube: 98, google: 201 },
  },
  {
    claim: "Tech-enabled learning",
    brandPush: 68,
    marketAgreement: 55,
    status: "Mostly aligned",
    statusColor: "green",
    insight: "AI Guru well-received. App 4.8 rating, 10M+ downloads. But 'app crash during live class' is a recurring complaint.",
    sources: { reddit: 189, youtube: 67, google: 45 },
  },
];

export const redditSentiment: SentimentDataPoint[] = [
  { week: "W1", score: 0.15 },
  { week: "W2", score: 0.12 },
  { week: "W3", score: 0.08 },
  { week: "W4", score: 0.10 },
  { week: "W5", score: 0.05 },
  { week: "W6", score: 0.03 },
  { week: "W7", score: -0.02 },
  { week: "W8", score: 0.01 },
  { week: "W9", score: -0.05 },
  { week: "W10", score: -0.08 },
  { week: "W11", score: -0.15 },
  { week: "W12", score: -0.10 },
];

export const redditMentions: RedditMention[] = [
  { subreddit: "JEENEETards", title: "PW offline vs Allen offline — honest comparison", snippet: "Allen's study material is on another level compared to PW Vidyapeeth...", upvotes: 847, comments: 234, sentiment: "negative" },
  { subreddit: "JEEAdvanced", title: "Why are good teachers leaving PW?", snippet: "First Sankalp teachers, now more quietly leaving...", upvotes: 623, comments: 189, sentiment: "negative" },
  { subreddit: "JEENEETards", title: "PW Lakshya 2026 batch — 3 months in", snippet: "Main lectures still good, doubt resolution gone downhill...", upvotes: 412, comments: 156, sentiment: "mixed" },
  { subreddit: "NEET", title: "PW Yakeen is actually underrated", snippet: "Cleared NEET with Yakeen, biology teachers amazing for the price...", upvotes: 389, comments: 98, sentiment: "positive" },
  { subreddit: "IndianTeenagers", title: "Is PW becoming the next BYJU'S?", snippet: "Started as anti-coaching mafia, now 300+ centres at Allen prices...", upvotes: 356, comments: 267, sentiment: "negative" },
];

export const instagramHashtags: InstagramHashtag[] = [
  { tag: "#PhysicsWallah", posts: 12400, sentiment: "positive", quote: "Day 45 of PW prep. Notes saving my life.", likes: 2340 },
  { tag: "#AlakhPandey", posts: 8900, sentiment: "mixed", quote: "Alakh sir please address teacher quality. We trust you.", likes: 5670 },
  { tag: "#PWVidyapeeth", posts: 3200, sentiment: "mixed", quote: "Kota experience not what I expected for the price.", likes: 1890 },
  { tag: "#PW", posts: 45600, sentiment: "positive", quote: "Thank you PW for making JEE prep possible.", likes: 8900 },
];

export const competitors: Competitor[] = [
  { name: "PW", shareOfVoice: 36, color: "#534AB7" },
  { name: "Allen", shareOfVoice: 26, color: "#1D9E75" },
  { name: "Unacademy", shareOfVoice: 20, color: "#378ADD" },
  { name: "BYJU'S", shareOfVoice: 12, color: "#9CA3AF" },
  { name: "Others", shareOfVoice: 6, color: "#D1D5DB" },
];

export const headToHead: HeadToHead[] = [
  { opponent: "Allen", pwWin: 42, opponentWin: 58 },
  { opponent: "Unacademy", pwWin: 67, opponentWin: 33 },
  { opponent: "BYJU'S", pwWin: 84, opponentWin: 16 },
];

export const competitorSignals: Signal[] = [
  { title: "Students considering PW", description: "Declining, down 12%", trend: "down", severity: "amber" },
  { title: "Students leaving PW", description: "Growing concern on Reddit", trend: "up", severity: "red" },
  { title: "Stock vs perception", description: "0.87 correlation, both declining", trend: "down", severity: "red" },
  { title: "Employer reputation", description: "40% attrition, silent terminations", trend: "down", severity: "amber" },
];

export const contagionChain: ContagionNode[] = [
  { label: "@ambedkariteIND", color: "#378ADD", timestamp: "Mar 21, 2:14 PM" },
  { label: "Student community", color: "#BA7517", timestamp: "Mar 21, 6:30 PM" },
  { label: "DNA India", color: "#D85A30", timestamp: "Mar 22, 9:00 AM" },
  { label: "Mainstream news", color: "#E24B4A", timestamp: "Mar 22, 2:00 PM" },
  { label: "Google autocomplete", color: "#991B1B", timestamp: "Mar 23, 11:00 AM" },
];

export const activeNarratives: NarrativeEvent[] = [
  { title: "Faculty quality decline", velocity: 0.6, velocityLabel: "growing", severity: "amber", age: "8 months active" },
  { title: "Casteist slur incident", velocity: 0.9, velocityLabel: "spreading", severity: "red", age: "1 week old" },
  { title: "Overpriced offline centres", velocity: 0.3, velocityLabel: "slowly growing", severity: "amber", age: "4 months" },
];

export const fadingNarratives: NarrativeEvent[] = [
  { title: "Kashmir forest FIR", velocity: -0.4, velocityLabel: "fading", severity: "green", age: "mostly forgotten" },
  { title: "Silent terminations", velocity: -0.2, velocityLabel: "fading slowly", severity: "amber", age: "still in Glassdoor reviews" },
];

export const counterStrategies: CounterStrategy[] = [
  {
    name: "Radical transparency",
    borderColor: "#639922",
    successRate: 68,
    action: "Publish retention data, let long-tenured teachers speak on camera",
    reactions: [
      { platform: "Reddit", prediction: "Cautiously positive, respects transparency" },
      { platform: "Twitter", prediction: "Mixed, some call it PR spin" },
    ],
    risk: "Backfires if actual numbers are bad",
  },
  {
    name: "New star hires",
    borderColor: "#BA7517",
    successRate: 45,
    action: "Announce high-profile teacher acquisitions",
    reactions: [
      { platform: "Reddit", prediction: "Skeptical, will compare against who left" },
      { platform: "Twitter", prediction: "Positive first 48hrs, then cynicism" },
    ],
    risk: "Creates star-dependency, if new hire leaves it doubles the narrative",
  },
  {
    name: "Ignore and let it fade",
    borderColor: "#E24B4A",
    successRate: 22,
    action: "Focus marketing elsewhere",
    reactions: [
      { platform: "Reddit", prediction: "Silence = confirmation" },
      { platform: "Twitter", prediction: "No immediate downside but narrative calcifies" },
    ],
    risk: "Velocity is +0.6, it's growing not fading",
  },
];

// --- Geographic Mention Data (India states) ---

export const geoMentions: GeoMention[] = [
  { state: "Rajasthan", stateCode: "RJ", lat: 26.9, lng: 75.8, totalMentions: 487, negativeMentions: 218, negativePct: 45, topIssue: "Offline centre pricing vs Allen", platforms: { reddit: 142, instagram: 89, twitter: 47 } },
  { state: "Uttar Pradesh", stateCode: "UP", lat: 26.8, lng: 80.9, totalMentions: 623, negativeMentions: 274, negativePct: 44, topIssue: "Faculty attrition, doubt resolution delays", platforms: { reddit: 178, instagram: 134, twitter: 56 } },
  { state: "Delhi", stateCode: "DL", lat: 28.6, lng: 77.2, totalMentions: 534, negativeMentions: 230, negativePct: 43, topIssue: "Refund policy, consumer court case", platforms: { reddit: 156, instagram: 112, twitter: 68 } },
  { state: "Bihar", stateCode: "BR", lat: 25.6, lng: 85.1, totalMentions: 412, negativeMentions: 169, negativePct: 41, topIssue: "App crashes during live classes", platforms: { reddit: 98, instagram: 145, twitter: 25 } },
  { state: "Madhya Pradesh", stateCode: "MP", lat: 23.3, lng: 77.4, totalMentions: 289, negativeMentions: 113, negativePct: 39, topIssue: "Vidyapeeth quality concerns", platforms: { reddit: 67, instagram: 78, twitter: 34 } },
  { state: "Maharashtra", stateCode: "MH", lat: 19.1, lng: 72.9, totalMentions: 378, negativeMentions: 140, negativePct: 37, topIssue: "Casteist slur incident backlash", platforms: { reddit: 112, instagram: 67, twitter: 73 } },
  { state: "Gujarat", stateCode: "GJ", lat: 23.0, lng: 72.6, totalMentions: 198, negativeMentions: 67, negativePct: 34, topIssue: "Allen comparison in offline", platforms: { reddit: 45, instagram: 56, twitter: 23 } },
  { state: "Karnataka", stateCode: "KA", lat: 12.97, lng: 77.6, totalMentions: 267, negativeMentions: 88, negativePct: 33, topIssue: "Teacher quality decline", platforms: { reddit: 89, instagram: 34, twitter: 53 } },
  { state: "Jharkhand", stateCode: "JH", lat: 23.6, lng: 85.3, totalMentions: 156, negativeMentions: 50, negativePct: 32, topIssue: "Network issues with app", platforms: { reddit: 34, instagram: 67, twitter: 12 } },
  { state: "Tamil Nadu", stateCode: "TN", lat: 13.1, lng: 80.3, totalMentions: 189, negativeMentions: 55, negativePct: 29, topIssue: "Limited regional language content", platforms: { reddit: 56, instagram: 23, twitter: 32 } },
  { state: "West Bengal", stateCode: "WB", lat: 22.6, lng: 88.4, totalMentions: 201, negativeMentions: 56, negativePct: 28, topIssue: "Offline centre expansion too fast", platforms: { reddit: 45, instagram: 78, twitter: 22 } },
  { state: "Telangana", stateCode: "TS", lat: 17.4, lng: 78.5, totalMentions: 145, negativeMentions: 38, negativePct: 26, topIssue: "Pricing transparency", platforms: { reddit: 34, instagram: 23, twitter: 19 } },
  { state: "Punjab", stateCode: "PB", lat: 31.1, lng: 75.3, totalMentions: 123, negativeMentions: 30, negativePct: 24, topIssue: "Limited batch sizes", platforms: { reddit: 23, instagram: 45, twitter: 12 } },
  { state: "Jammu & Kashmir", stateCode: "JK", lat: 34.1, lng: 74.8, totalMentions: 89, negativeMentions: 42, negativePct: 47, topIssue: "Consumer court refund case — PW no-show", platforms: { reddit: 28, instagram: 12, twitter: 14 } },
  { state: "Kerala", stateCode: "KL", lat: 10.0, lng: 76.3, totalMentions: 112, negativeMentions: 22, negativePct: 20, topIssue: "Content not competitive for Kerala boards", platforms: { reddit: 18, instagram: 34, twitter: 8 } },
  { state: "Haryana", stateCode: "HR", lat: 29.1, lng: 76.1, totalMentions: 178, negativeMentions: 71, negativePct: 40, topIssue: "Allen dominance in coaching hub", platforms: { reddit: 56, instagram: 34, twitter: 25 } },
  { state: "Chhattisgarh", stateCode: "CG", lat: 21.3, lng: 81.6, totalMentions: 67, negativeMentions: 14, negativePct: 21, topIssue: "Limited offline presence", platforms: { reddit: 8, instagram: 23, twitter: 5 } },
  { state: "Assam", stateCode: "AS", lat: 26.1, lng: 91.7, totalMentions: 78, negativeMentions: 18, negativePct: 23, topIssue: "Connectivity issues for live classes", platforms: { reddit: 12, instagram: 34, twitter: 6 } },
];
