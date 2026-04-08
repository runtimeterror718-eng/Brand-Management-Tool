/**
 * Demo data for OVAL dashboard — shown when Supabase is not configured.
 * Gives new users a realistic preview of the platform's capabilities.
 */

export function isDemoMode(): boolean {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
  const key = process.env.NEXT_PUBLIC_SUPABASE_KEY || "";
  return !url || !key;
}

// ---------------------------------------------------------------------------
// Command Center
// ---------------------------------------------------------------------------
export const demoCommandCenter = {
  live: true,
  demo: true,
  healthScore: 62,
  sentiment: { positive: 312, negative: 187, neutral: 245, total: 744 },
  alerts: [
    { id: "a1", severity: "critical", platform: "reddit", text: "\"Physics Wallah scam\" trending on r/JEENEETards — 14K views in 6 hours", time: "2h ago", department: "PR Team" },
    { id: "a2", severity: "critical", platform: "google", text: "Negative autocomplete: \"physics wallah fraud\" appearing in top 3 suggestions", time: "4h ago", department: "SEO Team" },
    { id: "a3", severity: "high", platform: "telegram", text: "Fake channel @PW_Official_Free impersonating brand — 1,200 members", time: "5h ago", department: "Legal" },
    { id: "a4", severity: "high", platform: "youtube", text: "Ex-faculty video \"Why I Left PW\" gaining traction — 45K views", time: "8h ago", department: "HR Team" },
    { id: "a5", severity: "medium", platform: "instagram", text: "Batch scheduling complaints spiking under latest Reel — 23 negative comments", time: "12h ago", department: "Batch Ops" },
    { id: "a6", severity: "medium", platform: "reddit", text: "Consumer court complaint thread gaining awards on r/IndianAcademia", time: "1d ago", department: "Legal" },
    { id: "a7", severity: "low", platform: "youtube", text: "Positive review by education influencer — 12K views, 94% positive comments", time: "1d ago", department: "Marketing" },
  ],
  platformPulse: [
    { name: "Instagram", mentions: 144, positiveRatio: 0.58, negative: 31 },
    { name: "Reddit", mentions: 153, positiveRatio: 0.22, negative: 89 },
    { name: "YouTube", mentions: 287, positiveRatio: 0.41, negative: 52 },
    { name: "Telegram", mentions: 96, positiveRatio: 0.35, negative: 28 },
    { name: "Google", mentions: 64, positiveRatio: 0.19, negative: 42 },
  ],
  recentSignals: [
    { text: "paisa doob gaya bhai, ek bhi doubt clear nahi hua 😤", platform: "instagram", sentiment: "negative", time: "23m ago" },
    { text: "PW teachers are genuinely the best for JEE prep, Alakh sir 🙏", platform: "youtube", sentiment: "positive", time: "41m ago" },
    { text: "Anyone else getting spammed by PW notifications? 15 per day is insane", platform: "reddit", sentiment: "negative", time: "1h ago" },
    { text: "Lakshya batch quality has gone down significantly this year", platform: "telegram", sentiment: "negative", time: "2h ago" },
    { text: "Just cleared JEE Advanced thanks to PW Arjuna batch! 🎉", platform: "instagram", sentiment: "positive", time: "3h ago" },
    { text: "physics wallah customer care number not working since 3 days", platform: "google", sentiment: "negative", time: "4h ago" },
    { text: "Comparison: PW vs Allen vs Unacademy for NEET 2026", platform: "youtube", sentiment: "neutral", time: "5h ago" },
    { text: "Fake PW Telegram channel charging money for free PDFs", platform: "telegram", sentiment: "negative", time: "6h ago" },
  ],
  enrollmentRisks: { negativeAutocomplete: 8, negativeNews: 3 },
  creators: [],
  rag: { negative: { summary: "Key concerns: batch quality decline, aggressive notification spam, consumer court cases, and fake Telegram channels impersonating the brand.", confidence: 0.87 }, positive: { summary: "Strong student success stories from JEE/NEET results, teacher quality appreciation, and affordable pricing compared to competitors.", confidence: 0.82 } },
};

