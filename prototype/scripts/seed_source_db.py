"""
Seed source_db with fintech test data scoped per role.

Idempotent — safe to re-run. Drops and recreates all tables.
Run via: python seed_source_db.py
Env: SOURCE_DSN (psycopg2-compatible connection string)
"""
import os
import psycopg2

DSN = os.environ.get(
    "SOURCE_DSN",
    "host=localhost port=5433 dbname=sourcedb user=user password=password",
)


SCHEMA_SQL = """
-- ── Shared tables (SUPPORT + FINANCE + BIZDEV) ────────────────────────────
CREATE TABLE IF NOT EXISTS companies (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    domain      TEXT,
    industry    TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT,
    price_usd   NUMERIC(12,2),
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ── SUPPORT tables ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tickets (
    id            SERIAL PRIMARY KEY,
    company_id    INT REFERENCES companies(id),
    subject       TEXT NOT NULL,
    status        TEXT CHECK (status IN ('open','in_progress','resolved','closed')),
    priority      TEXT CHECK (priority IN ('low','medium','high','critical')),
    created_by    TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    resolved_at   TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_contacts (
    id          SERIAL PRIMARY KEY,
    company_id  INT REFERENCES companies(id),
    name        TEXT NOT NULL,
    email       TEXT,
    phone       TEXT,
    role        TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS faq_entries (
    id          SERIAL PRIMARY KEY,
    category    TEXT,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- ── FINANCE tables ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    company_id      INT REFERENCES companies(id),
    amount          NUMERIC(14,2) NOT NULL,
    currency        TEXT DEFAULT 'USD',
    direction       TEXT CHECK (direction IN ('credit','debit')),
    status          TEXT CHECK (status IN ('pending','cleared','failed','reversed')),
    reference       TEXT,
    transaction_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id            SERIAL PRIMARY KEY,
    transaction_id INT REFERENCES transactions(id),
    account_code  TEXT NOT NULL,
    debit         NUMERIC(14,2) DEFAULT 0,
    credit        NUMERIC(14,2) DEFAULT 0,
    description   TEXT,
    entry_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS financial_reports (
    id           SERIAL PRIMARY KEY,
    report_type  TEXT CHECK (report_type IN ('P&L','balance_sheet','cash_flow','budget')),
    period       TEXT NOT NULL,
    total_revenue   NUMERIC(14,2),
    total_expenses  NUMERIC(14,2),
    net_income      NUMERIC(14,2),
    generated_at    TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);

-- ── BIZDEV tables ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS deals (
    id           SERIAL PRIMARY KEY,
    company_id   INT REFERENCES companies(id),
    title        TEXT NOT NULL,
    stage        TEXT CHECK (stage IN ('prospect','negotiation','signed','closed_lost')),
    deal_value   NUMERIC(14,2),
    owner        TEXT,
    created_at   TIMESTAMP DEFAULT NOW(),
    closed_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_history (
    id           SERIAL PRIMARY KEY,
    company_id   INT REFERENCES companies(id),
    event_type   TEXT,
    description  TEXT NOT NULL,
    occurred_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS partner_agreements (
    id             SERIAL PRIMARY KEY,
    company_id     INT REFERENCES companies(id),
    agreement_type TEXT CHECK (agreement_type IN ('NDA','reseller','referral','integration')),
    status         TEXT CHECK (status IN ('draft','active','expired','terminated')),
    signed_at      TIMESTAMP,
    expires_at     TIMESTAMP,
    notes          TEXT
);
"""


