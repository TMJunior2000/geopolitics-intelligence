-- =============================================================================
-- DATABASE MASTER SCHEMA (V2.0 - Scalable Intelligence)
-- Include supporto per: YouTube, Truth Social, News, Broker Integration
-- =============================================================================

-- =============================================================================
-- 1. PULIZIA TOTALE (Hard Reset)
-- Attenzione: Cancella tutti i dati esistenti!
-- =============================================================================
DROP TABLE IF EXISTS trade_history CASCADE;       -- Futuro (Broker)
DROP TABLE IF EXISTS portfolio_positions CASCADE; -- Futuro (Broker)
DROP TABLE IF EXISTS broker_accounts CASCADE;     -- Futuro (Broker)
DROP TABLE IF EXISTS market_insights CASCADE;
DROP TABLE IF EXISTS intelligence_feed CASCADE;
DROP TABLE IF EXISTS sources CASCADE;
DROP TABLE IF EXISTS assets CASCADE;

-- =============================================================================
-- 2. TABELLA ASSETS (Anagrafica Strumenti Estesa)
-- =============================================================================
CREATE TABLE assets (
  ticker TEXT PRIMARY KEY,
  name TEXT,
  type TEXT -- 'COMMODITY', 'FOREX', 'STOCK', 'INDEX', 'CRYPTO', 'MACRO', 'BOND'
);

-- Inserimento massivo (Tutti i mercati + Nuovi Asset Macro per Trump)
INSERT INTO assets (ticker, name, type) VALUES 
-- 1. INDICI
('SPX500', 'S&P 500 Index', 'INDEX'),
('NQ100', 'Nasdaq 100 Index', 'INDEX'),
('DJ30', 'Dow Jones 30 Index', 'INDEX'),
('RUT2000', 'Russell 2000', 'INDEX'),
('DXY', 'US Dollar Index', 'INDEX'),
('VIX', 'Volatility Index', 'INDEX'),
('DAX40', 'DAX 40 Germany', 'INDEX'),
('FTSE100', 'FTSE 100 UK', 'INDEX'),
('CAC40', 'CAC 40 France', 'INDEX'),
('FTSEMIB', 'FTSE MIB Italy', 'INDEX'),
('IBEX35', 'IBEX 35 Spain', 'INDEX'),
('ESTX50', 'Euro Stoxx 50', 'INDEX'),
('NIKKEI225', 'Nikkei 225 Japan', 'INDEX'),
('HSI50', 'Hang Seng Hong Kong', 'INDEX'),
('NIFTY50', 'Nifty 50 India', 'INDEX'),
('CHINA50', 'China A50', 'INDEX'),

-- 2. FOREX
('EURUSD', 'Euro / US Dollar', 'FOREX'),
('GBPUSD', 'British Pound / US Dollar', 'FOREX'),
('USDJPY', 'US Dollar / Japanese Yen', 'FOREX'),
('USDCHF', 'US Dollar / Swiss Franc', 'FOREX'),
('USDCAD', 'US Dollar / Canadian Dollar', 'FOREX'),
('AUDUSD', 'Australian Dollar / US Dollar', 'FOREX'),
('NZDUSD', 'New Zealand Dollar / US Dollar', 'FOREX'),
('EURGBP', 'Euro / British Pound', 'FOREX'),
('EURJPY', 'Euro / Japanese Yen', 'FOREX'),
('EURCHF', 'Euro / Swiss Franc', 'FOREX'),
('GBPJPY', 'British Pound / Japanese Yen', 'FOREX'),
('AUDJPY', 'Australian Dollar / Japanese Yen', 'FOREX'),
('CADJPY', 'Canadian Dollar / Japanese Yen', 'FOREX'),
('EURAUD', 'Euro / Australian Dollar', 'FOREX'),
('GBPAUD', 'British Pound / Australian Dollar', 'FOREX'),
('USDMXN', 'US Dollar / Mexican Peso', 'FOREX'),
('USDZAR', 'US Dollar / South African Rand', 'FOREX'),
('USDTRY', 'US Dollar / Turkish Lira', 'FOREX'),