// ---------------------------------------------------------------------------
// Instagram
// ---------------------------------------------------------------------------
export const demoInstagram = {
  live: true,
  demo: true,
  stats: {
    totalPosts: 144, totalLikes: 892340, totalComments: 739, totalReelPlays: 4200000,
    totalVideoViews: 1850000, totalHashtags: 47, storedComments: 739,
    sentiment: { positive: 84, negative: 31, neutral: 29, overall: "Mixed-positive", source: "demo" },
  },
  topHashtags: [
    { tag: "#physicswallah", posts: 89, likes: 450000, quote: "PW changing lives 🙏", accounts: 12, sentiment: "positive" },
    { tag: "#pw", posts: 67, likes: 320000, quote: "Best teachers for JEE", accounts: 8, sentiment: "positive" },
    { tag: "#jee2026", posts: 45, likes: 180000, quote: "JEE prep with PW", accounts: 15, sentiment: "neutral" },
    { tag: "#neet2026", posts: 38, likes: 150000, quote: "NEET aspirant life", accounts: 11, sentiment: "neutral" },
    { tag: "#alakhpandey", posts: 34, likes: 290000, quote: "Alakh sir is the GOAT", accounts: 6, sentiment: "positive" },
    { tag: "#pwscam", posts: 12, likes: 45000, quote: "paisa barbaad", accounts: 9, sentiment: "negative" },
  ],
  topAccounts: [
    { name: "physicswallah", posts: 42, totalLikes: 380000, totalComments: 245, avgLikes: 9048 },
    { name: "neet_jee_aspirants", posts: 28, totalLikes: 120000, totalComments: 89, avgLikes: 4286 },
    { name: "kota_factory_memes", posts: 19, totalLikes: 95000, totalComments: 67, avgLikes: 5000 },
    { name: "competishun", posts: 15, totalLikes: 72000, totalComments: 45, avgLikes: 4800 },
    { name: "unacademy", posts: 12, totalLikes: 58000, totalComments: 34, avgLikes: 4833 },
  ],
  mediaTypes: { reel: 67, image: 42, video: 23, carousel: 12 },
  sentimentTrend: [
    { week: "Mar 3", score: 0.52, count: 18 }, { week: "Mar 10", score: 0.48, count: 22 },
    { week: "Mar 17", score: 0.41, count: 31 }, { week: "Mar 24", score: 0.55, count: 27 },
    { week: "Mar 31", score: 0.38, count: 24 }, { week: "Apr 7", score: 0.44, count: 22 },
  ],
  topComments: [
    { text: "Sir ek baar batch scheduling fix karo please 🙏", author: "jee_warrior_2026" },
    { text: "PW is the best thing that happened to Indian education", author: "neet_dreamer" },
    { text: "Quality ghatiya ho gayi hai compared to 2024 batches", author: "disappointed_student" },
    { text: "Alakh sir please come back to teaching chemistry also", author: "pw_fan_forever" },
    { text: "Refund policy is a joke, 45 days and still waiting", author: "angry_parent_delhi" },
  ],
  topPosts: [
    { caption: "JEE Advanced 2026 Strategy by Alakh Pandey", likes: 45000, comments: 89, mediaType: "reel", url: "#", account: "physicswallah", reelPlays: 890000 },
    { caption: "NEET Topper Interview — PW Lakshya Batch", likes: 32000, comments: 67, mediaType: "reel", url: "#", account: "physicswallah", reelPlays: 650000 },
    { caption: "Why students are switching from Unacademy to PW", likes: 28000, comments: 145, mediaType: "video", url: "#", account: "neet_jee_aspirants", reelPlays: 0 },
  ],
  rag: { enabled: false },
};

