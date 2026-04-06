-- =============================================================================
-- Brand Management Tool — Supabase Schema
-- Covers: brands, all 8 platform tables, transcriptions, severity, fulfillment, analysis
-- Generated from supabase.txt field specs
-- =============================================================================

-- ======================== CORE TABLES ========================

CREATE TABLE IF NOT EXISTS brands (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    keywords TEXT[],
    hashtags TEXT[],
    platforms TEXT[],
    competitors TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== YOUTUBE ========================

CREATE TABLE IF NOT EXISTS youtube_channels (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    channel_subscribers INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS youtube_videos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    channel_id TEXT,
    video_id TEXT NOT NULL UNIQUE,
    video_title TEXT,
    video_date TIMESTAMPTZ,
    video_resolution TEXT,
    video_duration INT,              -- seconds
    video_views INT DEFAULT 0,
    video_likes INT DEFAULT 0,
    video_description TEXT,
    video_comment_count INT DEFAULT 0,
    media_type TEXT,                  -- 'video', 'short', 'live'
    source_url TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

CREATE TABLE IF NOT EXISTS youtube_comments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id TEXT,
    comment_author TEXT,
    comment_text TEXT,
    comment_replies INT DEFAULT 0,
    comment_likes INT DEFAULT 0,
    comment_date TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== INSTAGRAM ========================

CREATE TABLE IF NOT EXISTS instagram_accounts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    account_name TEXT NOT NULL,
    followers INT DEFAULT 0,
    following INT DEFAULT 0,
    number_of_posts INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS instagram_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    post_id TEXT UNIQUE,
    account_name TEXT,
    caption_text TEXT,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    media_type TEXT,                  -- 'image', 'video', 'reel', 'carousel'
    published_date TIMESTAMPTZ,
    hashtags TEXT[],
    post_url TEXT,
    video_views INT DEFAULT 0,
    reel_plays INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

CREATE TABLE IF NOT EXISTS instagram_comments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    post_id TEXT,
    comment_text TEXT,
    comment_author TEXT,
    comment_date TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== REDDIT ========================

CREATE TABLE IF NOT EXISTS reddit_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    post_id TEXT UNIQUE,
    post_title TEXT,
    post_body TEXT,
    author_username TEXT,
    subreddit_name TEXT,
    score INT DEFAULT 0,
    upvote_ratio FLOAT,
    num_comments INT DEFAULT 0,
    created_at TIMESTAMPTZ,
    post_url TEXT,
    post_flair TEXT,
    is_self_post BOOLEAN DEFAULT TRUE,
    awards_received INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

CREATE TABLE IF NOT EXISTS reddit_comments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    post_id TEXT,
    comment_body TEXT,
    comment_author TEXT,
    comment_score INT DEFAULT 0,
    comment_parent_id TEXT,
    comment_depth INT DEFAULT 0,
    created_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== GOOGLE / SEO ========================

CREATE TABLE IF NOT EXISTS google_seo_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    query_text TEXT,
    autocomplete_suggestion TEXT,
    people_also_ask TEXT,
    organic_title TEXT,
    organic_snippet TEXT,
    organic_url TEXT,
    organic_position INT,
    featured_snippet_text TEXT,
    knowledge_panel_info TEXT,
    news_results TEXT,
    review_stars FLOAT,
    related_searches TEXT,
    search_result_date TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

-- ======================== X / TWITTER ========================

CREATE TABLE IF NOT EXISTS twitter_tweets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    tweet_id TEXT UNIQUE,
    tweet_text TEXT,
    author_username TEXT,
    author_id TEXT,
    author_followers_count INT DEFAULT 0,
    author_verified BOOLEAN DEFAULT FALSE,
    retweet_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    reply_count INT DEFAULT 0,
    quote_count INT DEFAULT 0,
    impression_count INT DEFAULT 0,
    created_at TIMESTAMPTZ,
    hashtags TEXT[],
    mentioned_users TEXT[],
    in_reply_to_tweet_id TEXT,
    is_retweet BOOLEAN DEFAULT FALSE,
    tweet_url TEXT,
    language TEXT,
    media_attachments JSONB,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

-- ======================== TELEGRAM ========================

CREATE TABLE IF NOT EXISTS telegram_messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    message_id TEXT,
    message_text TEXT,
    sender_username TEXT,
    sender_id TEXT,
    channel_name TEXT,
    channel_id TEXT,
    views INT DEFAULT 0,
    forwards_count INT DEFAULT 0,
    reply_to_message_id TEXT,
    reactions JSONB,
    message_timestamp TIMESTAMPTZ,
    message_url TEXT,
    media_type TEXT,
    is_pinned BOOLEAN DEFAULT FALSE,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

-- ======================== LINKEDIN ========================

CREATE TABLE IF NOT EXISTS linkedin_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    post_text TEXT,
    author_name TEXT,
    author_headline TEXT,
    reactions_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    shares_count INT DEFAULT 0,
    published_date TIMESTAMPTZ,
    company_page_followers INT DEFAULT 0,
    employee_count INT DEFAULT 0,
    job_postings_count INT DEFAULT 0,
    post_url TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

-- ======================== FACEBOOK ========================

CREATE TABLE IF NOT EXISTS facebook_pages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    page_id TEXT UNIQUE,
    page_name TEXT,
    page_category TEXT,
    page_fan_count INT DEFAULT 0,
    page_follower_count INT DEFAULT 0,
    page_about_text TEXT,
    page_website TEXT,
    page_verification_status BOOLEAN DEFAULT FALSE,
    page_rating FLOAT,
    page_rating_count INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facebook_posts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    page_id TEXT,
    post_id TEXT UNIQUE,
    post_message TEXT,
    post_story TEXT,
    post_type TEXT,
    post_created_time TIMESTAMPTZ,
    post_permalink_url TEXT,
    post_shares_count INT DEFAULT 0,
    post_status_type TEXT,
    attached_link_url TEXT,
    attached_link_caption TEXT,
    post_description TEXT,
    full_picture_url TEXT,
    is_published BOOLEAN DEFAULT TRUE,
    post_updated_time TIMESTAMPTZ,
    total_reactions_count INT DEFAULT 0,
    like_reactions INT DEFAULT 0,
    love_reactions INT DEFAULT 0,
    haha_reactions INT DEFAULT 0,
    wow_reactions INT DEFAULT 0,
    sad_reactions INT DEFAULT 0,
    angry_reactions INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

CREATE TABLE IF NOT EXISTS facebook_comments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    post_id TEXT,
    comment_id TEXT,
    comment_message TEXT,
    comment_author_name TEXT,
    comment_author_id TEXT,
    comment_created_time TIMESTAMPTZ,
    comment_like_count INT DEFAULT 0,
    comment_reply_count INT DEFAULT 0,
    comment_parent_id TEXT,
    comment_permalink TEXT,
    comment_attachment_type TEXT,
    comment_attachment_url TEXT,
    can_reply BOOLEAN DEFAULT TRUE,
    is_hidden BOOLEAN DEFAULT FALSE,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facebook_page_insights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    page_id TEXT,
    date TIMESTAMPTZ,
    page_impressions INT DEFAULT 0,
    page_engaged_users INT DEFAULT 0,
    page_fans_total INT DEFAULT 0,
    page_fan_adds INT DEFAULT 0,
    page_fan_removes INT DEFAULT 0,
    page_negative_feedback INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facebook_post_insights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    post_id TEXT,
    post_impressions INT DEFAULT 0,
    post_engaged_users INT DEFAULT 0,
    post_clicks INT DEFAULT 0,
    post_reactions_by_type JSONB,
    post_negative_feedback INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS facebook_groups (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    group_name TEXT,
    group_member_count INT DEFAULT 0,
    post_text TEXT,
    post_author TEXT,
    post_reactions INT DEFAULT 0,
    post_comments INT DEFAULT 0,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== UNIFIED MENTIONS (cross-platform) ========================

CREATE TABLE IF NOT EXISTS mentions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    platform_ref_id TEXT,            -- FK to platform-specific table ID
    content_text TEXT,
    content_type VARCHAR(20) DEFAULT 'text',
    author_handle VARCHAR(255),
    author_name VARCHAR(255),
    engagement_score INT DEFAULT 0,
    likes INT DEFAULT 0,
    shares INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    sentiment_score FLOAT,
    sentiment_label VARCHAR(20),
    language VARCHAR(10),
    cluster_id INT,
    theme VARCHAR(100),
    source_url TEXT,
    published_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    duplicate_of UUID,
    raw_data JSONB
);

-- ======================== TRANSCRIPTIONS ========================

CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    mention_id UUID REFERENCES mentions(id) ON DELETE CASCADE,
    source_type VARCHAR(20),
    transcript_text TEXT,
    language VARCHAR(10),
    duration_seconds INT,
    brand_mentions JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== SEVERITY SCORES ========================

CREATE TABLE IF NOT EXISTS severity_scores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    mention_id UUID REFERENCES mentions(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    severity_level VARCHAR(20) NOT NULL,
    severity_score FLOAT,
    sentiment_component FLOAT,
    engagement_component FLOAT,
    velocity_component FLOAT,
    keyword_component FLOAT,
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== FULFILLMENT RESULTS ========================

CREATE TABLE IF NOT EXISTS fulfillment_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    search_query JSONB,
    mention_id UUID REFERENCES mentions(id) ON DELETE CASCADE,
    passed BOOLEAN DEFAULT FALSE,
    score FLOAT,
    criteria_met JSONB,
    queued_for_scraping BOOLEAN DEFAULT FALSE,
    queued_for_transcription BOOLEAN DEFAULT FALSE,
    evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== ANALYSIS RUNS ========================

CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    total_mentions INT,
    overall_sentiment FLOAT,
    cluster_count INT,
    themes JSONB,
    risks JSONB,
    opportunities JSONB,
    severity_summary JSONB,
    llm_cost_usd FLOAT,
    ran_at TIMESTAMPTZ DEFAULT NOW()
);

-- ======================== INDEXES ========================

CREATE INDEX IF NOT EXISTS idx_mentions_platform ON mentions(platform);
CREATE INDEX IF NOT EXISTS idx_mentions_brand ON mentions(brand_id);
CREATE INDEX IF NOT EXISTS idx_mentions_scraped ON mentions(scraped_at);
CREATE INDEX IF NOT EXISTS idx_severity_level ON severity_scores(severity_level);
CREATE INDEX IF NOT EXISTS idx_severity_brand ON severity_scores(brand_id);
CREATE INDEX IF NOT EXISTS idx_yt_videos_brand ON youtube_videos(brand_id);
CREATE INDEX IF NOT EXISTS idx_yt_videos_video_id ON youtube_videos(video_id);
CREATE INDEX IF NOT EXISTS idx_ig_posts_brand ON instagram_posts(brand_id);
CREATE INDEX IF NOT EXISTS idx_reddit_posts_brand ON reddit_posts(brand_id);
CREATE INDEX IF NOT EXISTS idx_twitter_tweets_brand ON twitter_tweets(brand_id);
CREATE INDEX IF NOT EXISTS idx_telegram_messages_brand ON telegram_messages(brand_id);
CREATE INDEX IF NOT EXISTS idx_fb_posts_brand ON facebook_posts(brand_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_posts_brand ON linkedin_posts(brand_id);
CREATE INDEX IF NOT EXISTS idx_google_seo_brand ON google_seo_results(brand_id);