-- 3. COMMODITIES
('XAUUSD', 'Gold Spot', 'COMMODITY'),
('XAGUSD', 'Silver Spot', 'COMMODITY'),
('XPTUSD', 'Platinum Spot', 'COMMODITY'),
('HG1!', 'Copper Futures', 'COMMODITY'),
('WTI', 'Crude Oil WTI', 'COMMODITY'),
('BRENT', 'Crude Oil Brent', 'COMMODITY'),
('NGAS', 'Natural Gas', 'COMMODITY'),
('URANIUM', 'Uranium', 'COMMODITY'),
('CORN', 'Corn Futures', 'COMMODITY'),
('WHEAT', 'Wheat Futures', 'COMMODITY'),
('SOY', 'Soybean Futures', 'COMMODITY'),
('COFFEE', 'Coffee Futures', 'COMMODITY'),
('SUGAR', 'Sugar Futures', 'COMMODITY'),
('COCOA', 'Cocoa Futures', 'COMMODITY'),

-- 4. CRYPTO
('BTCUSD', 'Bitcoin', 'CRYPTO'),
('ETHUSD', 'Ethereum', 'CRYPTO'),
('SOLUSD', 'Solana', 'CRYPTO'),
('XRPUSD', 'Ripple', 'CRYPTO'),
('BNBUSD', 'Binance Coin', 'CRYPTO'),
('DOGEUSD', 'Dogecoin', 'CRYPTO'),
('ADAUSD', 'Cardano', 'CRYPTO'),
('AVAXUSD', 'Avalanche', 'CRYPTO'),
('DOTUSD', 'Polkadot', 'CRYPTO'),
('LINKUSD', 'Chainlink', 'CRYPTO'),

-- 5. STOCKS (Mag 7, DJ30, Nasdaq Top)
('NVDA', 'NVIDIA Corp.', 'STOCK'),
('MSFT', 'Microsoft Corp.', 'STOCK'),
('AAPL', 'Apple Inc.', 'STOCK'),
('GOOGL', 'Alphabet Inc.', 'STOCK'),
('AMZN', 'Amazon.com Inc.', 'STOCK'),
('META', 'Meta Platforms', 'STOCK'),
('TSLA', 'Tesla Inc.', 'STOCK'),
('AVGO', 'Broadcom Inc.', 'STOCK'),
('AMD', 'Advanced Micro Devices', 'STOCK'),
('NFLX', 'Netflix Inc.', 'STOCK'),
('ADBE', 'Adobe Inc.', 'STOCK'),
('CRM', 'Salesforce Inc.', 'STOCK'),
('ORCL', 'Oracle Corp.', 'STOCK'),
('CSCO', 'Cisco Systems', 'STOCK'),
('INTC', 'Intel Corp.', 'STOCK'),
('QCOM', 'Qualcomm Inc.', 'STOCK'),
('JPM', 'JPMorgan Chase', 'STOCK'),
('GS', 'Goldman Sachs', 'STOCK'),
('V', 'Visa Inc.', 'STOCK'),
('MA', 'Mastercard Inc.', 'STOCK'),
('WMT', 'Walmart Inc.', 'STOCK'),
('KO', 'Coca-Cola Co.', 'STOCK'),
('DIS', 'Walt Disney Co.', 'STOCK'),
('BA', 'Boeing Co.', 'STOCK'),
('CAT', 'Caterpillar Inc.', 'STOCK'),
('LLY', 'Eli Lilly', 'STOCK'),
('XOM', 'Exxon Mobil', 'STOCK'),
('UNH', 'UnitedHealth Group', 'STOCK'),

-- 6. BONDS
('US10Y', 'US 10Y Yield', 'BOND'),
('US02Y', 'US 2Y Yield', 'BOND'),
('DE10Y', 'Germany 10Y Yield', 'BOND'),
('IT10Y', 'Italy 10Y Yield', 'BOND'),