// ---------------------------------------------------------------------------
// Reddit
// ---------------------------------------------------------------------------
export const demoReddit = {
  live: true,
  demo: true,
  stats: {
    totalMentions: 153, negativeCount: 89, positiveCount: 22, neutralCount: 42,
    sentiment: "Mixed-negative", topSubreddit: "r/JEENEETards",
    sentimentSource: "demo", totalEmbeddings: 153,
  },
  posts: [
    { subreddit: "r/JEENEETards", title: "Physics Wallah batch quality has gone downhill — here's proof", snippet: "I was a PW student in 2024 and the difference in quality between then and now is shocking...", upvotes: 892, comments: 234, sentiment: "negative", url: "#" },
    { subreddit: "r/IndianAcademia", title: "Consumer court ordered ₹50K compensation against PW", snippet: "Filed a case 3 months ago for misleading batch promises. Won ₹50,000 compensation...", upvotes: 1247, comments: 189, sentiment: "negative", url: "#" },
    { subreddit: "r/JEENEETards", title: "Honest review: PW Arjuna batch for JEE 2026", snippet: "Been studying from Arjuna batch for 4 months now. Physics faculty is excellent, Chemistry is good...", upvotes: 567, comments: 145, sentiment: "neutral", url: "#" },
    { subreddit: "r/JEENEETards", title: "PW vs Allen vs Unacademy — which one for NEET dropper?", snippet: "Comparing all three based on faculty, content quality, test series, and price...", upvotes: 423, comments: 312, sentiment: "neutral", url: "#" },
    { subreddit: "r/IndianAcademia", title: "PW's sell-a-pen interview process is humiliating", snippet: "Applied for content writer role. They made me sell a pen for 10 minutes. This is not how you hire...", upvotes: 2100, comments: 456, sentiment: "negative", url: "#" },
    { subreddit: "r/JEENEETards", title: "Scored 99.2 percentile in JEE Mains thanks to PW 🎉", snippet: "Just wanted to thank PW faculty especially Amit sir for Physics. Self-study + PW is the combo...", upvotes: 1890, comments: 267, sentiment: "positive", url: "#" },
    { subreddit: "r/IndianAcademia", title: "PW employee here — working conditions are terrible", snippet: "Throwaway account. I work at PW HQ in Noida. 12-hour days, no WFH, constant pressure to sell...", upvotes: 3400, comments: 678, sentiment: "negative", url: "#" },
    { subreddit: "r/JEENEETards", title: "PW notification spam is out of control", snippet: "15 notifications per day!! How do I make it stop without uninstalling? Settings don't help...", upvotes: 890, comments: 123, sentiment: "negative", url: "#" },
  ],
  sentimentTrend: [
    { week: "Mar 3", score: -0.35 }, { week: "Mar 10", score: -0.42 },
    { week: "Mar 17", score: -0.28 }, { week: "Mar 24", score: -0.51 },
    { week: "Mar 31", score: -0.38 }, { week: "Apr 7", score: -0.45 },
  ],
  totalComments: 4125,
  subredditBreakdown: [
    { name: "r/JEENEETards", count: 87 }, { name: "r/IndianAcademia", count: 38 },
    { name: "r/Indian_Academia", count: 15 }, { name: "r/NEET", count: 8 },
    { name: "r/india", count: 5 },
  ],
  rag: { enabled: false },
};

// ---------------------------------------------------------------------------
// YouTube
// ---------------------------------------------------------------------------
export const demoYoutube = {
  live: true,
  demo: true,
  stats: {
    totalChannels: 24, totalVideos: 287, totalViews: 18500000, totalLikes: 450000,
    totalComments: 12400, totalSubscribers: 2800000, prRiskCount: 8,
    sentiment: { positive: 118, negative: 52, neutral: 117, total: 287, overall: "Mixed", source: "demo" },
  },
  channels: [
    { name: "Physics Wallah - Alakh Pandey", subscribers: 13200000, owner: "official" },
    { name: "PW Lakshya NEET", subscribers: 890000, owner: "official" },
    { name: "Competishun", subscribers: 450000, owner: "competitor" },
    { name: "Education Exposed", subscribers: 120000, owner: "critic" },
    { name: "Kota Life Vlogs", subscribers: 89000, owner: "fan" },
  ],
  videos: [
    { videoId: "v1", title: "Why I Left Physics Wallah — Full Story", views: 450000, likes: 12000, comments: 3400, duration: "18:42", date: "2026-03-28", url: "#", triageLabel: "PR Risk", isPrRisk: true, transcriptSentiment: "negative" },
    { videoId: "v2", title: "PW vs Allen vs Unacademy — Honest Comparison 2026", views: 320000, likes: 8900, comments: 2100, duration: "24:15", date: "2026-03-25", url: "#", triageLabel: "Neutral", isPrRisk: false, transcriptSentiment: "neutral" },
    { videoId: "v3", title: "JEE Advanced Strategy by Alakh Pandey", views: 890000, likes: 45000, comments: 1800, duration: "32:10", date: "2026-04-01", url: "#", triageLabel: "Positive", isPrRisk: false, transcriptSentiment: "positive" },
    { videoId: "v4", title: "PW Scam Exposed? Student Review After 6 Months", views: 280000, likes: 7800, comments: 4500, duration: "15:30", date: "2026-03-20", url: "#", triageLabel: "PR Risk", isPrRisk: true, transcriptSentiment: "negative" },
    { videoId: "v5", title: "NEET 2026 Topper Credits PW for Success", views: 520000, likes: 34000, comments: 890, duration: "12:45", date: "2026-04-03", url: "#", triageLabel: "Positive", isPrRisk: false, transcriptSentiment: "positive" },
  ],
  prRiskVideos: [
    { videoId: "v1", title: "Why I Left Physics Wallah — Full Story", views: 450000, reason: "Ex-faculty exposing internal issues", severity: "high", summary: "Former PW teacher discusses toxic work culture, salary disputes, and forced content schedules.", url: "#" },
    { videoId: "v4", title: "PW Scam Exposed? Student Review After 6 Months", views: 280000, reason: "Misleading batch promises", severity: "high", summary: "Student claims batch quality doesn't match marketing, shows comparison screenshots.", url: "#" },
  ],
  topComments: [
    { text: "This is exactly why I switched from PW to Allen online", author: "JEE2026aspirant", likes: 890, sentiment: "negative" },
    { text: "Alakh sir please address these issues, we love PW but quality is dropping", author: "NEET_dreamer", likes: 670, sentiment: "negative" },
    { text: "Best free content on YouTube for JEE, nothing comes close 🙏", author: "grateful_student", likes: 1200, sentiment: "positive" },
    { text: "The Arjuna batch teachers are actually incredible, especially for Physics", author: "pw_fan", likes: 450, sentiment: "positive" },
  ],
  rag: { enabled: false },
};

