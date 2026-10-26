-- Datos exclusivamente sintéticos para la demostración de clase.
INSERT INTO customers(document_type,document_number,full_name,email,whatsapp,preferred_channel,special_attention) VALUES
('DNI','77654321','María Prueba Rojas','maria.prueba@example.com','51999900004','WHATSAPP',false),
('RUC','20601234567','Distribuidora Laboratorio SAC','cobranzas@laboratorio.example','51999900005','EMAIL',false),
('DNI','71234567','Carlos Demo Salas','carlos.demo@example.com','51999900006','WHATSAPP',false)
ON CONFLICT (document_number) DO NOTHING;

INSERT INTO obligations(customer_id,account_code,due_date,original_amount,outstanding_amount,status)
SELECT id,'CB-512',CURRENT_DATE-47,2400,1800,'OVERDUE' FROM customers WHERE document_number='77654321' ON CONFLICT (account_code) DO NOTHING;
INSERT INTO obligations(customer_id,account_code,due_date,original_amount,outstanding_amount,status)
SELECT id,'CB-613',CURRENT_DATE-8,12500,12500,'OVERDUE' FROM customers WHERE document_number='20601234567' ON CONFLICT (account_code) DO NOTHING;
INSERT INTO obligations(customer_id,account_code,due_date,original_amount,outstanding_amount,status)
SELECT id,'CB-714',CURRENT_DATE-65,1100,600,'OVERDUE' FROM customers WHERE document_number='71234567' ON CONFLICT (account_code) DO NOTHING;

INSERT INTO payment_history(customer_id,obligation_id,event_type,event_date,amount,status,details)
SELECT c.id,o.id,'PAYMENT',NOW()-INTERVAL '3 days',600,'APPLIED','Abono parcial aplicado; saldo pendiente sintético'
FROM customers c JOIN obligations o ON o.customer_id=c.id WHERE c.document_number='77654321' AND o.account_code='CB-512'
AND NOT EXISTS (SELECT 1 FROM payment_history WHERE obligation_id=o.id AND details LIKE 'Abono parcial aplicado%');
INSERT INTO payment_history(customer_id,obligation_id,event_type,event_date,amount,status,details)
SELECT c.id,o.id,'PROMISE',NOW()-INTERVAL '12 days',500,'BROKEN','Compromiso sintético vencido sin pago asociado'
FROM customers c JOIN obligations o ON o.customer_id=c.id WHERE c.document_number='71234567' AND o.account_code='CB-714'
AND NOT EXISTS (SELECT 1 FROM payment_history WHERE obligation_id=o.id AND status='BROKEN');

INSERT INTO policy_documents(document_code,version,section,title,content,access_role,embedding)
SELECT * FROM (VALUES
('POL-CAN-05','v2','§2 Canales autorizados','Política de contacto','Usar únicamente el canal preferido registrado y respetar la franja horaria autorizada. Todo recordatorio debe indicar saldo, canal de atención y opción de reportar un pago.','COBRANZA','[0.82,0.12,0.08,0.22]'::vector),
('MAN-ID-01','v1','§4 Validación de identidad','Manual de seguridad','Antes de revelar información detallada de una obligación, validar la identidad del cliente. No exponer datos personales completos en mensajes salientes.','COBRANZA','[0.61,0.08,0.66,0.12]'::vector),
('GUI-REC-06','v3','§6 Recepción de comprobantes','Guía de conciliación','Si el cliente reporta transferencia o adjunta comprobante, registrar el evento y pausar nuevas comunicaciones hasta completar la conciliación.','COBRANZA','[0.10,0.96,0.13,0.05]'::vector),
('POL-NEG-08','v4','§3 Alternativas de pago','Política de negociación','Las alternativas de fraccionamiento requieren revisar deuda total, comportamiento histórico y promesas previas. La aprobación final corresponde a un supervisor.','COBRANZA','[0.46,0.12,0.16,0.84]'::vector),
('MAN-VUL-03','v2','§5 Situaciones sensibles','Manual de atención especial','Ante dificultad económica declarada, reclamo abierto o condición vulnerable, detener la automatización y derivar el caso a un asesor humano.','COBRANZA','[0.08,0.11,0.97,0.12]'::vector),
('POL-AUD-01','v1','§8 Trazabilidad','Política de auditoría','Cada decisión debe conservar la consulta, fuentes consultadas, fragmentos recuperados, nivel de similitud y acción propuesta.','COBRANZA','[0.72,0.29,0.21,0.18]'::vector)
) AS v(document_code,version,section,title,content,access_role,embedding)
WHERE NOT EXISTS (SELECT 1 FROM policy_documents p WHERE p.document_code=v.document_code AND p.version=v.version);
