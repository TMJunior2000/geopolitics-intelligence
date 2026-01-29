-- =============================================================================
-- 1. PULIZIA TOTALE (Reset)
-- Cancelliamo le tabelle a cascata per evitare errori di dipendenza
-- =============================================================================
DROP TABLE IF EXISTS technical_signals CASCADE;
DROP TABLE IF EXISTS market_insights CASCADE;
DROP TABLE IF EXISTS intelligence_feed CASCADE;
DROP TABLE IF EXISTS sources CASCADE;
DROP TABLE IF EXISTS assets CASCADE;

-- =============================================================================
-- 2. TABELLA ASSETS
-- Anagrafica degli strumenti finanziari. Utile per i filtri della Dashboard.
-- =============================================================================
CREATE TABLE assets (
  ticker TEXT PRIMARY KEY, -- Es: 'XAUUSD', 'MSFT'
  name TEXT,
  type TEXT -- Es: 'COMMODITY', 'FOREX', 'STOCK', 'INDEX', 'CRYPTO'
);

-- =============================================================================
-- POPOLAMENTO MASSIVO ASSETS (ULTRA-COMPLETO)
-- Include: Forex, Commodities, Indici, Crypto, Bond.
-- Stocks: Mag 7, DJ30, Nasdaq 100 Top, S&P 500 Key Sectors (Finanza, Energia, Pharma).
-- =============================================================================

INSERT INTO assets (ticker, name, type) VALUES 

-- 1. INDICI (Americhe, Europa, Asia, Volatilità)
('SPX500', 'S&P 500', 'INDEX'),
('NQ100', 'Nasdaq 100', 'INDEX'),
('DJ30', 'Dow Jones Industrial Average', 'INDEX'),
('RUT2000', 'Russell 2000 (Small Cap)', 'INDEX'),
('DXY', 'US Dollar Index', 'INDEX'),
('VIX', 'Volatility Index (Fear Index)', 'INDEX'),
('DAX40', 'DAX 40 (Germany)', 'INDEX'),
('FTSE100', 'FTSE 100 (UK)', 'INDEX'),
('CAC40', 'CAC 40 (France)', 'INDEX'),
('FTSEMIB', 'FTSE MIB (Italy)', 'INDEX'),
('IBEX35', 'IBEX 35 (Spain)', 'INDEX'),
('ESTX50', 'Euro Stoxx 50', 'INDEX'),
('NIKKEI225', 'Nikkei 225 (Japan)', 'INDEX'),
('HSI50', 'Hang Seng (Hong Kong)', 'INDEX'),
('NIFTY50', 'Nifty 50 (India)', 'INDEX'),
('CHINA50', 'China A50', 'INDEX'),

-- 2. FOREX (Majors, Minors & Crosses)
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

-- 3. COMMODITIES (Metalli, Energia, Softs)
('XAUUSD', 'Gold Spot', 'COMMODITY'),
('XAGUSD', 'Silver Spot', 'COMMODITY'),
('XPTUSD', 'Platinum Spot', 'COMMODITY'),
('HG1!', 'Copper Futures', 'COMMODITY'),
('WTI', 'Crude Oil WTI', 'COMMODITY'),
('BRENT', 'Crude Oil Brent', 'COMMODITY'),
('NGAS', 'Natural Gas', 'COMMODITY'),
('URANIUM', 'Uranium Futures', 'COMMODITY'), -- Settore nucleare citato nei video
('CORN', 'Corn Futures', 'COMMODITY'),
('WHEAT', 'Wheat Futures', 'COMMODITY'),
('SOY', 'Soybean Futures', 'COMMODITY'),
('COFFEE', 'Coffee Futures', 'COMMODITY'),
('SUGAR', 'Sugar Futures', 'COMMODITY'),
('COCOA', 'Cocoa Futures', 'COMMODITY'),

-- 4. CRYPTO (Top Market Cap & High Volatility)
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