// ---------------------------------------------------------------------------
// Telegram
// ---------------------------------------------------------------------------
export const demoTelegram = {
  live: true,
  demo: true,
  stats: {
    totalChannels: 18, officialChannels: 3, fanChannels: 8, suspiciousChannels: 4,
    totalMembers: 52000, totalMessages: 3200, totalViews: 890000, totalForwards: 12000,
    suspiciousCount: 4,
    sentiment: { positive: 28, negative: 35, neutral: 33, total: 96, overall: "Mixed-negative", source: "demo" },
  },
  channels: [
    { username: "physicswallah_official", title: "Physics Wallah Official", label: "official", members: 28000, isFake: false, isScam: false, isVerified: true, url: "#", fakeScore: 0.02, confidence: 0.98, messagesLast7d: 45 },
    { username: "PW_Official_Free", title: "PW Official Free Notes", label: "suspicious_fake", members: 1200, isFake: true, isScam: false, isVerified: false, url: "#", fakeScore: 0.91, confidence: 0.89, messagesLast7d: 120 },
    { username: "pw_leaked_papers", title: "PW Leaked Test Papers 2026", label: "suspicious_fake", members: 800, isFake: true, isScam: true, isVerified: false, url: "#", fakeScore: 0.95, confidence: 0.92, messagesLast7d: 35 },
    { username: "jee_neet_pw_fans", title: "JEE NEET PW Fan Club", label: "fan_unofficial", members: 4500, isFake: false, isScam: false, isVerified: false, url: "#", fakeScore: 0.08, confidence: 0.85, messagesLast7d: 67 },
    { username: "pw_batch_reviews", title: "PW Batch Reviews", label: "fan_unofficial", members: 3200, isFake: false, isScam: false, isVerified: false, url: "#", fakeScore: 0.12, confidence: 0.78, messagesLast7d: 23 },
  ],
  riskBreakdown: { safe: 11, suspicious: 4, copyright_infringement: 3 },
  topMessages: [
    { text: "Join our channel for FREE PW Lakshya batch notes — 100% real 📚", channel: "PW_Official_Free", views: 8900, forwards: 230, riskLabel: "fake_content", riskScore: 0.91, isSuspicious: true, date: "2026-04-05", mediaType: "text" },
    { text: "PW physics chapter 4 leaked test paper — download now!", channel: "pw_leaked_papers", views: 4500, forwards: 180, riskLabel: "scam", riskScore: 0.95, isSuspicious: true, date: "2026-04-04", mediaType: "document" },
    { text: "Honest review: PW Arjuna batch month 3 — worth it?", channel: "pw_batch_reviews", views: 2300, forwards: 45, riskLabel: "safe", riskScore: 0.08, isSuspicious: false, date: "2026-04-03", mediaType: "text" },
  ],
  suspiciousContent: [
    { text: "Get PW premium content FREE — just forward to 5 groups!", channel: "PW_Official_Free", views: 8900, riskLabel: "fake_content", riskScore: 0.91, riskFlags: ["impersonation", "forwarding_spam"], date: "2026-04-05" },
    { text: "PW leaked test papers 2026 batch — real questions!", channel: "pw_leaked_papers", views: 4500, riskLabel: "scam", riskScore: 0.95, riskFlags: ["copyright", "scam"], date: "2026-04-04" },
  ],
  weeklyTrend: [
    { week: "Mar 3", count: 45, views: 12000 }, { week: "Mar 10", count: 52, views: 15000 },
    { week: "Mar 17", count: 38, views: 11000 }, { week: "Mar 24", count: 67, views: 23000 },
    { week: "Mar 31", count: 71, views: 28000 }, { week: "Apr 7", count: 58, views: 19000 },
  ],
  rag: { enabled: false },
};

