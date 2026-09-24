-- Distância ausente não pode ser representada por 0: zero é uma medição válida.
-- Integrações que ainda aguardam roteamento persistem NULL e registram o estado
-- PENDING_ROUTING no metadata do pedido.
ALTER TABLE public."Order"
    ALTER COLUMN "distanceMeters" DROP NOT NULL;

ALTER TABLE public."Order"
    DROP CONSTRAINT IF EXISTS order_distance_meters_nonnegative;

ALTER TABLE public."Order"
    ADD CONSTRAINT order_distance_meters_nonnegative
    CHECK ("distanceMeters" IS NULL OR "distanceMeters" >= 0) NOT VALID;

ALTER TABLE public."Order"
    VALIDATE CONSTRAINT order_distance_meters_nonnegative;