-- 5. STOCKS - MAGNIFICENT 7 & BIG TECH (US100 Leaders)
('NVDA', 'NVIDIA Corp.', 'STOCK'),
('MSFT', 'Microsoft Corp.', 'STOCK'),
('AAPL', 'Apple Inc.', 'STOCK'),
('GOOGL', 'Alphabet Inc. (Google)', 'STOCK'),
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
('TXN', 'Texas Instruments', 'STOCK'),
('IBM', 'International Business Machines', 'STOCK'),
('PLTR', 'Palantir Technologies', 'STOCK'),
('SMCI', 'Super Micro Computer', 'STOCK'), -- Molto volatile, spesso citata
('ARM', 'Arm Holdings', 'STOCK'),

-- 6. STOCKS - FINANZA & PAGAMENTI (S&P 500 / DJ30)
('JPM', 'JPMorgan Chase & Co.', 'STOCK'),
('BAC', 'Bank of America Corp.', 'STOCK'),
('WFC', 'Wells Fargo & Co.', 'STOCK'),
('GS', 'Goldman Sachs Group', 'STOCK'),
('MS', 'Morgan Stanley', 'STOCK'),
('V', 'Visa Inc.', 'STOCK'),
('MA', 'Mastercard Inc.', 'STOCK'),
('AXP', 'American Express Co.', 'STOCK'),
('PYPL', 'PayPal Holdings', 'STOCK'),
('BLK', 'BlackRock Inc.', 'STOCK'),
('COIN', 'Coinbase Global', 'STOCK'), -- Proxy Crypto
('HOOD', 'Robinhood Markets', 'STOCK'),

-- 7. STOCKS - RETAIL & CONSUMER GOODS (DJ30 Staples)
('WMT', 'Walmart Inc.', 'STOCK'),
('TGT', 'Target Corp.', 'STOCK'),
('HD', 'Home Depot Inc.', 'STOCK'),
('AMZN', 'Amazon (Retail)', 'STOCK'),
('COST', 'Costco Wholesale', 'STOCK'),
('KO', 'Coca-Cola Co.', 'STOCK'),
('PEP', 'PepsiCo Inc.', 'STOCK'),
('MCD', 'McDonald''s Corp.', 'STOCK'),
('PG', 'Procter & Gamble', 'STOCK'),
('NKE', 'Nike Inc.', 'STOCK'),
('DIS', 'Walt Disney Co.', 'STOCK'),

-- 8. STOCKS - HEALTHCARE & PHARMA (Molto attive per GLP-1 drugs)
('LLY', 'Eli Lilly and Co.', 'STOCK'),
('NVO', 'Novo Nordisk', 'STOCK'),
('UNH', 'UnitedHealth Group', 'STOCK'),
('JNJ', 'Johnson & Johnson', 'STOCK'),
('PFE', 'Pfizer Inc.', 'STOCK'),
('MRK', 'Merck & Co.', 'STOCK'),
('ABBV', 'AbbVie Inc.', 'STOCK'),

-- 9. STOCKS - ENERGIA & INDUSTRIA (DJ30 / S&P500)
('XOM', 'Exxon Mobil Corp.', 'STOCK'),
('CVX', 'Chevron Corp.', 'STOCK'),
('SHEL', 'Shell PLC', 'STOCK'),
('OXY', 'Occidental Petroleum', 'STOCK'),
('CAT', 'Caterpillar Inc.', 'STOCK'),
('DE', 'Deere & Company', 'STOCK'),
('BA', 'Boeing Co.', 'STOCK'),
('LMT', 'Lockheed Martin', 'STOCK'), -- Settore Difesa/Geopolitica
('RTX', 'RTX Corp (Raytheon)', 'STOCK'),
('GE', 'General Electric', 'STOCK'),

-- 10. STOCKS - AUTOMOTIVE (Oltre Tesla)
('F', 'Ford Motor Co.', 'STOCK'),
('GM', 'General Motors', 'STOCK'),
('TM', 'Toyota Motor Corp.', 'STOCK'),
('RACE', 'Ferrari NV', 'STOCK'),
('STLA', 'Stellantis NV', 'STOCK'),