// ---------------------------------------------------------------------------
// Google
// ---------------------------------------------------------------------------
export const demoGoogle = {
  live: true,
  demo: true,
  stats: {
    totalAutocomplete: 42, negativeAutocomplete: 8, warningAutocomplete: 6,
    newsArticles: 18, trendsDataPoints: 180, trendsRegions: 12, serpResults: 35, serpQueries: 7,
  },
  autocomplete: [
    { suggestion: "physics wallah scam", sentiment: "negative", query_text: "physics wallah", triage_label: "PR Risk", triage_is_pr_risk: true },
    { suggestion: "physics wallah fraud", sentiment: "negative", query_text: "physics wallah", triage_label: "PR Risk", triage_is_pr_risk: true },
    { suggestion: "physics wallah refund", sentiment: "negative", query_text: "physics wallah", triage_label: "Negative", triage_is_pr_risk: false },
    { suggestion: "physics wallah review", sentiment: "neutral", query_text: "physics wallah", triage_label: "Neutral", triage_is_pr_risk: false },
    { suggestion: "physics wallah jee 2026", sentiment: "neutral", query_text: "physics wallah", triage_label: "Positive", triage_is_pr_risk: false },
    { suggestion: "physics wallah app", sentiment: "neutral", query_text: "physics wallah", triage_label: "Neutral", triage_is_pr_risk: false },
    { suggestion: "physics wallah salary", sentiment: "negative", query_text: "physics wallah", triage_label: "Negative", triage_is_pr_risk: false },
    { suggestion: "physics wallah customer care", sentiment: "negative", query_text: "physics wallah", triage_label: "Negative", triage_is_pr_risk: false },
    { suggestion: "physics wallah alakh pandey", sentiment: "positive", query_text: "physics wallah", triage_label: "Positive", triage_is_pr_risk: false },
    { suggestion: "physics wallah offline center", sentiment: "neutral", query_text: "physics wallah", triage_label: "Neutral", triage_is_pr_risk: false },
  ],
  negativeSuggestions: [
    { sentiment: "negative", suggestion: "physics wallah scam" },
    { sentiment: "negative", suggestion: "physics wallah fraud" },
    { sentiment: "negative", suggestion: "physics wallah refund" },
    { sentiment: "negative", suggestion: "physics wallah salary" },
    { sentiment: "negative", suggestion: "physics wallah customer care" },
    { sentiment: "negative", suggestion: "physics wallah consumer court" },
    { sentiment: "negative", suggestion: "physics wallah fake" },
    { sentiment: "negative", suggestion: "physics wallah complaints" },
  ],
  news: [
    { title: "Consumer Court Orders PW to Pay ₹50K Compensation to Student", source: "The Indian Express", url: "#", published: "2026-03-28", sentiment: "negative", is_pr_risk: true, severity: "high" },
    { title: "Physics Wallah Expands to 50 Offline Centers Across India", source: "Economic Times", url: "#", published: "2026-04-02", sentiment: "positive", is_pr_risk: false, severity: "low" },
    { title: "EdTech Layoffs: PW Reportedly Cuts 200 Jobs in Content Division", source: "Inc42", url: "#", published: "2026-03-15", sentiment: "negative", is_pr_risk: true, severity: "high" },
    { title: "PW IPO: Analysts Predict $4B Valuation for FY27 Listing", source: "Mint", url: "#", published: "2026-04-01", sentiment: "positive", is_pr_risk: false, severity: "low" },
    { title: "Student Protests Outside PW Kota Center Over Batch Changes", source: "Times of India", url: "#", published: "2026-03-22", sentiment: "negative", is_pr_risk: true, severity: "high" },
  ],
  trendsChart: [
    { date: "2026-03-01", "physics wallah": 72, "pw scam": 18, "pw review": 45 },
    { date: "2026-03-08", "physics wallah": 68, "pw scam": 22, "pw review": 42 },
    { date: "2026-03-15", "physics wallah": 85, "pw scam": 35, "pw review": 51 },
    { date: "2026-03-22", "physics wallah": 78, "pw scam": 28, "pw review": 48 },
    { date: "2026-03-29", "physics wallah": 91, "pw scam": 31, "pw review": 55 },
    { date: "2026-04-05", "physics wallah": 82, "pw scam": 25, "pw review": 47 },
  ],
  trendsRegions: {
    "physics wallah": [
      { region: "Uttar Pradesh", interest: 100 }, { region: "Bihar", interest: 92 },
      { region: "Rajasthan", interest: 88 }, { region: "Madhya Pradesh", interest: 76 },
      { region: "Delhi", interest: 71 },
    ],
  },
  trendsKeywords: ["physics wallah", "pw scam", "pw review"],
  serp: {
    "physics wallah scam": [
      { organic_title: "Is Physics Wallah a Scam? Honest Student Review 2026", organic_snippet: "After using PW for 8 months, here's my honest take on whether it's worth the hype...", organic_url: "#", organic_position: 1 },
      { organic_title: "Consumer Court Cases Against Physics Wallah — Full List", organic_snippet: "A compilation of all consumer court complaints filed against PW in 2025-2026...", organic_url: "#", organic_position: 2 },
    ],
  },
  serpQueries: ["physics wallah scam", "physics wallah review", "pw vs allen"],
};

