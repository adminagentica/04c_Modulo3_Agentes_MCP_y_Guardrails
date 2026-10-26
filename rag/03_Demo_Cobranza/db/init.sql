CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE customers (
  id serial PRIMARY KEY,
  document_type varchar(3) NOT NULL CHECK (document_type IN ('DNI','RUC')),
  document_number varchar(11) NOT NULL UNIQUE,
  full_name text NOT NULL,
  email text,
  whatsapp text,
  preferred_channel text NOT NULL DEFAULT 'WHATSAPP',
  special_attention boolean NOT NULL DEFAULT false
);

CREATE TABLE obligations (
  id serial PRIMARY KEY,
  customer_id int NOT NULL REFERENCES customers(id),
  account_code text NOT NULL UNIQUE,
  due_date date NOT NULL,
  original_amount numeric(12,2) NOT NULL,
  outstanding_amount numeric(12,2) NOT NULL,
  status text NOT NULL
);

CREATE TABLE payment_history (
  id serial PRIMARY KEY,
  customer_id int NOT NULL REFERENCES customers(id),
  obligation_id int REFERENCES obligations(id),
  event_type text NOT NULL,
  event_date timestamptz NOT NULL,
  amount numeric(12,2),
  status text NOT NULL,
  details text
);

CREATE TABLE policy_documents (
  id serial PRIMARY KEY,
  document_code text NOT NULL,
  version text NOT NULL,
  section text NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  access_role text NOT NULL DEFAULT 'COBRANZA',
  embedding vector(4) NOT NULL
);

INSERT INTO customers(document_type,document_number,full_name,email,whatsapp,preferred_channel,special_attention) VALUES
('DNI','74851236','Cliente Demo Uno','cliente.demo@example.com','51999900001','WHATSAPP',false),
('RUC','20548796321','Comercial Demo SAC','pagos@comercialdemo.example','51999900002','EMAIL',false),
('DNI','40112233','Cliente Atención Especial','atencion@example.com','51999900003','EMAIL',true);

INSERT INTO obligations(customer_id,account_code,due_date,original_amount,outstanding_amount,status) VALUES
(1,'CB-204',CURRENT_DATE - 18,1850,1850,'OVERDUE'),
(1,'CB-177',CURRENT_DATE - 90,900,0,'PAID'),
(2,'CB-310',CURRENT_DATE - 32,4800,3200,'OVERDUE'),
(3,'CB-411',CURRENT_DATE - 12,750,750,'OVERDUE');

INSERT INTO payment_history(customer_id,obligation_id,event_type,event_date,amount,status,details) VALUES
(1,2,'PAYMENT',NOW() - INTERVAL '80 days',900,'APPLIED','Pago aplicado correctamente'),
(1,1,'PROMISE',NOW() - INTERVAL '4 days',650,'PENDING','Propuesta registrada para revisión'),
(2,3,'PAYMENT',NOW() - INTERVAL '1 day',1600,'PENDING_RECONCILIATION','Pago informado, pendiente de conciliación'),
(2,3,'PROMISE',NOW() - INTERVAL '20 days',1200,'BROKEN','Promesa anterior incumplida'),
(3,4,'NOTE',NOW() - INTERVAL '2 days',NULL,'HUMAN_REVIEW','Caso marcado para atención humana');

INSERT INTO policy_documents(document_code,version,section,title,content,access_role,embedding) VALUES
('POL-COB-04','v3','§5 Gestión temprana','Política de cobranza temprana','Para atrasos de hasta 30 días, el agente puede preparar una propuesta dentro de los rangos autorizados. La confirmación requiere un responsable humano.','COBRANZA','[0.95,0.10,0.05,0.20]'),
('POL-PAG-02','v4','§4 Conciliación','Política de aplicación de pagos','Cuando existe un pago pendiente de conciliación se debe pausar el contacto de cobranza y derivar el caso a Operaciones.','COBRANZA','[0.10,0.95,0.15,0.05]'),
('MAN-ATN-02','v2','§3 Atención especial','Manual de atención al cliente','Los casos marcados para atención especial requieren intervención humana y no deben continuar con negociación automatizada.','COBRANZA','[0.05,0.15,0.95,0.10]'),
('POL-PRO-03','v3','§7 Promesas incumplidas','Política de promesas de pago','Una promesa incumplida requiere revisar el historial antes de presentar una nueva alternativa.','COBRANZA','[0.20,0.05,0.10,0.95]');
