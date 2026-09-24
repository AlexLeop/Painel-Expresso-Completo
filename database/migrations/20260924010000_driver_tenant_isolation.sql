-- F-02: exclusividade de motoboy e integridade referencial multi-tenant.
-- A API já restringe o tenant; estas constraints tornam o banco a última
-- barreira contra associações cruzadas feitas por SQL, jobs ou integrações.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM "StoreDriver" sd
        JOIN "Store" s ON s.id = sd.store_id
        JOIN "Driver" d ON d.id = sd.driver_id
        WHERE sd.operator_id <> s.operator_id
           OR sd.operator_id <> d.operator_id
    ) THEN
        RAISE EXCEPTION 'F-02: StoreDriver possui vínculos entre operadores; corrija os dados antes do deploy';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM "ScheduleEntry" se
        JOIN "Store" s ON s.id = se.store_id
        JOIN "Driver" d ON d.id = se.driver_id
        JOIN "Turno" t ON t.id = se.turno_id
        WHERE se.operator_id <> s.operator_id
           OR se.operator_id <> d.operator_id
           OR se.operator_id <> t.operator_id
    ) THEN
        RAISE EXCEPTION 'F-02: ScheduleEntry possui vínculos entre operadores; corrija os dados antes do deploy';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM "Turno" t
        JOIN "Store" s ON s.id = t.store_id
        WHERE t.operator_id <> s.operator_id
    ) THEN
        RAISE EXCEPTION 'F-02: Turno possui loja de outro operador; corrija os dados antes do deploy';
    END IF;

    IF EXISTS (
        SELECT regexp_replace(phone, '\\D', '', 'g')
        FROM "Driver"
        WHERE active AND regexp_replace(phone, '\\D', '', 'g') <> ''
        GROUP BY regexp_replace(phone, '\\D', '', 'g')
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'F-02: existem motoboys ativos com telefone duplicado entre operadores';
    END IF;

    IF EXISTS (
        SELECT regexp_replace(document, '\\D', '', 'g')
        FROM "Driver"
        WHERE active
          AND document IS NOT NULL
          AND regexp_replace(document, '\\D', '', 'g') <> ''
        GROUP BY regexp_replace(document, '\\D', '', 'g')
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'F-02: existem motoboys ativos com documento duplicado entre operadores';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_driver_active_phone_identity
    ON "Driver" ((regexp_replace(phone, '\\D', '', 'g')))
    WHERE active AND regexp_replace(phone, '\\D', '', 'g') <> '';

CREATE UNIQUE INDEX IF NOT EXISTS uq_driver_active_document_identity
    ON "Driver" ((regexp_replace(document, '\\D', '', 'g')))
    WHERE active
      AND document IS NOT NULL
      AND regexp_replace(document, '\\D', '', 'g') <> '';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_store_id_operator') THEN
        ALTER TABLE "Store" ADD CONSTRAINT uq_store_id_operator UNIQUE (id, operator_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_driver_id_operator') THEN
        ALTER TABLE "Driver" ADD CONSTRAINT uq_driver_id_operator UNIQUE (id, operator_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_turno_id_operator') THEN
        ALTER TABLE "Turno" ADD CONSTRAINT uq_turno_id_operator UNIQUE (id, operator_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_turno_store_same_operator') THEN
        ALTER TABLE "Turno"
            ADD CONSTRAINT fk_turno_store_same_operator
            FOREIGN KEY (store_id, operator_id)
            REFERENCES "Store" (id, operator_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_storedriver_store_same_operator') THEN
        ALTER TABLE "StoreDriver"
            ADD CONSTRAINT fk_storedriver_store_same_operator
            FOREIGN KEY (store_id, operator_id)
            REFERENCES "Store" (id, operator_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_storedriver_driver_same_operator') THEN
        ALTER TABLE "StoreDriver"
            ADD CONSTRAINT fk_storedriver_driver_same_operator
            FOREIGN KEY (driver_id, operator_id)
            REFERENCES "Driver" (id, operator_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_schedule_store_same_operator') THEN
        ALTER TABLE "ScheduleEntry"
            ADD CONSTRAINT fk_schedule_store_same_operator
            FOREIGN KEY (store_id, operator_id)
            REFERENCES "Store" (id, operator_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_schedule_driver_same_operator') THEN
        ALTER TABLE "ScheduleEntry"
            ADD CONSTRAINT fk_schedule_driver_same_operator
            FOREIGN KEY (driver_id, operator_id)
            REFERENCES "Driver" (id, operator_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_schedule_turno_same_operator') THEN
        ALTER TABLE "ScheduleEntry"
            ADD CONSTRAINT fk_schedule_turno_same_operator
            FOREIGN KEY (turno_id, operator_id)
            REFERENCES "Turno" (id, operator_id) NOT VALID;
    END IF;
END $$;

ALTER TABLE "Turno" VALIDATE CONSTRAINT fk_turno_store_same_operator;
ALTER TABLE "StoreDriver" VALIDATE CONSTRAINT fk_storedriver_store_same_operator;
ALTER TABLE "StoreDriver" VALIDATE CONSTRAINT fk_storedriver_driver_same_operator;
ALTER TABLE "ScheduleEntry" VALIDATE CONSTRAINT fk_schedule_store_same_operator;
ALTER TABLE "ScheduleEntry" VALIDATE CONSTRAINT fk_schedule_driver_same_operator;
ALTER TABLE "ScheduleEntry" VALIDATE CONSTRAINT fk_schedule_turno_same_operator;

CREATE UNIQUE INDEX IF NOT EXISTS uq_storedriver_tenant_membership
    ON "StoreDriver" (operator_id, store_id, driver_id);