// ---------------------------------------------------------------------------
// Competitors
// ---------------------------------------------------------------------------
export const demoCompetitors = {
  live: true,
  demo: true,
  competitors: [
    { name: "Allen", mentions: 45, sentiment: "mixed", sentimentBreakdown: { positive: 18, negative: 15, neutral: 12 }, comparison_quotes: ["Allen's test series is better than PW", "Allen offline > PW online"], platforms: { reddit: 22, youtube: 15, instagram: 8 } },
    { name: "Unacademy", mentions: 38, sentiment: "negative", sentimentBreakdown: { positive: 8, negative: 22, neutral: 8 }, comparison_quotes: ["Unacademy is even worse than PW now", "At least PW is affordable unlike Unacademy"], platforms: { reddit: 20, youtube: 12, instagram: 6 } },
    { name: "BYJU'S", mentions: 28, sentiment: "negative", sentimentBreakdown: { positive: 3, negative: 21, neutral: 4 }, comparison_quotes: ["BYJU's is the real scam, not PW", "At least PW doesn't harass parents for EMI"], platforms: { reddit: 18, youtube: 8, instagram: 2 } },
    { name: "Vedantu", mentions: 15, sentiment: "neutral", sentimentBreakdown: { positive: 5, negative: 4, neutral: 6 }, comparison_quotes: ["Vedantu and PW are similar quality now"], platforms: { reddit: 8, youtube: 5, instagram: 2 } },
    { name: "Aakash", mentions: 12, sentiment: "mixed", sentimentBreakdown: { positive: 5, negative: 3, neutral: 4 }, comparison_quotes: ["Aakash offline is still gold standard for NEET"], platforms: { reddit: 6, youtube: 4, instagram: 2 } },
  ],
  negativeAmplifiers: [
    { text: "PW quality has dropped so much, even Allen students feel bad for us", platform: "reddit", sentiment: "negative" },
    { text: "Switched from PW to Competishun, best decision ever", platform: "youtube", sentiment: "negative" },
    { text: "At least Unacademy gives refunds, PW won't even respond", platform: "reddit", sentiment: "negative" },
  ],
  shareOfVoice: { "Physics Wallah": 744, Allen: 45, Unacademy: 38, "BYJU'S": 28, Vedantu: 15, Aakash: 12 },
  stats: { totalMentions: 882, competitorMentions: 138, sentimentSource: "demo" },
  rag: { enabled: false },
};

// ---------------------------------------------------------------------------
// Creators
// ---------------------------------------------------------------------------
export const demoCreators = {
  live: true,
  demo: true,
  creators: [
    { platform: "youtube", name: "Education Exposed", subscribers: 120000, stance: "threat", threatLevel: "high", videoCount: 8, totalViews: 1200000, negativeVideos: 6, positiveVideos: 0, topVideos: [{ title: "Why I Left Physics Wallah", views: 450000, url: "#", videoId: "v1", triage: "PR Risk", isPrRisk: true }] },
    { platform: "youtube", name: "Competishun", subscribers: 450000, stance: "threat", threatLevel: "medium", videoCount: 5, totalViews: 890000, negativeVideos: 3, positiveVideos: 1, topVideos: [{ title: "PW vs Competishun — Honest Take", views: 320000, url: "#", videoId: "v2", triage: "Negative", isPrRisk: false }] },
    { platform: "youtube", name: "Physics Wallah - Alakh Pandey", subscribers: 13200000, stance: "friend", threatLevel: "low", videoCount: 42, totalViews: 8900000, negativeVideos: 0, positiveVideos: 38, topVideos: [{ title: "JEE Advanced 2026 Strategy", views: 890000, url: "#", videoId: "v3", triage: "Positive", isPrRisk: false }] },
    { platform: "telegram", name: "PW Official Free Notes", username: "PW_Official_Free", members: 1200, stance: "threat", threatLevel: "high", label: "suspicious_fake", isFake: true, fakeScore: 0.91 },
    { platform: "telegram", name: "JEE NEET PW Fan Club", username: "jee_neet_pw_fans", members: 4500, stance: "friend", threatLevel: "low", label: "fan_unofficial", isFake: false, fakeScore: 0.08 },
    { platform: "youtube", name: "Kota Life Vlogs", subscribers: 89000, stance: "neutral", threatLevel: "low", videoCount: 3, totalViews: 180000, negativeVideos: 1, positiveVideos: 1, topVideos: [] },
  ],
  stats: { totalCreators: 6, threats: 3, friends: 2, neutral: 1, totalReach: 14300000 },
};

