CREATE TABLE public."InvoiceSnapshot" (
    invoice_id UUID PRIMARY KEY REFERENCES public."WeeklyStoreInvoice"(id) ON DELETE RESTRICT,
    operator_id UUID NOT NULL REFERENCES public."Operator"(id) ON DELETE RESTRICT,
    "createdBy" UUID NOT NULL REFERENCES public."PlatformAdmin"(id) ON DELETE RESTRICT,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL
);
ALTER TABLE public."InvoiceSnapshot" ENABLE ROW LEVEL SECURITY;
CREATE POLICY invoice_snapshot_read ON public."InvoiceSnapshot" FOR SELECT
    USING (public.is_platform_admin() OR operator_id = public.current_operator_id());
CREATE POLICY invoice_snapshot_create ON public."InvoiceSnapshot" FOR INSERT
    WITH CHECK (public.is_platform_admin());