-- 11. BONDS (Titoli di Stato)
('US10Y', 'US 10 Year Treasury Yield', 'BOND'),
('US02Y', 'US 2 Year Treasury Yield', 'BOND'),
('US30Y', 'US 30 Year Treasury Yield', 'BOND'),
('DE10Y', 'Germany 10 Year Bund Yield', 'BOND'),
('IT10Y', 'Italy 10 Year BTP Yield', 'BOND')

ON CONFLICT (ticker) DO NOTHING;

-- =============================================================================
-- 3. TABELLA SOURCES
-- I canali YouTube o le fonti di notizie monitorate.
-- =============================================================================
CREATE TABLE sources (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  name TEXT UNIQUE NOT NULL, -- Es: '@InvestireBiz'
  base_url TEXT
);

-- =============================================================================
-- 4. TABELLA INTELLIGENCE_FEED
-- Memorizza il video grezzo, la trascrizione e i metadati di base.
-- =============================================================================
CREATE TABLE intelligence_feed (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  source_id BIGINT REFERENCES sources(id),
  
  title TEXT,
  url TEXT UNIQUE NOT NULL, -- Evita duplicati dello stesso video
  published_at TIMESTAMP WITH TIME ZONE,
  
  content TEXT, -- La trascrizione completa (può essere lunga)
  summary TEXT, -- Riassunto generato dall'AI
  
  raw_metadata JSONB -- Flessibilità per salvare ID video originali, tag, ecc.
);

-- =============================================================================
-- 5. TABELLA MARKET_INSIGHTS (CORE)
-- Contiene l'analisi strutturata estratta dall'AI.
-- Aggiornata per gestire Analisi Tecnica, Fondamentale e Macro.
-- =============================================================================
CREATE TABLE market_insights (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  
  -- Collegamento al video padre (Se il video viene cancellato, cancella anche gli insights)
  video_id BIGINT REFERENCES intelligence_feed(id) ON DELETE CASCADE,
  
  -- Identificazione Asset
  asset_ticker TEXT NOT NULL, -- Es: 'MSFT'. Non vincolato a foreign key per permettere nuovi asset scoperti dall'AI.
  asset_class TEXT, -- 'STOCK', 'FOREX', 'CRYPTO', 'INDEX', 'COMMODITY'
  
  -- Segnali Operativi
  sentiment TEXT CHECK (sentiment IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
  recommendation TEXT CHECK (recommendation IN ('BUY', 'SELL', 'WATCH', 'HOLD')),
  
  -- Dettagli Analisi
  timeframe TEXT, -- Es: 'INTRADAY', 'SHORT_TERM', 'LONG_TERM'
  key_levels TEXT, -- Es: "Supp: 150, Res: 160" (Testo libero per flessibilità)
  ai_reasoning TEXT, -- Il "Perché" visualizzato nella card della dashboard
  
  -- Contesto (Nuovi campi)
  catalyst TEXT, -- L'evento scatenante (es: "Earnings Q4", "Fed Meeting", "Stagionalità")
  confidence_score INTEGER DEFAULT 5 -- Da 1 a 10
);

-- Indici per velocizzare le query della Dashboard
CREATE INDEX idx_insights_ticker ON market_insights(asset_ticker);
CREATE INDEX idx_insights_created_at ON market_insights(created_at);

-- =============================================================================
-- 6. TABELLA TECHNICAL_SIGNALS (Opzionale/Futura)
-- Per segnali puramente algoritmici se vorrai espandere il sistema.
-- =============================================================================
CREATE TABLE technical_signals (
  id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  asset_ticker TEXT REFERENCES assets(ticker),
  pattern TEXT, 
  direction TEXT CHECK (direction IN ('LONG', 'SHORT')),
  status TEXT DEFAULT 'PENDING', 
  notes TEXT
);

-- Abilitazione Row Level Security (Opzionale, buona pratica su Supabase)
ALTER TABLE intelligence_feed ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_insights ENABLE ROW LEVEL SECURITY;
-- Policy di lettura pubblica (per permettere alla dashboard di leggere se non usa la service key)
CREATE POLICY "Public read access" ON market_insights FOR SELECT USING (true);
CREATE POLICY "Public read access" ON intelligence_feed FOR SELECT USING (true);