// ---------------------------------------------------------------------------
// Neural Map
// ---------------------------------------------------------------------------
export const demoNeuralMap = {
  live: true,
  demo: true,
  nodes: [
    { id: "pw", label: "Physics Wallah", group: "brand", size: 50, color: "#534AB7" },
    { id: "instagram", label: "Instagram", group: "platform", size: 20, color: "#E1306C", metadata: { mentions: 144 } },
    { id: "reddit", label: "Reddit", group: "platform", size: 22, color: "#FF5700", metadata: { mentions: 153 } },
    { id: "youtube", label: "YouTube", group: "platform", size: 30, color: "#FF0000", metadata: { mentions: 287 } },
    { id: "telegram", label: "Telegram", group: "platform", size: 15, color: "#0088CC", metadata: { mentions: 96 } },
    { id: "google", label: "Google", group: "platform", size: 12, color: "#4285F4", metadata: { mentions: 64 } },
    { id: "allen", label: "Allen", group: "competitor", size: 12, color: "#EF4444" },
    { id: "unacademy", label: "Unacademy", group: "competitor", size: 10, color: "#EF4444" },
    { id: "byjus", label: "BYJU'S", group: "competitor", size: 8, color: "#EF4444" },
    { id: "refund", label: "Refund Issues", group: "topic", size: 14, color: "#F59E0B" },
    { id: "scam", label: "Scam Narrative", group: "topic", size: 16, color: "#F59E0B" },
    { id: "teacher_quality", label: "Teacher Quality", group: "topic", size: 12, color: "#F59E0B" },
    { id: "app_issues", label: "App Problems", group: "topic", size: 10, color: "#F59E0B" },
    { id: "batch_quality", label: "Batch Quality", group: "topic", size: 13, color: "#F59E0B" },
    { id: "alakh", label: "Alakh Pandey", group: "person", size: 18, color: "#8B5CF6" },
  ],
  links: [
    { source: "pw", target: "instagram", label: "monitored", strength: 0.8, sentiment: "mixed", mentions: 144 },
    { source: "pw", target: "reddit", label: "monitored", strength: 0.9, sentiment: "negative", mentions: 153 },
    { source: "pw", target: "youtube", label: "monitored", strength: 1.0, sentiment: "mixed", mentions: 287 },
    { source: "pw", target: "telegram", label: "monitored", strength: 0.6, sentiment: "negative", mentions: 96 },
    { source: "pw", target: "google", label: "monitored", strength: 0.5, sentiment: "negative", mentions: 64 },
    { source: "pw", target: "allen", label: "compared", strength: 0.4, sentiment: "negative", mentions: 45 },
    { source: "pw", target: "unacademy", label: "compared", strength: 0.35, sentiment: "neutral", mentions: 38 },
    { source: "pw", target: "byjus", label: "compared", strength: 0.25, sentiment: "positive", mentions: 28 },
    { source: "reddit", target: "scam", label: "discusses", strength: 0.7, sentiment: "negative", mentions: 34 },
    { source: "reddit", target: "refund", label: "discusses", strength: 0.6, sentiment: "negative", mentions: 28 },
    { source: "youtube", target: "teacher_quality", label: "discusses", strength: 0.5, sentiment: "mixed", mentions: 22 },
    { source: "instagram", target: "batch_quality", label: "discusses", strength: 0.4, sentiment: "negative", mentions: 18 },
    { source: "google", target: "scam", label: "autocomplete", strength: 0.8, sentiment: "negative", mentions: 8 },
    { source: "pw", target: "alakh", label: "founded_by", strength: 0.9, sentiment: "positive", mentions: 34 },
    { source: "telegram", target: "app_issues", label: "discusses", strength: 0.3, sentiment: "negative", mentions: 12 },
  ],
  stats: { totalNodes: 15, totalLinks: 15, groups: { brand: 1, platform: 5, competitor: 3, topic: 4, person: 1, channel: 0, cluster: 0 } },
};

