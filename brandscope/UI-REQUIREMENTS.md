# OVAL Dashboard — UI/UX Requirements

> Learned from Abhishek's feedback across this session. Reference this before making any UI changes.

## What Abhishek Likes
- Clean, minimal, data-dense layouts (Bloomberg terminal meets Notion)
- Solid card backgrounds with subtle drop shadows — NOT glass/blur effects
- Numbers that count up on load (AnimatedNumber component)
- Donut charts that spin in with circular animation (Recharts Pie with animationDuration)
- Bar charts that grow from left to right
- Smooth page entrance animations (framer-motion fadeUp with stagger)
- Purple (#534AB7) as primary accent
- Small, compact metric cards in a single row
- Filterable, searchable scrollable lists for comments/posts
- Platform-colored icons (Reddit orange, IG pink, YT red, Telegram blue, Google blue)
- Bold section headings, uppercase tracking-widest for labels
- "Live" badge indicator (green dot with pulse)

## What Abhishek Does NOT Like
- Glass/glassmorphism effects on cards (LiquidCard, blur filters)
- Markdown symbols showing in rendered text (###, **, *, etc.)
- Long walls of LLM-generated text — wants bullet points, max 6
- Technical jargon visible to users ("LLM-classified", "pgvector", "1536-dim embeddings")
- Cluttered layouts with too many sections fighting for attention
- Charts/cards that stack vertically when they should be in a row
- Flat/bland visualizations with no animation
- Tremor library (incompatible with Next.js 14 SWC, caused 500 errors)
- Using sed/grep to edit JSX files (causes syntax breaks)
- Slow page loads (wants cached API responses)
- Mock data labels showing ("MOCK DATA" badges)
- Empty charts when data is loading (wants loading spinners)

## Layout Rules
1. Score cards / metric cards: ALWAYS in a single horizontal row, never stacking
2. Charts: use AnimatedChart wrapper so they animate on scroll into view
3. Analysis sections: at the TOP of intel pages, formatted as cards with bold headings
4. Comments/posts: scrollable container with max-height, search bar, filter dropdown
5. RAG insights: parsed into bullet points (max 6), no raw markdown, rendered as card grid
6. Loading states: bouncing dots in platform color, centered
7. Page sections: uniform spacing (space-y-6), rounded-2xl borders, consistent padding (p-5)

## Color System
- Brand purple: #534AB7
- Positive/safe: #639922
- Negative/danger: #E24B4A
- Warning/amber: #BA7517
- Reddit: #FF5700
- Instagram: #E1306C
- YouTube: #FF0000
- Telegram: #0088CC
- Google: #4285F4
- Neutral: #9CA3AF
- Card background: bg-card (CSS var)
- Card border: border-border (CSS var)

## Typography
- UI text: Inter (var --font-sans)
- AI/editorial text: Merriweather (serif) — but keep it minimal
- Metric labels: text-[10px] uppercase tracking-widest text-muted-foreground
- Metric values: text-xl font-bold
- Section headings: text-sm font-bold or text-xs font-semibold uppercase tracking-widest
- Body text: text-sm text-foreground/80

## Component Stack (What Works)
- Recharts (PieChart, BarChart, AreaChart, LineChart) — with animationDuration={1500}
- Framer Motion — page entrance animations, stagger, fadeUp
- AnimatedChart wrapper — IntersectionObserver scroll trigger
- AnimatedNumber — count-up on scroll into view
- Lucide React icons — all icons from this set
- react-simple-maps — India geographic map
- @ant-design/graphs NetworkGraph — neural map visualization

## Component Stack (What Does NOT Work)
- @tremor/react — incompatible with Next.js 14 SWC, causes 500 errors
- LiquidCard / liquid-glass effects — user finds them ugly
- Tremor's BarList, DonutChart, Tracker — never rendered properly

## Anti-Patterns to Avoid
- Never use sed/perl to edit .tsx files — always use direct file writes
- Never put useState/useEffect after an early return — hooks rule violation
- Never import Tremor components — SWC parser fails
- Never show "LLM-classified" or "pgvector" or "embeddings" in UI text
- Never render raw LLM markdown — always strip with cleanAnalysis()
- Always add loading states before data renders
- Always cache API responses (5 min TTL minimum)