-- 7. NUOVI ASSET MACRO (Per Trump & News Geopolitiche)
('USD', 'US Dollar Generic', 'FOREX'),
('TARIFFS', 'Trade War / Tariffs Risk', 'MACRO'),
('FED', 'Federal Reserve Policy', 'MACRO'),
('WAR', 'Geopolitical Conflict Risk', 'MACRO')

ON CONFLICT (ticker) DO NOTHING;

-- =============================================================================
-- 3. TABELLA SOURCES (Canali Youtube & Social)
-- =============================================================================
CREATE TABLE sources (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  base_url TEXT,
  category TEXT DEFAULT 'VIDEO_ANALYSIS' -- 'VIDEO_ANALYSIS', 'SOCIAL', 'NEWS', 'PODCAST'
);

-- Inseriamo subito Truth Social per essere pronti
INSERT INTO sources (name, base_url, category) VALUES 
('Truth Social', 'https://truthsocial.com', 'SOCIAL');

-- =============================================================================
-- 4. TABELLA INTELLIGENCE_FEED (Hub Centrale Dati)
-- =============================================================================
CREATE TABLE intelligence_feed (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  source_id BIGINT REFERENCES sources(id),
  
  -- Contenuto
  title TEXT,       -- Titolo video o estratto post
  url TEXT UNIQUE NOT NULL,
  published_at TIMESTAMP WITH TIME ZONE,
  content TEXT,     -- Trascrizione Video o Testo Post
  feed_type TEXT DEFAULT 'VIDEO', -- 'VIDEO', 'SOCIAL_POST', 'ARTICLE'
  
  -- Analisi AI Raw
  summary TEXT, 
  macro_sentiment TEXT, -- 'macro_sentiment' dal prompt
  
  -- Metadati Flessibili (Likes, Views, Tags originali)
  raw_metadata JSONB
);

CREATE INDEX idx_feed_type ON intelligence_feed(feed_type);

-- =============================================================================
-- 5. TABELLA MARKET_INSIGHTS (Analisi e Segnali Operativi)
-- =============================================================================
CREATE TABLE market_insights (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  video_id BIGINT REFERENCES intelligence_feed(id) ON DELETE CASCADE,
  
  -- Info Asset
  asset_ticker TEXT NOT NULL REFERENCES assets(ticker), -- Link forte (Foreign Key)
  asset_name TEXT,
  channel_style TEXT, -- 'Tecnica', 'Fondamentale', 'Quantitativa', 'Macro/Geopolitics'
  
  -- Sentiment e Segnale
  sentiment TEXT,      -- 'Bullish', 'Bearish', 'Neutral/Range'
  recommendation TEXT, -- 'LONG', 'SHORT', 'WATCH', 'HOLD'
  time_horizon TEXT,   -- 'Intraday', 'Multiday/Weekly', 'News_Event'
  
  -- Metriche di Impatto (Fondamentale per Trump)
  impact_score INTEGER DEFAULT 0, -- 1-5 (5 = Market Mover / Black Swan)
  
  -- Livelli Operativi (Tecnici)
  entry_zone TEXT,
  target_price TEXT,
  stop_invalidation TEXT,
  
  -- Contenuti UI
  key_drivers JSONB,   -- ["Dazi Cina", "Taglio Tassi"]
  summary_card TEXT,   -- Frase breve per card UI
  
  -- Extra
  confidence_score INTEGER DEFAULT 5
);

-- =============================================================================
-- 6. INDICI E POLICY DI SICUREZZA
-- =============================================================================
CREATE INDEX idx_insights_ticker ON market_insights(asset_ticker);
CREATE INDEX idx_insights_style ON market_insights(channel_style);
CREATE INDEX idx_insights_impact ON market_insights(impact_score); -- Utile per filtrare "Breaking News"

ALTER TABLE intelligence_feed ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON market_insights FOR SELECT USING (true);
CREATE POLICY "Public read access" ON intelligence_feed FOR SELECT USING (true);

-- =============================================================================
-- FINE SETUP
-- =============================================================================