DATA_SQL = """
-- ── Companies (shared) ─────────────────────────────────────────────────────
INSERT INTO companies (id, name, domain, industry) VALUES
  (1, 'Acme Corp',       'acme.com',       'SaaS'),
  (2, 'Beta Finance',    'betafin.com',    'Fintech'),
  (3, 'Gamma Retail',    'gamma.com',      'Retail'),
  (4, 'Delta Partners',  'deltapart.com',  'Consulting'),
  (5, 'Epsilon Health',  'epsilonhealth.com', 'Healthcare')
ON CONFLICT (id) DO NOTHING;

-- ── Products (shared) ──────────────────────────────────────────────────────
INSERT INTO products (id, name, category, price_usd) VALUES
  (1, 'Analytics Pro',   'SaaS',    299.00),
  (2, 'Data Vault',      'Storage', 149.00),
  (3, 'Insight Suite',   'SaaS',    499.00),
  (4, 'Connector API',   'API',      99.00),
  (5, 'Compliance Guard','Compliance',799.00)
ON CONFLICT (id) DO NOTHING;

-- ── Tickets (SUPPORT) ─────────────────────────────────────────────────────
INSERT INTO tickets (id, company_id, subject, status, priority, created_by) VALUES
  (1, 1, 'Cannot login to dashboard',         'open',        'high',   'alice@acme.com'),
  (2, 1, 'Export to CSV fails for large sets', 'in_progress', 'medium', 'bob@acme.com'),
  (3, 2, 'Password reset email not arriving',  'resolved',    'high',   'carol@betafin.com'),
  (4, 3, 'API rate limit hit unexpectedly',    'open',        'critical','dave@gamma.com'),
  (5, 4, 'Wrong currency displayed in invoice','closed',      'low',    'eve@deltapart.com'),
  (6, 5, 'MFA not working after phone change', 'in_progress', 'critical','frank@epsilonhealth.com')
ON CONFLICT (id) DO NOTHING;

-- ── Customer contacts (SUPPORT) ───────────────────────────────────────────
INSERT INTO customer_contacts (id, company_id, name, email, phone, role) VALUES
  (1, 1, 'Alice Johnson',  'alice@acme.com',       '+14155550101', 'CTO'),
  (2, 1, 'Bob Smith',      'bob@acme.com',         '+14155550102', 'Engineer'),
  (3, 2, 'Carol White',    'carol@betafin.com',    '+14155550103', 'Head of Ops'),
  (4, 3, 'Dave Brown',     'dave@gamma.com',       '+14155550104', 'CEO'),
  (5, 4, 'Eve Davis',      'eve@deltapart.com',    '+14155550105', 'Account Manager'),
  (6, 5, 'Frank Miller',   'frank@epsilonhealth.com','+14155550106','IT Director')
ON CONFLICT (id) DO NOTHING;

-- ── FAQ entries (SUPPORT) ─────────────────────────────────────────────────
INSERT INTO faq_entries (id, category, question, answer) VALUES
  (1, 'Login',     'How do I reset my password?',
                   'Go to Settings > Security > Reset Password and follow the email link.'),
  (2, 'Billing',   'Where can I find my invoices?',
                   'Invoices are available under Account > Billing > Invoice History.'),
  (3, 'API',       'What are the API rate limits?',
                   'Default is 1000 requests/minute. Contact support to increase limits.'),
  (4, 'Security',  'How do I enable MFA?',
                   'Navigate to Settings > Security > Two-Factor Authentication and scan the QR code.'),
  (5, 'Data',      'Can I export my data?',
                   'Yes, use the Export button on any table view. CSV and JSON formats supported.')
ON CONFLICT (id) DO NOTHING;

-- ── Transactions (FINANCE) ────────────────────────────────────────────────
INSERT INTO transactions (id, company_id, amount, currency, direction, status, reference) VALUES
  (1, 1, 12500.00, 'USD', 'credit', 'cleared',  'INV-2024-001'),
  (2, 1,  3200.00, 'USD', 'debit',  'cleared',  'EXP-2024-042'),
  (3, 2, 87000.00, 'USD', 'credit', 'cleared',  'INV-2024-002'),
  (4, 2,  1500.00, 'USD', 'debit',  'pending',  'EXP-2024-043'),
  (5, 3,  4400.00, 'USD', 'credit', 'cleared',  'INV-2024-003'),
  (6, 3,   750.00, 'USD', 'debit',  'failed',   'EXP-2024-044'),
  (7, 4, 23100.00, 'USD', 'credit', 'cleared',  'INV-2024-004'),
  (8, 5,  9800.00, 'USD', 'credit', 'reversed', 'INV-2024-005')
ON CONFLICT (id) DO NOTHING;

-- ── Ledger entries (FINANCE) ──────────────────────────────────────────────
INSERT INTO ledger_entries (id, transaction_id, account_code, debit, credit, description) VALUES
  (1, 1, '1000-AR', 0.00,     12500.00, 'Accounts Receivable - Acme Corp'),
  (2, 1, '4000-REV',12500.00, 0.00,     'Revenue recognition - Acme Corp'),
  (3, 2, '6000-EXP',3200.00,  0.00,     'Operating expense'),
  (4, 2, '2000-AP',  0.00,    3200.00,  'Accounts Payable'),
  (5, 3, '1000-AR',  0.00,    87000.00, 'Accounts Receivable - Beta Finance'),
  (6, 3, '4000-REV', 87000.00,0.00,     'Revenue recognition - Beta Finance')
ON CONFLICT (id) DO NOTHING;

-- ── Financial reports (FINANCE) ───────────────────────────────────────────
INSERT INTO financial_reports (id, report_type, period, total_revenue, total_expenses, net_income, notes) VALUES
  (1, 'P&L',           'Q1-2024', 215000.00, 128000.00, 87000.00,  'Strong SaaS growth'),
  (2, 'P&L',           'Q2-2024', 243000.00, 141000.00, 102000.00, 'New enterprise deal closed'),
  (3, 'balance_sheet', 'Q2-2024', NULL,       NULL,      NULL,      'Total assets 1.2M'),
  (4, 'cash_flow',     'Q2-2024', NULL,       NULL,      98000.00,  'Operating cash flow positive'),
  (5, 'budget',        'FY-2025', 1100000.00, 680000.00, 420000.00, 'Board-approved annual budget')
ON CONFLICT (id) DO NOTHING;

-- ── Deals (BIZDEV) ────────────────────────────────────────────────────────
INSERT INTO deals (id, company_id, title, stage, deal_value, owner) VALUES
  (1, 1, 'Acme Corp - Enterprise Expansion',    'negotiation', 120000.00, 'sarah@internal.com'),
  (2, 2, 'Beta Finance - Platform Integration', 'signed',      350000.00, 'james@internal.com'),
  (3, 3, 'Gamma Retail - Pilot Program',        'prospect',     25000.00, 'sarah@internal.com'),
  (4, 4, 'Delta Partners - Reseller Agreement', 'negotiation',  80000.00, 'james@internal.com'),
  (5, 5, 'Epsilon Health - Compliance Bundle',  'closed_lost',  95000.00, 'sarah@internal.com')
ON CONFLICT (id) DO NOTHING;

-- ── Company history (BIZDEV) ──────────────────────────────────────────────
INSERT INTO company_history (id, company_id, event_type, description) VALUES
  (1, 1, 'funding',      'Acme Corp raised Series B - $40M led by Sequoia'),
  (2, 1, 'product',      'Launched v3.0 platform with AI-assisted analytics'),
  (3, 2, 'acquisition',  'Beta Finance acquired PayStream for $12M'),
  (4, 2, 'partnership',  'Announced strategic partnership with GlobalBank'),
  (5, 3, 'leadership',   'New CTO hired from Amazon AWS division'),
  (6, 4, 'contract',     'Signed 3-year reseller agreement renewed'),
  (7, 5, 'regulatory',   'Achieved SOC2 Type II certification')
ON CONFLICT (id) DO NOTHING;

-- ── Partner agreements (BIZDEV) ───────────────────────────────────────────
INSERT INTO partner_agreements (id, company_id, agreement_type, status, notes) VALUES
  (1, 1, 'integration', 'active',    'API integration with Acme CRM'),
  (2, 2, 'reseller',    'active',    'Beta Finance resells to EU market'),
  (3, 3, 'referral',    'active',    'Gamma Retail referral commission 15%'),
  (4, 4, 'NDA',         'expired',   'Initial NDA from 2022 engagement'),
  (5, 5, 'NDA',         'active',    'Current NDA signed by both parties')
ON CONFLICT (id) DO NOTHING;
"""


def run() -> None:
    print("Connecting to source_db …")
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        print("Creating schema …")
        cur.execute(SCHEMA_SQL)

        print("Seeding data …")
        cur.execute(DATA_SQL)

        conn.commit()
        print("✓ source_db seeded successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"✗ Seed failed: {exc}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