// ---------------------------------------------------------------------------
// Actionables
// ---------------------------------------------------------------------------
export const demoActionables = {
  live: true,
  demo: true,
  actionables: [
    {
      id: "act1", cluster_label: "Refund & Compensation", department: "Finance Team", priority: "high",
      task_title: "Address refund backlog — 28 unresolved complaints in 30 days",
      task_description: "Students across Reddit and Instagram are reporting 30-45 day wait times for refunds. Three consumer court cases have been filed. This is the #1 driver of negative sentiment.",
      suggested_actions: ["Set up dedicated refund hotline", "Publish refund SLA on website", "Proactively reach out to pending refund cases"],
      mention_count: 28, evidence: [
        { text: "Filed for refund 45 days ago, still no response from PW support", platform: "reddit", sentiment: "negative", similarity: 0.89, source_url: "#" },
        { text: "Consumer court ordered ₹50K compensation, PW still hasn't paid", platform: "reddit", sentiment: "negative", similarity: 0.85, source_url: "#" },
      ],
    },
    {
      id: "act2", cluster_label: "Scam Narrative on Google", department: "PR Team", priority: "high",
      task_title: "Counter 'physics wallah scam' autocomplete — appearing in top 3 Google suggestions",
      task_description: "8 negative autocomplete suggestions dominate Google search. This is the first thing parents see before visiting the PW website.",
      suggested_actions: ["Publish student success stories as blog posts", "Run Google Ads on branded keywords", "Request autocomplete review via Google support"],
      mention_count: 42, evidence: [
        { text: "physics wallah scam", platform: "google", sentiment: "negative", similarity: 0.95, source_url: "#" },
        { text: "physics wallah fraud", platform: "google", sentiment: "negative", similarity: 0.92, source_url: "#" },
      ],
    },
    {
      id: "act3", cluster_label: "Fake Telegram Channels", department: "Legal", priority: "high",
      task_title: "Take down 4 fake Telegram channels impersonating PW",
      task_description: "Four channels use PW branding to distribute pirated content and scam students. Combined membership: 2,000+. Two channels are actively collecting payments.",
      suggested_actions: ["File DMCA takedowns via Telegram", "Report channels for impersonation", "Add verified badge to official PW channels"],
      mention_count: 4, evidence: [
        { text: "Join PW Official Free Notes for premium content — 100% free!", platform: "telegram", sentiment: "negative", similarity: 0.91, source_url: "#" },
      ],
    },
    {
      id: "act4", cluster_label: "Notification Spam", department: "Product Team", priority: "medium",
      task_title: "Reduce app notification frequency — 15/day is driving uninstalls",
      task_description: "Multiple Reddit threads and Instagram comments mention excessive notifications as a key frustration. Students are uninstalling the app rather than adjusting settings.",
      suggested_actions: ["Cap notifications to 3/day by default", "Add granular notification preferences", "A/B test notification frequency vs retention"],
      mention_count: 18, evidence: [
        { text: "15 notifications per day!! How do I make it stop without uninstalling?", platform: "reddit", sentiment: "negative", similarity: 0.88, source_url: "#" },
      ],
    },
    {
      id: "act5", cluster_label: "Batch Quality Decline", department: "Batch Operations", priority: "medium",
      task_title: "Investigate Lakshya batch quality complaints — 31 negative mentions this month",
      task_description: "Students comparing 2024 vs 2026 batch quality, citing reduced teacher availability, fewer doubt sessions, and lower content freshness.",
      suggested_actions: ["Survey Lakshya batch students on satisfaction", "Compare 2024 vs 2026 teaching hours per batch", "Add more doubt-clearing sessions"],
      mention_count: 31, evidence: [
        { text: "Lakshya batch quality has gone down significantly this year", platform: "telegram", sentiment: "negative", similarity: 0.86, source_url: "#" },
        { text: "Quality ghatiya ho gayi hai compared to 2024 batches", platform: "instagram", sentiment: "negative", similarity: 0.83, source_url: "#" },
      ],
    },
    {
      id: "act6", cluster_label: "Employee Wellbeing", department: "HR Team", priority: "medium",
      task_title: "Address viral 'sell-a-pen interview' narrative on Reddit",
      task_description: "A Reddit post about PW's interview process went viral (3,400 upvotes). Combined with an employee throwaway post about working conditions, this is damaging employer brand.",
      suggested_actions: ["Review and modernize interview process", "Publish employee culture blog posts", "Address Glassdoor reviews proactively"],
      mention_count: 8, evidence: [
        { text: "PW's sell-a-pen interview process is humiliating", platform: "reddit", sentiment: "negative", similarity: 0.92, source_url: "#" },
      ],
    },
  ],
  stats: {
    totalTasks: 6, highPriority: 3, mediumPriority: 3, lowPriority: 0,
    ragEnabled: false, pureVectorSearch: false, negativeOnly: true, reranked: false,
    embeddingModel: "demo", vectorDimensions: 1536, totalMentionsAnalyzed: 744,
  },
};
