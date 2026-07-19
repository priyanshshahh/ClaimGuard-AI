-- ClaimGuard-AI Phase 2/3: org-scoped multi-tenant schema

CREATE TABLE IF NOT EXISTS orgs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    org_id uuid NOT NULL REFERENCES orgs (id) ON DELETE CASCADE,
    display_name text,
    role text NOT NULL DEFAULT 'member',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS claims (
    org_id uuid NOT NULL REFERENCES orgs (id) ON DELETE CASCADE,
    claim_id text NOT NULL,
    claim_value_usd double precision NOT NULL DEFAULT 0,
    denial_probability double precision NOT NULL DEFAULT 0,
    expected_loss_usd double precision NOT NULL DEFAULT 0,
    risk_level text NOT NULL DEFAULT 'MEDIUM',
    payer_id text NOT NULL DEFAULT '',
    icd_10_code text NOT NULL DEFAULT '',
    cpt_code text NOT NULL DEFAULT '',
    documentation_complete integer NOT NULL DEFAULT 1,
    clinical_justification_present integer NOT NULL DEFAULT 1,
    procedure_mismatch_flag integer NOT NULL DEFAULT 0,
    patient_chart_notes text NOT NULL DEFAULT '',
    agent_correction_draft text NOT NULL DEFAULT '',
    explanation text NOT NULL DEFAULT '',
    recommended_action text NOT NULL DEFAULT '',
    confidence double precision NOT NULL DEFAULT 0.82,
    missing_elements jsonb NOT NULL DEFAULT '[]'::jsonb,
    predicted_denial_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    payer_days_to_pay integer NOT NULL DEFAULT 35,
    cash_flow_urgency double precision NOT NULL DEFAULT 0,
    model_base_probability double precision,
    is_demo boolean NOT NULL DEFAULT false,
    resolved boolean NOT NULL DEFAULT false,
    resolved_at timestamptz,
    resolved_by text,
    analyzed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, claim_id)
);

CREATE INDEX IF NOT EXISTS claims_org_resolved_idx ON claims (org_id, resolved, analyzed_at DESC);
CREATE INDEX IF NOT EXISTS profiles_org_id_idx ON profiles (org_id);

ALTER TABLE orgs ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;

CREATE POLICY orgs_select_own ON orgs
    FOR SELECT
    USING (
        id IN (SELECT org_id FROM profiles WHERE user_id = auth.uid())
    );

CREATE POLICY profiles_select_org ON profiles
    FOR SELECT
    USING (
        org_id IN (SELECT org_id FROM profiles WHERE user_id = auth.uid())
    );

CREATE POLICY profiles_update_self ON profiles
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY claims_select_org ON claims
    FOR SELECT
    USING (
        org_id IN (SELECT org_id FROM profiles WHERE user_id = auth.uid())
    );

CREATE POLICY claims_insert_org ON claims
    FOR INSERT
    WITH CHECK (
        org_id IN (SELECT org_id FROM profiles WHERE user_id = auth.uid())
    );

CREATE POLICY claims_update_org ON claims
    FOR UPDATE
    USING (
        org_id IN (SELECT org_id FROM profiles WHERE user_id = auth.uid())
    )
    WITH CHECK (
        org_id IN (SELECT org_id FROM profiles WHERE user_id = auth.uid())
    );

CREATE POLICY claims_delete_org ON claims
    FOR DELETE
    USING (
        org_id IN (SELECT org_id FROM profiles WHERE user_id = auth.uid())
    );
