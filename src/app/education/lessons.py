"""Structured Bitcoin learning curriculum — bilingual (English / Spanish).

``LESSONS`` is a list of lesson dicts. Each lesson contains:

    id            : str   — unique slug
    title_en      : str
    title_es      : str
    description_en: str   — short summary (1-2 sentences)
    description_es: str
    category      : str   — matches glossary.CATEGORIES
    difficulty    : str   — beginner / intermediate / advanced
    duration_min  : int   — estimated reading time in minutes
    content_en    : str   — full lesson body in English
    content_es    : str   — full lesson body in Spanish
    quiz          : list  — list of question dicts (see below)

Each quiz question dict:
    question_en   : str
    question_es   : str
    options       : list[str]  — 4 answer options (language-independent labels)
    correct_index : int        — 0-based index of the correct option
    explanation_en: str        — why this answer is correct
    explanation_es: str

Helper functions
----------------
    get_lesson(lesson_id: str) -> dict | None
    list_lessons(category=None, difficulty=None) -> list[dict]
"""

from __future__ import annotations

LESSONS: list[dict] = [
    # =========================================================================
    # 1. What is Bitcoin?
    # =========================================================================
    {
        "id": "what-is-bitcoin",
        "title_en": "What is Bitcoin?",
        "title_es": "¿Qué es Bitcoin?",
        "description_en": (
            "An introduction to Bitcoin — what it is, why it was created, and why "
            "it matters for people around the world."
        ),
        "description_es": (
            "Una introducción a Bitcoin — qué es, por qué fue creado y por qué "
            "importa para las personas en todo el mundo."
        ),
        "category": "basics",
        "difficulty": "beginner",
        "duration_min": 8,
        "content_en": """
## What is Bitcoin?

Bitcoin is a peer-to-peer electronic cash system, described in a nine-page whitepaper published on October 31, 2008, by the pseudonymous Satoshi Nakamoto. The timing was deliberate: the world was in the middle of the worst financial crisis since the Great Depression, and the first Bitcoin block — the genesis block — was mined on January 3, 2009, with a headline embedded in it: "Chancellor on brink of second bailout for banks."

### The Problem Bitcoin Solves

Before Bitcoin, all digital payment systems required a trusted third party — a bank, a payment processor, or a government — to prevent the same digital money from being spent twice (the "double-spend problem"). This dependency on trust created systemic risks: institutions could freeze accounts, inflate the money supply, or simply fail.

Bitcoin solves the double-spend problem without a trusted intermediary by using a distributed ledger (the blockchain) maintained by thousands of independent computers (nodes). Every transaction is cryptographically signed by the sender and permanently recorded in a public, immutable ledger that anyone can verify.

### Key Properties

**Decentralized** — No single entity controls Bitcoin. Rules are enforced by the network's consensus, not by any company or government.

**Scarce** — Only 21 million bitcoin will ever exist. This limit is enforced by code, not by policy. Contrast this with traditional currencies, where central banks can — and do — print money.

**Permissionless** — Anyone with an internet connection can send or receive Bitcoin without asking anyone's permission. No ID, no credit check, no bank account required.

**Censorship-resistant** — No one can stop a valid Bitcoin transaction from being confirmed, and no one can reverse a confirmed transaction.

**Transparent** — Every transaction ever made is visible on the public blockchain. While addresses are pseudonymous, the ledger itself is open to anyone.

**Self-sovereign** — When you hold your own private keys, you — and only you — control your Bitcoin. No institution can freeze or confiscate it.

### Bitcoin vs. the Dollar

The U.S. dollar and every other national currency are controlled by central banks that can increase supply at will. Since 2008, the Federal Reserve's balance sheet has grown from under $1 trillion to over $7 trillion. Bitcoin cannot be inflated — its supply schedule is fixed forever. This makes Bitcoin a form of digital hard money, often compared to gold but with the portability of email.

### El Salvador and Bitcoin

In September 2021, El Salvador became the first country to adopt Bitcoin as legal tender. For a country where about 70% of the population was unbanked and over 20% of GDP came from remittances (which carried fees of 5-10%), Bitcoin offered a revolutionary alternative — instant transfers, near-zero fees, and no intermediaries.

### Getting Started

You don't need to understand all the technical details to use Bitcoin. All you need is:
1. A wallet — an app that stores your private keys.
2. A small amount of Bitcoin — you can start with less than $1 worth of sats.
3. A basic understanding of how to send and receive payments.

As you learn more, you'll discover that Bitcoin's simplicity on the surface is backed by decades of cryptography research and some of the most elegant mathematics in computer science.
""",
        "content_es": """
## ¿Qué es Bitcoin?

Bitcoin es un sistema de dinero electrónico entre pares, descrito en un documento de nueve páginas publicado el 31 de octubre de 2008 por el seudónimo Satoshi Nakamoto. El momento fue deliberado: el mundo estaba en medio de la peor crisis financiera desde la Gran Depresión, y el primer bloque Bitcoin — el bloque génesis — fue minado el 3 de enero de 2009 con un titular incrustado: "Chancellor on brink of second bailout for banks" (El canciller a punto de un segundo rescate para los bancos).

### El Problema que Bitcoin Resuelve

Antes de Bitcoin, todos los sistemas de pago digital requerían un tercero de confianza — un banco, un procesador de pagos o un gobierno — para evitar que el mismo dinero digital se gastara dos veces (el "problema del doble gasto"). Esta dependencia de la confianza creaba riesgos sistémicos: las instituciones podían congelar cuentas, inflar la oferta monetaria o simplemente fallar.

Bitcoin resuelve el problema del doble gasto sin un intermediario de confianza usando un libro mayor distribuido (la blockchain) mantenido por miles de computadoras independientes (nodos). Cada transacción es firmada criptográficamente por el remitente y registrada permanentemente en un libro mayor público e inmutable que cualquiera puede verificar.

### Propiedades Clave

**Descentralizado** — Ninguna entidad controla Bitcoin. Las reglas son aplicadas por el consenso de la red, no por ninguna empresa o gobierno.

**Escaso** — Solo existirán 21 millones de bitcoin. Este límite está aplicado por código, no por política.

**Sin permisos** — Cualquier persona con conexión a internet puede enviar o recibir Bitcoin sin pedir permiso. Sin ID, sin verificación de crédito, sin cuenta bancaria.

**Resistente a la censura** — Nadie puede detener una transacción Bitcoin válida de ser confirmada, ni nadie puede revertir una transacción confirmada.

**Transparente** — Cada transacción realizada es visible en la blockchain pública.

**Soberano** — Cuando tienes tus propias claves privadas, tú — y solo tú — controlas tu Bitcoin.

### El Salvador y Bitcoin

En septiembre de 2021, El Salvador se convirtió en el primer país en adoptar Bitcoin como moneda de curso legal. Para un país donde aproximadamente el 70% de la población no tenía cuenta bancaria y más del 20% del PIB provenía de remesas (con comisiones del 5-10%), Bitcoin ofreció una alternativa revolucionaria — transferencias instantáneas, comisiones casi nulas y sin intermediarios.
""",
        "quiz": [
            {
                "question_en": "What problem does Bitcoin solve without a trusted third party?",
                "question_es": "¿Qué problema resuelve Bitcoin sin un tercero de confianza?",
                "options": [
                    "A) The inflation problem",
                    "B) The double-spend problem",
                    "C) The identity verification problem",
                    "D) The transaction speed problem",
                ],
                "correct_index": 1,
                "explanation_en": "Bitcoin's blockchain prevents double-spending by recording all transactions in an immutable, distributed ledger verified by the network.",
                "explanation_es": "La blockchain de Bitcoin previene el doble gasto registrando todas las transacciones en un libro mayor inmutable y distribuido verificado por la red.",
            },
            {
                "question_en": "What is the maximum supply of Bitcoin?",
                "question_es": "¿Cuál es el suministro máximo de Bitcoin?",
                "options": [
                    "A) 100 million BTC",
                    "B) 21 billion BTC",
                    "C) 21 million BTC",
                    "D) Unlimited",
                ],
                "correct_index": 2,
                "explanation_en": "Bitcoin's protocol enforces a hard cap of exactly 21 million coins, making it the scarcest monetary asset ever created.",
                "explanation_es": "El protocolo de Bitcoin aplica un límite máximo de exactamente 21 millones de monedas, haciéndolo el activo monetario más escaso jamás creado.",
            },
        ],
    },
    # =========================================================================
    # 2. How Bitcoin Transactions Work
    # =========================================================================
    {
        "id": "how-transactions-work",
        "title_en": "How Bitcoin Transactions Work",
        "title_es": "Cómo Funcionan las Transacciones Bitcoin",
        "description_en": (
            "Learn how Bitcoin transactions are constructed, signed, broadcast, "
            "and confirmed on the blockchain."
        ),
        "description_es": (
            "Aprende cómo se construyen, firman, difunden y confirman las "
            "transacciones Bitcoin en la blockchain."
        ),
        "category": "transactions",
        "difficulty": "beginner",
        "duration_min": 10,
        "content_en": """
## How Bitcoin Transactions Work

A Bitcoin transaction is a message that says: "I, the owner of these satoshis, authorize their transfer to this new owner." It is the fundamental building block of the Bitcoin system.

### Anatomy of a Transaction

Every transaction has three core components:

**Inputs** — References to previous transactions that prove where the Bitcoin is coming from. Each input points to a specific Unspent Transaction Output (UTXO) by its transaction ID and output index. The input also contains a cryptographic signature proving the sender has the private key corresponding to the UTXO's locking script.

**Outputs** — Destinations for the satoshis. Each output has two parts: an amount (in satoshis) and a locking script (scriptPubKey) that specifies the conditions to spend it. A typical transaction has two outputs: the payment amount to the recipient, and change back to the sender.

**Fee** — The difference between the sum of input values and the sum of output values. There is no explicit fee field — it is implicit. Miners collect the fee as part of their block reward.

### Step-by-Step: Sending Bitcoin

1. **Wallet assembles inputs** — Your wallet selects which UTXOs to spend. If you have 50,000 sats and want to send 30,000, the wallet might select a 50,000-sat UTXO.

2. **Wallet creates outputs** — One output of 30,000 sats to the recipient's address. One change output of ~19,000 sats back to your wallet (the ~1,000 difference is the miner fee).

3. **Transaction is signed** — Your wallet uses your private key to create an ECDSA or Schnorr signature proving you own the inputs. The signature covers the transaction data so it cannot be modified after signing.

4. **Transaction is broadcast** — Your wallet sends the raw transaction to the Bitcoin peer-to-peer network. It propagates from node to node.

5. **Transaction enters the mempool** — Every node that receives the transaction validates it and places it in their local mempool (memory pool of unconfirmed transactions).

6. **Miner picks and mines** — A miner selects transactions from their mempool (prioritizing by fee rate), assembles a block, and mines it by finding a valid proof-of-work nonce.

7. **Block is confirmed** — Once a block containing your transaction is mined and accepted by the network, your transaction has 1 confirmation. Each subsequent block adds another confirmation.

### Confirmations and Security

The more confirmations a transaction has, the more computationally expensive it becomes to reverse:

- **0 confirmations** (unconfirmed): In the mempool; could be replaced (if RBF is enabled) or dropped.
- **1 confirmation**: Generally safe for small amounts.
- **3 confirmations**: Recommended for moderate amounts.
- **6 confirmations**: Bitcoin community standard for large amounts; an attacker would need to redo 6 blocks' worth of proof-of-work.

### Transaction Malleability (and how SegWit fixed it)

Before SegWit (2017), signature data was part of the main transaction body, and it was possible to create alternate valid signatures for the same transaction, changing the transaction ID without changing the economic content. This was called "transaction malleability" and was a blocker for the Lightning Network. SegWit moved signature data to a separate "witness" section, solving this problem.
""",
        "content_es": """
## Cómo Funcionan las Transacciones Bitcoin

Una transacción Bitcoin es un mensaje que dice: "Yo, el propietario de estos satoshis, autorizo su transferencia a este nuevo propietario." Es el bloque fundamental del sistema Bitcoin.

### Anatomía de una Transacción

Cada transacción tiene tres componentes principales:

**Entradas** — Referencias a transacciones anteriores que prueban de dónde proviene el Bitcoin. Cada entrada apunta a un UTXO específico por su ID de transacción e índice de salida. La entrada también contiene una firma criptográfica que prueba que el remitente tiene la clave privada.

**Salidas** — Destinos para los satoshis. Cada salida tiene un monto (en satoshis) y un script de bloqueo que especifica las condiciones para gastarlo. Una transacción típica tiene dos salidas: el monto de pago al receptor y el cambio de vuelta al remitente.

**Tarifa** — La diferencia entre la suma de los valores de entrada y la suma de los valores de salida. No hay campo de tarifa explícito — es implícita. Los mineros cobran la tarifa como parte de su recompensa de bloque.

### Paso a Paso: Enviar Bitcoin

1. **La billetera ensambla entradas** — Tu billetera selecciona qué UTXOs gastar.
2. **La billetera crea salidas** — Una salida al receptor y una de cambio de vuelta a tu billetera.
3. **La transacción es firmada** — Tu billetera usa tu clave privada para crear una firma que prueba que eres el dueño.
4. **La transacción es difundida** — Tu billetera envía la transacción raw a la red Bitcoin.
5. **La transacción entra al mempool** — Cada nodo la valida y la coloca en su mempool local.
6. **El minero la selecciona** — Un minero selecciona transacciones del mempool, ensambla un bloque y lo mina.
7. **El bloque es confirmado** — Tu transacción tiene 1 confirmación. Cada bloque posterior añade otra.
""",
        "quiz": [
            {
                "question_en": "What is the Bitcoin miner fee?",
                "question_es": "¿Qué es la tarifa de minería de Bitcoin?",
                "options": [
                    "A) A fixed fee of 1,000 sats per transaction",
                    "B) The difference between total input values and total output values",
                    "C) A percentage of the transaction amount",
                    "D) A fee paid to the Bitcoin Foundation",
                ],
                "correct_index": 1,
                "explanation_en": "The miner fee is implicit — it is the difference between the sum of input values and the sum of output values, and is collected by the miner who confirms the block.",
                "explanation_es": "La tarifa del minero es implícita — es la diferencia entre la suma de los valores de entrada y la suma de los valores de salida.",
            },
            {
                "question_en": "How many confirmations does the Bitcoin community recommend for large amounts?",
                "question_es": "¿Cuántas confirmaciones recomienda la comunidad Bitcoin para grandes cantidades?",
                "options": ["A) 1", "B) 3", "C) 6", "D) 100"],
                "correct_index": 2,
                "explanation_en": "6 confirmations is the community standard for high-value transactions, as it would require an attacker to redo 6 blocks of proof-of-work.",
                "explanation_es": "6 confirmaciones es el estándar para transacciones de alto valor, ya que requeriría que un atacante rehaga 6 bloques de prueba de trabajo.",
            },
        ],
    },
    # =========================================================================
    # 3. Understanding UTXOs
    # =========================================================================
    {
        "id": "understanding-utxos",
        "title_en": "Understanding UTXOs",
        "title_es": "Entendiendo los UTXOs",
        "description_en": (
            "Discover how Bitcoin tracks ownership through the UTXO model "
            "and why coin management matters for fees and privacy."
        ),
        "description_es": (
            "Descubre cómo Bitcoin rastrea la propiedad mediante el modelo UTXO "
            "y por qué la gestión de monedas importa para las tarifas y la privacidad."
        ),
        "category": "transactions",
        "difficulty": "intermediate",
        "duration_min": 12,
        "content_en": """
## Understanding UTXOs

Bitcoin does not use an account model like a bank. There is no ledger entry that says "Alice has 1.5 BTC." Instead, Bitcoin tracks ownership through Unspent Transaction Outputs (UTXOs) — discrete chunks of Bitcoin that can only be spent in their entirety.

### What is a UTXO?

When you receive Bitcoin, a new UTXO is created — a specific amount locked to a locking script (usually your address). Your "wallet balance" is actually the sum of all UTXOs that your wallet controls through the corresponding private keys.

Think of UTXOs like physical coins and banknotes. If you have a 50-sat "coin" and want to pay 30 sats, you cannot split the coin and hand over just part of it. You hand over the entire 50-sat coin and receive 20 sats in change. Bitcoin works the same way.

### UTXO Set

The set of all unspent transaction outputs in existence is called the UTXO set. Every full node maintains the entire UTXO set in memory to validate new transactions instantly. The UTXO set is much smaller than the full blockchain — it only contains outputs that have not yet been spent.

As of recent years, the UTXO set contains tens of millions of entries. Managing this set efficiently is crucial for Bitcoin node performance, which is why outputs that are too small to be worth spending ("dust") are a concern — they bloat the UTXO set indefinitely.

### UTXO Lifecycle

1. **Creation** — A transaction output is created with an amount and a locking script. It enters the UTXO set.
2. **Stored** — The UTXO remains unspent in the UTXO set until it is referenced by a future transaction.
3. **Spent** — A transaction uses the UTXO as an input, removes it from the UTXO set, and creates new UTXOs in its outputs.
4. **Gone** — Spent UTXOs are removed from the UTXO set and only exist in historical blockchain data.

### Why UTXO Management Matters

**Fees** — Each input you add to a transaction increases its byte count (and thus its fee). A wallet with 100 small UTXOs may pay 5-10x more in fees than one with 5 large UTXOs to send the same amount.

**Privacy** — When your wallet combines multiple UTXOs in one transaction, blockchain analysis firms can often infer that all those inputs belong to the same person. Careful coin control helps prevent this.

**Consolidation** — During periods of low fees, it is smart to "consolidate" many small UTXOs into fewer, larger ones. This reduces future fees and simplifies wallet management.

**Dust** — Very small UTXOs (under 546 satoshis for P2PKH) may be uneconomical to spend because the fee to spend them exceeds their value. These are called "dust" and can accumulate if you receive many small payments.

### Coin Control in Practice

Advanced wallets (like Sparrow Wallet) offer "coin control" — the ability to manually select which UTXOs to use as inputs. This is important for:

- Avoiding linking UTXOs from different sources (privacy)
- Choosing UTXOs that minimize fees
- Spending before a UTXO becomes dust

In Magma, your savings and DCA purchases each create new UTXOs in your self-custody wallet. Understanding UTXOs helps you plan your withdrawals efficiently.
""",
        "content_es": """
## Entendiendo los UTXOs

Bitcoin no usa un modelo de cuentas como un banco. No existe una entrada en el libro mayor que diga "Alicia tiene 1.5 BTC". En cambio, Bitcoin rastrea la propiedad mediante Salidas de Transacción No Gastadas (UTXOs) — trozos discretos de Bitcoin que solo pueden gastarse en su totalidad.

### ¿Qué es un UTXO?

Cuando recibes Bitcoin, se crea un nuevo UTXO — una cantidad específica bloqueada a un script de bloqueo (normalmente tu dirección). El "saldo de tu billetera" es en realidad la suma de todos los UTXOs que controlas a través de las claves privadas correspondientes.

Piensa en los UTXOs como monedas y billetes físicos. Si tienes una "moneda" de 50 sats y quieres pagar 30 sats, no puedes dividir la moneda. Entregas toda la moneda de 50 sats y recibes 20 sats de cambio. Bitcoin funciona igual.

### Por Qué Importa la Gestión de UTXOs

**Tarifas** — Cada entrada que añades a una transacción aumenta su tamaño en bytes (y por ende su tarifa). Una billetera con 100 UTXOs pequeños puede pagar 5-10 veces más en tarifas que una con 5 UTXOs grandes para enviar la misma cantidad.

**Privacidad** — Cuando tu billetera combina múltiples UTXOs en una transacción, las firmas de análisis blockchain a menudo pueden inferir que todas esas entradas pertenecen a la misma persona.

**Consolidación** — Durante períodos de tarifas bajas, es inteligente "consolidar" muchos UTXOs pequeños en unos pocos más grandes. Esto reduce las tarifas futuras y simplifica la gestión de la billetera.
""",
        "quiz": [
            {
                "question_en": "What is the 'UTXO set'?",
                "question_es": "¿Qué es el 'conjunto UTXO'?",
                "options": [
                    "A) The set of all Bitcoin wallets",
                    "B) The set of all unspent transaction outputs currently in existence",
                    "C) The set of all confirmed transactions",
                    "D) The set of all miners",
                ],
                "correct_index": 1,
                "explanation_en": "The UTXO set is the collection of all outputs that have been created but not yet spent, maintained by every full node to validate new transactions.",
                "explanation_es": "El conjunto UTXO es la colección de todas las salidas creadas pero aún no gastadas, mantenida por cada nodo completo para validar nuevas transacciones.",
            },
            {
                "question_en": "Why is it smart to consolidate small UTXOs during low-fee periods?",
                "question_es": "¿Por qué es inteligente consolidar UTXOs pequeños durante períodos de tarifas bajas?",
                "options": [
                    "A) To earn interest on your Bitcoin",
                    "B) To reduce the number of inputs in future transactions and save on fees",
                    "C) To improve your Bitcoin's privacy automatically",
                    "D) To increase your wallet's security",
                ],
                "correct_index": 1,
                "explanation_en": "Each input costs bytes in a transaction. Consolidating many small UTXOs into fewer large ones reduces the number of inputs needed in future transactions, lowering fees.",
                "explanation_es": "Cada entrada cuesta bytes en una transacción. Consolidar muchos UTXOs pequeños en unos pocos grandes reduce el número de entradas necesarias en transacciones futuras.",
            },
        ],
    },
    # =========================================================================
    # 4. Bitcoin Mining and Proof of Work
    # =========================================================================
    {
        "id": "mining-and-pow",
        "title_en": "Bitcoin Mining and Proof of Work",
        "title_es": "Minería Bitcoin y Prueba de Trabajo",
        "description_en": (
            "Understand how miners secure the network, how new Bitcoin is created, "
            "and why proof-of-work is essential to Bitcoin's security model."
        ),
        "description_es": (
            "Entiende cómo los mineros aseguran la red, cómo se crea el nuevo "
            "Bitcoin y por qué la prueba de trabajo es esencial para el modelo "
            "de seguridad de Bitcoin."
        ),
        "category": "mining",
        "difficulty": "intermediate",
        "duration_min": 14,
        "content_en": """
## Bitcoin Mining and Proof of Work

Bitcoin mining is often misunderstood as simply "creating Bitcoin." In reality, mining serves three critical functions: it validates transactions, secures the blockchain against rewrites, and issues new Bitcoin in a transparent, predictable schedule.

### What is Proof of Work?

Proof of Work (PoW) is the mechanism that makes Bitcoin mining a competitive lottery with a cost. To produce a valid block, a miner must find a number (the "nonce") such that when combined with the block header data and hashed with SHA-256 twice, the resulting 256-bit hash is numerically smaller than the current difficulty target.

This is computationally hard to do but trivially easy for anyone to verify. The average number of hashes required to find a valid nonce is enormous — today it exceeds a quintillion (10^18) hashes per block. But verification requires only a single SHA-256 computation.

### The Mining Process

1. **Collect transactions** — The miner selects transactions from their mempool, prioritizing by fee rate (sat/vB), to fill a block up to its weight limit (~4 million weight units).

2. **Build the block header** — The header contains: the previous block hash, the Merkle root of selected transactions, a timestamp, the current difficulty target, and a nonce field (32 bits).

3. **Hash repeatedly** — The miner increments the nonce and hashes the header with SHA-256 twice. If the result is below the difficulty target, the block is valid. Otherwise, try again.

4. **Broadcast the block** — The winning miner broadcasts the valid block to the network. Nodes verify it and add it to their blockchain.

5. **Earn the reward** — The miner includes a special "coinbase transaction" that creates new Bitcoin (the block subsidy) and collects all the transaction fees. This is the only mechanism by which new Bitcoin is ever created.

### Difficulty Adjustment

Bitcoin adjusts its mining difficulty every 2,016 blocks (approximately every two weeks). If the previous 2,016 blocks took less than 2 weeks on average, difficulty increases. If they took more than 2 weeks, difficulty decreases. This keeps the block time centered around 10 minutes regardless of how much mining hardware joins or leaves the network.

This elegantly self-regulating system means Bitcoin is not disrupted when large miners come online or go offline.

### Hash Rate and Network Security

The network's security is proportional to its total hash rate — the number of SHA-256 computations performed per second by all miners combined. A higher hash rate means an attacker needs more hardware and energy to attempt a 51% attack (controlling the majority of hash rate to rewrite recent blocks).

As of 2024, the Bitcoin network operates at hundreds of exahashes per second (EH/s). To attack it, you would need to acquire and operate more mining hardware than exists on Earth — a practically impossible feat.

### Bitcoin Mining in El Salvador

El Salvador operates geothermal Bitcoin mining using energy from its volcanoes. Because volcanic energy is cheap and would otherwise be wasted, this makes El Salvador's mining highly economical and one of the world's lowest-carbon mining operations. It is a demonstration of how Bitcoin mining can monetize otherwise stranded energy resources.

### Mining Economics

Miners face two income sources:
1. **Block subsidy** — Currently 3.125 BTC per block (after the April 2024 halving), declining with each halving.
2. **Transaction fees** — The sum of fees from all transactions in the block.

As the subsidy approaches zero (around 2140), the fee market must sustain miners. This is why a healthy Bitcoin fee economy is important for long-term security.
""",
        "content_es": """
## Minería Bitcoin y Prueba de Trabajo

La minería Bitcoin a menudo se malentiende como simplemente "crear Bitcoin". En realidad, la minería cumple tres funciones críticas: valida transacciones, asegura la blockchain contra reescrituras y emite nuevos Bitcoin en un calendario transparente y predecible.

### ¿Qué es la Prueba de Trabajo?

La Prueba de Trabajo (PoW) es el mecanismo que hace de la minería Bitcoin una lotería competitiva con un costo. Para producir un bloque válido, un minero debe encontrar un número (el "nonce") tal que, combinado con los datos de la cabecera del bloque y hasheado con SHA-256 dos veces, el hash resultante sea numéricamente menor que el objetivo de dificultad actual.

Esto es computacionalmente difícil de hacer pero trivialmente fácil de verificar para cualquiera.

### Ajuste de Dificultad

Bitcoin ajusta su dificultad de minería cada 2,016 bloques (aproximadamente cada dos semanas). Esto mantiene el tiempo de bloque centrado en 10 minutos independientemente de cuánto hardware de minería se una o abandone la red.

### Minería en El Salvador

El Salvador opera minería Bitcoin geotérmica usando energía de sus volcanes. Como la energía volcánica es barata y de otro modo se desperdiciaría, esto hace que la minería de El Salvador sea altamente económica y una de las operaciones de minería con menor huella de carbono del mundo.
""",
        "quiz": [
            {
                "question_en": "How often does Bitcoin adjust its mining difficulty?",
                "question_es": "¿Con qué frecuencia ajusta Bitcoin su dificultad de minería?",
                "options": [
                    "A) Every 1,000 blocks",
                    "B) Every 2,016 blocks (~2 weeks)",
                    "C) Every 210,000 blocks (~4 years)",
                    "D) Every day at midnight",
                ],
                "correct_index": 1,
                "explanation_en": "Bitcoin adjusts difficulty every 2,016 blocks (approximately 2 weeks) to keep the average block time at 10 minutes.",
                "explanation_es": "Bitcoin ajusta la dificultad cada 2,016 bloques (~2 semanas) para mantener el tiempo promedio de bloque en 10 minutos.",
            },
            {
                "question_en": "What is the ONLY way new Bitcoin is created?",
                "question_es": "¿Cuál es la ÚNICA forma en que se crea nuevo Bitcoin?",
                "options": [
                    "A) By the Bitcoin Foundation issuing new coins",
                    "B) By the coinbase transaction in a mined block",
                    "C) By converting satoshis on the Lightning Network",
                    "D) By running a Bitcoin node",
                ],
                "correct_index": 1,
                "explanation_en": "The coinbase transaction in each new block is the only mechanism that creates new Bitcoin. It includes the block subsidy and cannot exceed the protocol-defined amount.",
                "explanation_es": "La transacción coinbase en cada nuevo bloque es el único mecanismo que crea nuevo Bitcoin.",
            },
        ],
    },
    # =========================================================================
    # 5. The Lightning Network
    # =========================================================================
    {
        "id": "lightning-network",
        "title_en": "The Lightning Network",
        "title_es": "La Red Lightning",
        "description_en": (
            "Explore Bitcoin's layer-2 payment network: how payment channels work, "
            "how payments route, and why Lightning enables instant micropayments."
        ),
        "description_es": (
            "Explora la red de pago de capa 2 de Bitcoin: cómo funcionan los canales "
            "de pago, cómo se enrutan los pagos y por qué Lightning permite "
            "micropagos instantáneos."
        ),
        "category": "lightning",
        "difficulty": "intermediate",
        "duration_min": 15,
        "content_en": """
## The Lightning Network

The Lightning Network is a layer-2 protocol built on top of Bitcoin that enables instant, near-zero-fee payments. While Bitcoin's base layer prioritizes security and decentralization (at the cost of throughput), Lightning trades some decentralization for dramatically improved scalability.

### The Scaling Problem

Bitcoin processes approximately 7 transactions per second on its base layer (versus Visa's ~24,000). The block size and 10-minute block time are intentional design choices that keep the blockchain small enough for anyone to run a full node. But this limits throughput.

Lightning solves this by allowing most payments to happen off-chain, between parties who have established payment channels, with only the opening and closing transactions touching the blockchain.

### Payment Channels

A payment channel between Alice and Bob works like this:

1. **Open** — Alice and Bob create a 2-of-2 multisig transaction (the "funding transaction") that locks some Bitcoin on-chain. Both must sign to spend from it.

2. **Transact** — Alice and Bob exchange signed commitment transactions that redistribute the channel balance between them. These are valid Bitcoin transactions that could be broadcast but don't have to be — they stay off-chain.

3. **Close** — When either party wants to settle, the latest commitment transaction is broadcast to the blockchain. Each party receives their final balance on-chain.

Between open and close, the channel can handle an unlimited number of instant, fee-free transactions.

### Multi-Hop Payments

You don't need a direct channel with every person you want to pay. Lightning routes payments through intermediate nodes. If Alice has a channel with Bob, and Bob has a channel with Carol, Alice can pay Carol through Bob.

This works safely using Hash Time-Locked Contracts (HTLCs): Alice locks payment to Bob conditional on Bob proving he delivered it to Carol within a time window. If anything goes wrong, timeouts ensure funds return to their rightful owner.

### Invoices and Payments

To receive a Lightning payment, you generate an invoice — a payment request string (BOLT11 format) that encodes:
- The payment hash (a cryptographic commitment)
- The amount in millisatoshis
- The node's public key
- An expiry time

The payer decodes the invoice and Lightning Network routing finds the best path to deliver the payment.

### Lightning in El Salvador

The Lightning Network is central to Bitcoin's role in El Salvador. The Chivo wallet (government app) and many merchant integrations use Lightning for instant, near-zero-fee payments. Remittances via Lightning from the United States to El Salvador can arrive in seconds with fees of a fraction of a cent, compared to the 5-10% charged by legacy services like Western Union.

### Running a Lightning Node

Running your own Lightning node gives you:
- Full sovereignty over your Lightning payments
- The ability to earn routing fees (small amounts for forwarding payments)
- No custodial risk — you control your channel funds

Bitcoin and Lightning together provide a complete monetary stack: Bitcoin for savings and settlement, Lightning for everyday payments.
""",
        "content_es": """
## La Red Lightning

La Red Lightning es un protocolo de capa 2 construido sobre Bitcoin que permite pagos instantáneos y casi sin comisiones. Mientras que la capa base de Bitcoin prioriza la seguridad y la descentralización, Lightning sacrifica algo de descentralización por una escalabilidad dramáticamente mejorada.

### Canales de Pago

Un canal de pago entre Alicia y Bob funciona así:

1. **Abrir** — Alicia y Bob crean una transacción multisig 2-de-2 (la "transacción de financiamiento") que bloquea algo de Bitcoin en cadena.
2. **Transaccionar** — Alician y Bob intercambian transacciones de compromiso firmadas que redistribuyen el saldo del canal entre ellos. Estas permanecen fuera de la cadena.
3. **Cerrar** — Cuando cualquiera de las partes quiere liquidar, la última transacción de compromiso se difunde a la blockchain.

### Lightning en El Salvador

La Red Lightning es central para el papel de Bitcoin en El Salvador. Las remesas vía Lightning desde Estados Unidos a El Salvador pueden llegar en segundos con tarifas de una fracción de centavo, comparado con el 5-10% cobrado por servicios legacy como Western Union.
""",
        "quiz": [
            {
                "question_en": "What is the on-chain component that opens a Lightning payment channel?",
                "question_es": "¿Cuál es el componente en cadena que abre un canal de pago Lightning?",
                "options": [
                    "A) A Lightning invoice",
                    "B) A 2-of-2 multisig funding transaction",
                    "C) An OP_RETURN output",
                    "D) A coinbase transaction",
                ],
                "correct_index": 1,
                "explanation_en": "A Lightning channel is opened with a 2-of-2 multisig funding transaction on-chain. Both parties must sign to spend from it, ensuring neither can unilaterally steal funds.",
                "explanation_es": "Un canal Lightning se abre con una transacción de financiamiento multisig 2-de-2 en cadena.",
            },
            {
                "question_en": "How do multi-hop Lightning payments work safely?",
                "question_es": "¿Cómo funcionan de forma segura los pagos Lightning de múltiples saltos?",
                "options": [
                    "A) By trusting intermediate routing nodes",
                    "B) Using Hash Time-Locked Contracts (HTLCs) that ensure atomic delivery",
                    "C) By broadcasting each hop on-chain",
                    "D) By splitting the payment into smaller amounts",
                ],
                "correct_index": 1,
                "explanation_en": "HTLCs make multi-hop payments atomic — either the full payment completes along the route, or all funds are returned. No intermediate node can steal the payment.",
                "explanation_es": "Los HTLCs hacen que los pagos de múltiples saltos sean atómicos — o el pago completo se completa a lo largo de la ruta, o todos los fondos se devuelven.",
            },
        ],
    },
    # =========================================================================
    # 6. Saving in Bitcoin (DCA Strategy)
    # =========================================================================
    {
        "id": "saving-in-bitcoin",
        "title_en": "Saving in Bitcoin: The DCA Strategy",
        "title_es": "Ahorrar en Bitcoin: La Estrategia DCA",
        "description_en": (
            "Learn why many Bitcoiners use Dollar-Cost Averaging as their preferred "
            "savings strategy and how to implement it effectively."
        ),
        "description_es": (
            "Aprende por qué muchos Bitcoiners usan el Promedio del Costo en Dólares "
            "como su estrategia de ahorro preferida y cómo implementarla eficazmente."
        ),
        "category": "basics",
        "difficulty": "beginner",
        "duration_min": 10,
        "content_en": """
## Saving in Bitcoin: The DCA Strategy

Bitcoin's price is volatile in the short term but has appreciated significantly over every extended time horizon since its creation. Dollar-Cost Averaging (DCA) is an investment strategy designed to take advantage of this long-term trajectory while minimizing the risk of buying at a local peak.

### What is DCA?

Dollar-Cost Averaging means buying a fixed dollar amount of Bitcoin at regular intervals — weekly, bi-weekly, or monthly — regardless of the current price. When the price is high, your fixed amount buys fewer sats. When the price is low, it buys more sats. Over time, your average purchase price smooths out and is typically lower than the average price during the same period.

### Why DCA Works for Bitcoin

Bitcoin's price history shows extreme volatility — 70-80% drawdowns during bear markets — but also extraordinary long-term appreciation. The challenge is that timing the market consistently is practically impossible. DCA bypasses this problem entirely: instead of trying to buy at the perfect moment, you buy consistently over time.

**Key advantages:**
- Removes emotion from investment decisions
- Requires no market timing skill
- Builds a disciplined savings habit
- Reduces the impact of short-term volatility
- Can be automated for true "set and forget" savings

### Historical Performance

Bitcoin DCA has historically outperformed almost every other savings vehicle. A person who DCA'd $100 per week into Bitcoin for any 4-year period since 2012 would have positive returns. No 4-year DCA period in Bitcoin's history has been negative.

This is not a guarantee for the future — past performance does not guarantee future returns — but it reflects Bitcoin's consistent long-term growth driven by growing adoption, fixed supply, and increasing institutional recognition.

### DCA in Practice with Magma

Magma makes Bitcoin DCA simple for Salvadoran users. You can:

1. Set a recurring purchase amount (e.g., $25 per week)
2. Choose automatic conversion from USD savings
3. Track your accumulated sats and average purchase price
4. Withdraw to self-custody when your stack reaches a target size

The key principle: the sats you stack today are worth keeping. Even a small, consistent amount — 10,000 sats per week — adds up to over 520,000 sats in a year. At Bitcoin's historical growth rate, small daily or weekly savings can become meaningful wealth over a decade.

### Beyond DCA: The HODL Philosophy

DCA gets you into Bitcoin. HODLing keeps you in Bitcoin. The two strategies work together: you accumulate with DCA, then hold through volatility without panic-selling.

The Bitcoiner mentality is long-term oriented: Bitcoin is not a trading instrument but a savings technology — a way to preserve the value of your work across time, outside the reach of inflation and monetary debasement.
""",
        "content_es": """
## Ahorrar en Bitcoin: La Estrategia DCA

El precio de Bitcoin es volátil a corto plazo pero ha apreciado significativamente en cada horizonte temporal extendido desde su creación. El Promedio del Costo en Dólares (DCA) es una estrategia diseñada para aprovechar esta trayectoria a largo plazo mientras se minimiza el riesgo de comprar en un pico local.

### ¿Qué es el DCA?

El DCA significa comprar una cantidad fija en dólares de Bitcoin a intervalos regulares — semanal, quincenal o mensual — independientemente del precio actual. Cuando el precio es alto, tu cantidad fija compra menos sats. Cuando el precio es bajo, compra más sats.

### DCA con Magma

Magma hace que el DCA de Bitcoin sea simple para los usuarios salvadoreños. Puedes:

1. Establecer un monto de compra recurrente (p.ej., $25 por semana)
2. Elegir conversión automática desde ahorros en USD
3. Rastrear tus sats acumulados y precio promedio de compra
4. Retirar a autocustodia cuando tu stack alcance un objetivo

El principio clave: los sats que apilas hoy vale la pena mantener.
""",
        "quiz": [
            {
                "question_en": "What is the core mechanism of Dollar-Cost Averaging?",
                "question_es": "¿Cuál es el mecanismo central del Promedio del Costo en Dólares?",
                "options": [
                    "A) Buying Bitcoin only when the price drops 10%",
                    "B) Investing a fixed dollar amount at regular intervals regardless of price",
                    "C) Tracking the market and buying at the lowest point each month",
                    "D) Converting all your salary to Bitcoin at once",
                ],
                "correct_index": 1,
                "explanation_en": "DCA means buying a fixed dollar amount at regular intervals. This removes the need for market timing and smooths out the average purchase price over time.",
                "explanation_es": "DCA significa comprar una cantidad fija en dólares a intervalos regulares, eliminando la necesidad de timing del mercado.",
            },
            {
                "question_en": "What is the main advantage of DCA over lump-sum investing?",
                "question_es": "¿Cuál es la principal ventaja del DCA sobre la inversión de suma global?",
                "options": [
                    "A) DCA always guarantees higher returns",
                    "B) DCA reduces the impact of short-term price volatility on your average cost",
                    "C) DCA avoids all transaction fees",
                    "D) DCA is only for experts",
                ],
                "correct_index": 1,
                "explanation_en": "By spreading purchases over time, DCA ensures you don't buy your entire position at a potential market peak. Your average cost reflects prices across the full period.",
                "explanation_es": "Al distribuir las compras a lo largo del tiempo, el DCA garantiza que no compres toda tu posición en un posible pico del mercado.",
            },
        ],
    },
    # =========================================================================
    # 7. Understanding Bitcoin Fees
    # =========================================================================
    {
        "id": "understanding-fees",
        "title_en": "Understanding Bitcoin Fees",
        "title_es": "Entendiendo las Tarifas de Bitcoin",
        "description_en": (
            "Learn how Bitcoin transaction fees work, why they fluctuate, "
            "and strategies to minimize costs when sending Bitcoin."
        ),
        "description_es": (
            "Aprende cómo funcionan las tarifas de transacción Bitcoin, por qué "
            "fluctúan y estrategias para minimizar costos al enviar Bitcoin."
        ),
        "category": "transactions",
        "difficulty": "intermediate",
        "duration_min": 11,
        "content_en": """
## Understanding Bitcoin Fees

Bitcoin transaction fees are the price you pay to have your transaction included in a block. They are the market mechanism that allocates scarce block space among competing users.

### How Fees Work

Miners have limited block space (~4 million weight units per block). They fill this space with transactions from the mempool, typically selecting those with the highest fee rate (sat/vB) first.

Your transaction fee is calculated as: **Fee = Fee Rate × Transaction Size in vBytes**

A typical native SegWit (P2WPKH) transaction with 1 input and 2 outputs is about 141 vbytes. At a fee rate of 10 sat/vB, the fee would be 1,410 sats.

### Factors That Affect Fees

**Block space demand** — When many people want to transact simultaneously (during bull markets, ETF launches, or ordinals activity), the mempool fills up and users bid higher fees to get priority confirmation.

**Transaction size (vbytes)** — More inputs and outputs = larger transaction = higher fee. This is why UTXO consolidation during low-fee periods matters.

**Address type** — Native SegWit (bc1q) and Taproot (bc1p) addresses have significantly lower fees than legacy (1...) addresses because witness data has a 75% weight discount.

**Time sensitivity** — If you're not in a hurry, you can set a low fee rate and wait for a low-demand period. If you need confirmation in the next block, you pay the market rate for priority.

### Fee Estimation

Good wallets offer fee estimation based on current mempool conditions:
- **Next block (~10 min)**: High fee rate (priority)
- **~30 min**: Medium fee rate
- **~1-2 hours**: Low fee rate (economy)

Always check a mempool visualizer (like mempool.space) before sending large amounts.

### Fee Bumping

If your transaction is stuck in the mempool:

**RBF (Replace-By-Fee)** — If you enabled RBF when creating the transaction, you can broadcast a new version with a higher fee. Most modern wallets support this.

**CPFP (Child Pays for Parent)** — Create a new transaction spending one of the outputs from the stuck transaction, with a high enough fee that miners are incentivized to include both the parent and child together.

### Lightning vs On-chain Fees

Lightning Network payments have near-zero fees — typically 1-10 sats regardless of the payment amount. For small, frequent payments (remittances, purchases, tips), Lightning is dramatically more economical than on-chain transactions.

Use on-chain Bitcoin for:
- Large, infrequent transfers
- Cold storage movements
- Channel openings and closings

Use Lightning for:
- Daily spending
- Remittances
- Micropayments
- Point-of-sale payments
""",
        "content_es": """
## Entendiendo las Tarifas de Bitcoin

Las tarifas de transacción Bitcoin son el precio que pagas para que tu transacción sea incluida en un bloque. Son el mecanismo de mercado que asigna el escaso espacio de bloque entre usuarios competidores.

### Cómo Funcionan las Tarifas

Los mineros tienen espacio de bloque limitado (~4 millones de unidades de peso por bloque). Llenan este espacio con transacciones del mempool, típicamente seleccionando las que tienen la tasa de tarifa más alta (sat/vB) primero.

Tu tarifa de transacción se calcula como: **Tarifa = Tasa de Tarifa × Tamaño de la Transacción en vBytes**

### Lightning vs Tarifas en Cadena

Los pagos de la Red Lightning tienen tarifas casi nulas — típicamente 1-10 sats independientemente del monto del pago. Para pagos pequeños y frecuentes (remesas, compras, propinas), Lightning es dramáticamente más económico que las transacciones en cadena.
""",
        "quiz": [
            {
                "question_en": "What unit is used to express Bitcoin fee rates?",
                "question_es": "¿Qué unidad se usa para expresar las tasas de tarifa de Bitcoin?",
                "options": [
                    "A) Satoshis per transaction",
                    "B) Satoshis per virtual byte (sat/vB)",
                    "C) Dollars per kilobyte",
                    "D) Bits per second",
                ],
                "correct_index": 1,
                "explanation_en": "Fee rates are expressed in satoshis per virtual byte (sat/vB). The total fee equals the fee rate multiplied by the transaction's size in vbytes.",
                "explanation_es": "Las tasas de tarifa se expresan en satoshis por byte virtual (sat/vB). La tarifa total es igual a la tasa multiplicada por el tamaño de la transacción en vbytes.",
            },
            {
                "question_en": "Which technique lets a recipient speed up a stuck incoming transaction?",
                "question_es": "¿Qué técnica permite a un receptor acelerar una transacción entrante atascada?",
                "options": [
                    "A) RBF — Replace By Fee",
                    "B) CPFP — Child Pays for Parent",
                    "C) SegWit upgrade",
                    "D) Changing the fee rate after sending",
                ],
                "correct_index": 1,
                "explanation_en": "CPFP allows the recipient to create a high-fee 'child' transaction spending the unconfirmed output, incentivizing miners to include the 'parent' stuck transaction as well.",
                "explanation_es": "CPFP permite al receptor crear una transacción 'hijo' de alta tarifa que gasta la salida no confirmada, incentivando a los mineros a incluir también la transacción 'padre' atascada.",
            },
        ],
    },
    # =========================================================================
    # 8. SegWit and Transaction Optimization
    # =========================================================================
    {
        "id": "segwit-optimization",
        "title_en": "SegWit and Transaction Optimization",
        "title_es": "SegWit y Optimización de Transacciones",
        "description_en": (
            "Deep dive into the SegWit upgrade, how it reduces fees through the "
            "witness discount, and best practices for address selection."
        ),
        "description_es": (
            "Análisis profundo de la actualización SegWit, cómo reduce las tarifas "
            "mediante el descuento witness y las mejores prácticas para la "
            "selección de direcciones."
        ),
        "category": "transactions",
        "difficulty": "intermediate",
        "duration_min": 12,
        "content_en": """
## SegWit and Transaction Optimization

Segregated Witness (SegWit) is one of the most important protocol upgrades in Bitcoin's history. Activated in August 2017 via a soft fork, it simultaneously fixed transaction malleability, enabled the Lightning Network, and made transactions cheaper.

### The Witness Discount

SegWit restructures transaction serialization by separating signature data (the "witness") from the rest of the transaction. Crucially, witness data is given a 75% weight discount: it counts as 1 weight unit (WU) per byte instead of 4 WU.

A block can hold up to 4 million WU. Because signature data is the largest part of most transactions, moving it to the discounted witness section means more transactions fit per block without increasing the raw block size.

**Practical impact:**
- Legacy P2PKH: ~148 vbytes per input
- P2SH-wrapped SegWit (P2SH-P2WPKH): ~91 vbytes per input
- Native SegWit P2WPKH: ~68 vbytes per input
- Taproot P2TR: ~57 vbytes per input (key-path spend)

Switching from a legacy address to a native SegWit address can reduce your transaction fee by 30-60%.

### Address Types and Their Costs

| Format | Address Prefix | Single Input vbytes | Relative Cost |
|--------|---------------|---------------------|---------------|
| P2PKH (Legacy) | 1... | ~148 | 100% |
| P2SH-P2WPKH (Wrapped SegWit) | 3... | ~91 | 61% |
| P2WPKH (Native SegWit) | bc1q | ~68 | 46% |
| P2TR (Taproot) | bc1p | ~57 | 38% |

### How to Optimize Your Transactions

1. **Use native SegWit or Taproot addresses** — Every byte counts when fees are high. Never use legacy addresses if you can avoid it.

2. **Consolidate UTXOs during low-fee periods** — Each input adds ~68+ vbytes. Having 10 inputs instead of 2 multiplies your fee by ~5x.

3. **Batch transactions** — If sending Bitcoin to multiple recipients, combine them into one transaction. Adding a second output costs only ~31 vbytes, much cheaper than a second transaction.

4. **Set appropriate fee rates** — Use mempool.space to see current fee conditions. Don't overpay for non-urgent transactions.

5. **Enable RBF** — Always enable RBF on your transactions so you can bump the fee if the transaction gets stuck without creating a new one.

6. **Use Lightning for small amounts** — On-chain fees are fixed per transaction, not per satoshi. Sending 1,000 sats on-chain may cost 500+ sats in fees. Lightning handles this much better.

### Transaction Batching Example

Without batching: Sending to 5 recipients = 5 transactions × 141 vbytes = 705 vbytes total.
With batching: 1 transaction with 5 outputs = 1 input + 5 outputs + overhead ≈ 350 vbytes total.

Batching roughly halves the total fee when sending to multiple recipients simultaneously.
""",
        "content_es": """
## SegWit y Optimización de Transacciones

Segregated Witness (SegWit) es una de las actualizaciones de protocolo más importantes en la historia de Bitcoin. Activada en agosto de 2017 mediante un soft fork, simultáneamente solucionó la maleabilidad de transacciones, habilitó la Red Lightning e hizo las transacciones más baratas.

### El Descuento Witness

SegWit reestructura la serialización de transacciones separando los datos de firma (el "witness") del resto de la transacción. Crucialmente, los datos witness reciben un descuento del 75% en peso: cuentan como 1 unidad de peso (WU) por byte en lugar de 4 WU.

**Impacto práctico:**
- P2PKH Legacy: ~148 vbytes por entrada
- P2WPKH SegWit Nativo: ~68 vbytes por entrada
- P2TR Taproot: ~57 vbytes por entrada (gasto por ruta de clave)

Cambiar de una dirección legacy a una nativa SegWit puede reducir tu tarifa entre un 30-60%.
""",
        "quiz": [
            {
                "question_en": "What weight discount does SegWit give to witness data?",
                "question_es": "¿Qué descuento de peso da SegWit a los datos witness?",
                "options": [
                    "A) 25% discount (3 WU per byte instead of 4)",
                    "B) 50% discount (2 WU per byte instead of 4)",
                    "C) 75% discount (1 WU per byte instead of 4)",
                    "D) No discount",
                ],
                "correct_index": 2,
                "explanation_en": "Witness data counts as 1 weight unit per byte versus 4 WU for non-witness data — a 75% discount. This is why SegWit transactions are cheaper.",
                "explanation_es": "Los datos witness cuentan como 1 unidad de peso por byte versus 4 WU para datos no-witness — un descuento del 75%.",
            },
            {
                "question_en": "Which Bitcoin address format is the cheapest to spend from?",
                "question_es": "¿Qué formato de dirección Bitcoin es el más barato para gastar?",
                "options": [
                    "A) P2PKH (addresses starting with 1)",
                    "B) P2SH (addresses starting with 3)",
                    "C) P2WPKH (addresses starting with bc1q)",
                    "D) P2TR Taproot (addresses starting with bc1p)",
                ],
                "correct_index": 3,
                "explanation_en": "Taproot P2TR key-path spends are the most efficient, using only ~57 vbytes per input, beating even native SegWit P2WPKH at ~68 vbytes.",
                "explanation_es": "Los gastos de ruta de clave P2TR Taproot son los más eficientes, usando solo ~57 vbytes por entrada.",
            },
        ],
    },
    # =========================================================================
    # 9. Bitcoin Privacy Basics
    # =========================================================================
    {
        "id": "bitcoin-privacy",
        "title_en": "Bitcoin Privacy Basics",
        "title_es": "Conceptos Básicos de Privacidad en Bitcoin",
        "description_en": (
            "Understand Bitcoin's pseudonymous nature, common privacy threats, "
            "and practical techniques to improve your on-chain privacy."
        ),
        "description_es": (
            "Comprende la naturaleza seudónima de Bitcoin, las amenazas comunes "
            "a la privacidad y técnicas prácticas para mejorar tu privacidad en cadena."
        ),
        "category": "privacy",
        "difficulty": "intermediate",
        "duration_min": 13,
        "content_en": """
## Bitcoin Privacy Basics

Bitcoin is pseudonymous, not anonymous. Every transaction is permanently recorded on a public blockchain. While addresses don't directly reveal your identity, sophisticated blockchain analysis techniques can often link addresses to real-world identities — especially if you've ever used a KYC exchange.

### The Pseudonymity Misconception

Many beginners assume Bitcoin is anonymous. It is not. Consider:
- All transactions are permanently public and visible to anyone
- Blockchain analysis firms (like Chainalysis) specialize in tracing Bitcoin flows
- If you've ever used an exchange with identity verification (KYC), that exchange knows your addresses
- Address reuse makes it trivial to track your transaction history

This doesn't mean Bitcoin has no privacy — it means privacy requires intentional choices.

### Common Privacy Threats

**Address Reuse** — Using the same Bitcoin address for multiple transactions allows anyone to see your full payment history for that address. Always use a new address for each payment.

**Input Clustering** — When a transaction has multiple inputs, analysts typically assume they all belong to the same wallet. This "common input ownership heuristic" is a powerful de-anonymization tool.

**Change Output Detection** — When you send Bitcoin and get change back, analysts can often identify which output is the change (usually a round-number payment vs. odd-amount change).

**UTXO Merging** — Combining UTXOs from different sources (e.g., a KYC exchange withdrawal and a peer-to-peer purchase) in one transaction links those otherwise separate identities.

### Privacy-Improving Techniques

**Coin Control** — Manually select which UTXOs to spend. Never mix coins from different sources (e.g., KYC exchange + P2P purchase) in the same transaction.

**CoinJoin** — A technique where multiple users collaborate to combine their transactions into one, breaking the common-input-ownership heuristic. Whirlpool (Samourai), JoinMarket, and Wasabi Wallet implement CoinJoin.

**Lightning Payments** — Lightning payments are not recorded on the public blockchain. They offer significantly better privacy for everyday spending than on-chain transactions.

**Run your own node** — Using a third-party node means that node operator can see your IP address and the addresses you're querying. Your own node means your queries stay private.

**Fresh address for each receipt** — Every time you share an address for a payment, use a fresh, previously unused one. HD wallets generate these automatically.

### Bitcoin Privacy vs. True Anonymity

Bitcoin is not a privacy coin and was never designed to be. For maximum financial privacy, techniques like CoinJoin, Lightning, and careful UTXO management are necessary. Perfect anonymity is extremely difficult to achieve on Bitcoin — but reasonable operational privacy is achievable with discipline.

The goal is not perfect anonymity but rather financial sovereignty: the ability to transact without being subject to surveillance capitalism or arbitrary financial censorship.
""",
        "content_es": """
## Conceptos Básicos de Privacidad en Bitcoin

Bitcoin es seudónimo, no anónimo. Cada transacción queda permanentemente registrada en una blockchain pública. Aunque las direcciones no revelan directamente tu identidad, técnicas sofisticadas de análisis blockchain a menudo pueden vincular direcciones a identidades del mundo real.

### Amenazas Comunes a la Privacidad

**Reutilización de Direcciones** — Usar la misma dirección Bitcoin para múltiples transacciones permite a cualquiera ver tu historial completo de pagos. Siempre usa una nueva dirección para cada pago.

**Agrupamiento de Entradas** — Cuando una transacción tiene múltiples entradas, los analistas típicamente asumen que todas pertenecen a la misma billetera.

**Combinación de UTXOs** — Combinar UTXOs de diferentes fuentes en una transacción vincula esas identidades de otro modo separadas.

### Técnicas para Mejorar la Privacidad

**Control de Monedas** — Selecciona manualmente qué UTXOs gastar. Nunca mezcles monedas de diferentes fuentes.

**CoinJoin** — Una técnica donde múltiples usuarios colaboran para combinar sus transacciones en una, rompiendo la heurística de propiedad común de entradas.

**Pagos Lightning** — Los pagos Lightning no se registran en la blockchain pública y ofrecen significativamente mejor privacidad para el gasto diario.
""",
        "quiz": [
            {
                "question_en": "What is the 'common input ownership heuristic'?",
                "question_es": "¿Qué es la 'heurística de propiedad común de entradas'?",
                "options": [
                    "A) The rule that all Bitcoin nodes must share the same mempool",
                    "B) The blockchain analysis assumption that all inputs in a transaction belong to the same owner",
                    "C) The rule that miners must own the inputs they confirm",
                    "D) The requirement to verify identity before transacting",
                ],
                "correct_index": 1,
                "explanation_en": "Blockchain analysts assume all inputs in a transaction belong to the same wallet, allowing them to cluster addresses. CoinJoin is specifically designed to break this assumption.",
                "explanation_es": "Los analistas de blockchain asumen que todas las entradas en una transacción pertenecen a la misma billetera, permitiéndoles agrupar direcciones.",
            },
            {
                "question_en": "Which approach provides the best privacy for small everyday Bitcoin payments?",
                "question_es": "¿Qué enfoque proporciona la mejor privacidad para pagos cotidianos pequeños de Bitcoin?",
                "options": [
                    "A) On-chain P2PKH transactions with address reuse",
                    "B) Lightning Network payments",
                    "C) On-chain P2TR transactions",
                    "D) Exchange transfers",
                ],
                "correct_index": 1,
                "explanation_en": "Lightning Network payments are not recorded on the public blockchain and use onion routing, providing much better privacy than on-chain transactions for everyday payments.",
                "explanation_es": "Los pagos de Lightning no se registran en la blockchain pública y usan enrutamiento cebolla, proporcionando mucha mejor privacidad que las transacciones en cadena.",
            },
        ],
    },
    # =========================================================================
    # 10. Running a Bitcoin Node
    # =========================================================================
    {
        "id": "running-a-node",
        "title_en": "Running a Bitcoin Node",
        "title_es": "Ejecutar un Nodo Bitcoin",
        "description_en": (
            "Discover why running your own Bitcoin node is the highest expression "
            "of Bitcoin sovereignty and how to get started."
        ),
        "description_es": (
            "Descubre por qué ejecutar tu propio nodo Bitcoin es la mayor expresión "
            "de soberanía Bitcoin y cómo empezar."
        ),
        "category": "protocol",
        "difficulty": "intermediate",
        "duration_min": 11,
        "content_en": """
## Running a Bitcoin Node

"Don't trust, verify" is the core Bitcoin principle. Running your own full node is the ultimate expression of this principle — you independently verify every transaction and block without trusting anyone.

### What Does a Full Node Do?

A Bitcoin full node:
- Downloads the complete blockchain from the genesis block (over 500 GB)
- Independently validates every transaction against Bitcoin's consensus rules
- Relays valid transactions and blocks to other nodes
- Maintains the complete UTXO set in memory
- Enforces your version of the consensus rules — no block or transaction that violates these rules will be accepted

This matters because when you use someone else's node (like a public Electrum server), you trust that node to tell you the truth about your balance and the state of the network. With your own node, you verify it yourself.

### Economic Nodes and Consensus

The most important property of running a node is that it gives you a vote in the Bitcoin consensus. If a miner or a coalition tries to change Bitcoin's rules (block size, supply cap, etc.), nodes that enforce the old rules will reject their blocks.

This is why the maxim is: "One CPU, one vote" for mining, but "One node, one veto" for consensus. Miners produce blocks; nodes decide which blocks to accept.

### What You Need to Run a Node

**Hardware requirements (Bitcoin Core):**
- ~500 GB storage (full archival node) or ~10 GB (pruned node)
- 2+ GB RAM
- Broadband internet connection
- Any modern computer or a Raspberry Pi 4

**Software options:**
- **Bitcoin Core** — The reference implementation, the gold standard
- **Umbrel / Start9 / RaspiBlitz** — Node-in-a-box solutions for non-technical users

### Running Lightning Alongside Your Node

Most Bitcoiners who run a node also run a Lightning node. This gives them:
- Full control over their Lightning channel funds
- Ability to route payments and earn small fees
- No trust in a third-party Lightning service provider

Common Lightning implementations: LND, CLN (Core Lightning), Eclair.

### Privacy Benefits of Your Own Node

When you use a third-party node, that node operator can see:
- Your IP address
- All addresses you're monitoring
- All transactions you broadcast

Your own node eliminates this surveillance. Combined with Tor, your Bitcoin activity becomes very difficult to associate with your IP address.

### Practical Impact for Magma Users

Even if you use Magma as your interface, connecting Magma to your own Bitcoin and Lightning nodes provides the highest level of sovereignty. Your node enforces the rules, your keys hold the funds, and no third party can censor your transactions.
""",
        "content_es": """
## Ejecutar un Nodo Bitcoin

"No confíes, verifica" es el principio central de Bitcoin. Ejecutar tu propio nodo completo es la mayor expresión de este principio — verificas independientemente cada transacción y bloque sin confiar en nadie.

### ¿Qué Hace un Nodo Completo?

Un nodo completo Bitcoin:
- Descarga la blockchain completa desde el bloque génesis (más de 500 GB)
- Valida independientemente cada transacción contra las reglas de consenso
- Retransmite transacciones y bloques válidos a otros nodos
- Mantiene el conjunto UTXO completo en memoria
- Aplica tu versión de las reglas de consenso

### Nodos Económicos y Consenso

La propiedad más importante de ejecutar un nodo es que te da un voto en el consenso Bitcoin. "Un nodo, un veto" para el consenso. Los mineros producen bloques; los nodos deciden qué bloques aceptar.
""",
        "quiz": [
            {
                "question_en": "What is the primary purpose of running a Bitcoin full node?",
                "question_es": "¿Cuál es el propósito principal de ejecutar un nodo completo Bitcoin?",
                "options": [
                    "A) To earn Bitcoin mining rewards",
                    "B) To independently verify every transaction and block without trusting anyone",
                    "C) To get faster transaction confirmations",
                    "D) To access lower fee rates",
                ],
                "correct_index": 1,
                "explanation_en": "A full node independently validates all transactions and blocks against Bitcoin's consensus rules, embodying the 'don't trust, verify' principle.",
                "explanation_es": "Un nodo completo valida independientemente todas las transacciones y bloques contra las reglas de consenso de Bitcoin.",
            },
            {
                "question_en": "How much storage does a full archival Bitcoin node require (approximately)?",
                "question_es": "¿Cuánto almacenamiento requiere un nodo Bitcoin archival completo (aproximadamente)?",
                "options": [
                    "A) 1 GB", "B) 50 GB", "C) 500 GB", "D) 10 TB",
                ],
                "correct_index": 2,
                "explanation_en": "A full archival Bitcoin node requires approximately 500+ GB of storage to hold the complete blockchain history from the genesis block.",
                "explanation_es": "Un nodo Bitcoin archival completo requiere aproximadamente 500+ GB de almacenamiento.",
            },
        ],
    },
    # =========================================================================
    # 11. Understanding the Mempool
    # =========================================================================
    {
        "id": "understanding-mempool",
        "title_en": "Understanding the Mempool",
        "title_es": "Entendiendo el Mempool",
        "description_en": (
            "Learn how the Bitcoin mempool works, why it causes fee spikes, "
            "and how to use mempool data to time your transactions."
        ),
        "description_es": (
            "Aprende cómo funciona el mempool de Bitcoin, por qué causa picos "
            "de tarifas y cómo usar datos del mempool para sincronizar tus transacciones."
        ),
        "category": "transactions",
        "difficulty": "intermediate",
        "duration_min": 9,
        "content_en": """
## Understanding the Mempool

The mempool (memory pool) is the waiting room for Bitcoin transactions. Before a transaction is confirmed in a block, it sits in the mempool — a temporary, in-memory data structure maintained by every node.

### How the Mempool Works

When you broadcast a transaction, it propagates through the Bitcoin peer-to-peer network, and each node that receives it:
1. Validates the transaction (correct signatures, no double-spends, valid scripts)
2. Adds it to their local mempool if valid
3. Relays it to their peers

Note: Each node maintains its own independent mempool. There is no single "global mempool" — nodes can have slightly different contents based on what they've received and their own policies (e.g., minimum fee rate thresholds).

### Mempool as a Fee Market

The mempool is where fee competition happens. Miners look at the mempool and pick the highest-fee-rate transactions to include in their next block.

When demand for block space is low (few pending transactions), even 1 sat/vB transactions confirm quickly. When demand is high (during bull markets or special events), users must bid higher fee rates to get priority.

### Mempool Size and Fee Spikes

During congestion events (NFT/ordinal crazes, bull market FOMO, large exchange movements), the mempool can swell from a few MB to hundreds of MB of pending transactions. Fee rates spike from 1-5 sat/vB to 50-500+ sat/vB.

Practical implications:
- If you need to send urgently during congestion: pay the market rate
- If it's not urgent: set a low fee rate and wait for the mempool to clear
- Never send with 0-fee or very low fees during busy periods — your transaction may be stuck for days or dropped

### Mempool Tools

**mempool.space** — The gold standard mempool visualizer. Shows pending transactions by fee rate, estimated confirmation times, and historical fee charts. Essential for anyone who sends Bitcoin on-chain regularly.

**Wallet fee estimation** — Most good wallets integrate mempool data to suggest appropriate fee rates. Always verify against a real-time mempool viewer for large transactions.

### Mempool and RBF

If your transaction is stuck because you set too low a fee rate, and you enabled RBF (BIP125) when sending, you can broadcast a replacement transaction with a higher fee. Your wallet creates a new transaction that spends the same inputs with a higher fee rate, and the new version will propagate through the network and replace the stuck original in most mempools.
""",
        "content_es": """
## Entendiendo el Mempool

El mempool (pool de memoria) es la sala de espera para las transacciones Bitcoin. Antes de que una transacción se confirme en un bloque, espera en el mempool — una estructura de datos temporal en memoria mantenida por cada nodo.

### El Mempool como Mercado de Tarifas

El mempool es donde ocurre la competencia de tarifas. Los mineros miran el mempool y seleccionan las transacciones con la tasa de tarifa más alta para incluir en su siguiente bloque.

Cuando la demanda de espacio de bloque es baja, incluso transacciones de 1 sat/vB se confirman rápidamente. Cuando la demanda es alta, los usuarios deben pujar tarifas más altas para obtener prioridad.

### Herramientas del Mempool

**mempool.space** — El visualizador de mempool estándar de oro. Muestra transacciones pendientes por tasa de tarifa, tiempos de confirmación estimados y gráficos históricos de tarifas.
""",
        "quiz": [
            {
                "question_en": "What happens to Bitcoin transactions when the mempool is congested?",
                "question_es": "¿Qué le ocurre a las transacciones Bitcoin cuando el mempool está congestionado?",
                "options": [
                    "A) Transactions are automatically confirmed faster",
                    "B) Fee rates spike as users compete for limited block space",
                    "C) The block size automatically increases",
                    "D) Miners confirm all transactions for free",
                ],
                "correct_index": 1,
                "explanation_en": "When the mempool fills up with pending transactions, users must pay higher fee rates to get priority. Fee rates rise with demand for the fixed supply of block space.",
                "explanation_es": "Cuando el mempool se llena de transacciones pendientes, los usuarios deben pagar tarifas más altas para obtener prioridad.",
            },
            {
                "question_en": "Is there a single global Bitcoin mempool?",
                "question_es": "¿Existe un mempool Bitcoin global único?",
                "options": [
                    "A) Yes, maintained by the Bitcoin Foundation",
                    "B) Yes, maintained by the largest mining pools",
                    "C) No — each node maintains its own independent mempool",
                    "D) Yes, stored on a dedicated mempool server",
                ],
                "correct_index": 2,
                "explanation_en": "Each Bitcoin node maintains its own independent mempool. There is no single global mempool — nodes can have slightly different contents based on their policies and what transactions they've received.",
                "explanation_es": "Cada nodo Bitcoin mantiene su propio mempool independiente. No existe un mempool global único.",
            },
        ],
    },
    # =========================================================================
    # 12. Bitcoin Halvings and Supply
    # =========================================================================
    {
        "id": "halvings-and-supply",
        "title_en": "Bitcoin Halvings and Supply",
        "title_es": "Halvings de Bitcoin y Suministro",
        "description_en": (
            "Explore Bitcoin's fixed supply schedule, how halvings affect miners "
            "and price, and why Bitcoin's monetary policy is unique."
        ),
        "description_es": (
            "Explora el programa de suministro fijo de Bitcoin, cómo los halvings "
            "afectan a los mineros y al precio, y por qué la política monetaria "
            "de Bitcoin es única."
        ),
        "category": "mining",
        "difficulty": "beginner",
        "duration_min": 10,
        "content_en": """
## Bitcoin Halvings and Supply

Bitcoin's monetary policy is determined by code, not by committees. Unlike central banks that adjust money supply based on economic conditions, Bitcoin follows a fixed, predetermined schedule that anyone can verify.

### The 21 Million Cap

Bitcoin's protocol enforces a hard cap of 21 million BTC. This limit is encoded into the consensus rules and enforced by every full node. No miner, developer, or government can create more Bitcoin than the protocol allows.

As of 2024, approximately 19.7 million BTC have been mined. The remaining 1.3 million will be issued gradually through the block subsidy over the next ~116 years.

### The Halving Schedule

Every 210,000 blocks (approximately 4 years), the block subsidy — the amount of new Bitcoin created per block — is cut in half:

| Halving | Approx. Year | Block Subsidy |
|---------|-------------|---------------|
| 0 (Genesis) | 2009 | 50 BTC |
| 1st | 2012 | 25 BTC |
| 2nd | 2016 | 12.5 BTC |
| 3rd | 2020 | 6.25 BTC |
| 4th | 2024 | 3.125 BTC |
| 5th | ~2028 | 1.5625 BTC |
| ... | ... | ... |
| ~33rd | ~2140 | ~0 BTC (last satoshi) |

### Why Halvings Matter

**For miners** — Each halving cuts their block reward in half, reducing revenue. Miners who are inefficient may become unprofitable and shut down. This causes a temporary drop in hash rate, which the difficulty adjustment corrects within two weeks.

**For supply** — Each halving reduces the rate at which new Bitcoin enters circulation. Bitcoin's annual inflation rate was ~50% in 2009, ~4% before the 2020 halving, ~1.7% before the 2024 halving, and will continue declining toward zero.

**For markets** — Historically, Bitcoin halvings have preceded major bull markets. The reduction in new supply, combined with steady or growing demand, exerts upward price pressure over time. This is not guaranteed, but the pattern has been consistent.

### Stock-to-Flow

Bitcoin's "stock-to-flow" ratio measures the existing supply (stock) divided by annual new production (flow). After the 2024 halving, Bitcoin's stock-to-flow ratio (~120) exceeds gold's (~60), making Bitcoin the scarcest monetary asset ever created by this measure.

### The End of Subsidies (~2140)

Eventually, the block subsidy will reach zero. At that point, miners must be sustained entirely by transaction fees. This is why a healthy Bitcoin fee market matters for long-term security. If fees are insufficient to sustain mining, Bitcoin's security would degrade.

Most Bitcoin economists believe that as adoption grows, higher transaction volumes and more sophisticated fee markets (with Layer-2 channels opening and closing on-chain) will provide adequate fee income for miners.
""",
        "content_es": """
## Halvings de Bitcoin y Suministro

La política monetaria de Bitcoin está determinada por código, no por comités. A diferencia de los bancos centrales que ajustan la oferta monetaria según las condiciones económicas, Bitcoin sigue un programa fijo y predeterminado que cualquiera puede verificar.

### El Límite de 21 Millones

El protocolo de Bitcoin aplica un límite máximo de 21 millones de BTC. Este límite está codificado en las reglas de consenso y aplicado por cada nodo completo. Ningún minero, desarrollador o gobierno puede crear más Bitcoin del que permite el protocolo.

### El Programa de Halving

Cada 210,000 bloques (~4 años), el subsidio de bloque se reduce a la mitad. Históricamente, los halvings de Bitcoin han precedido a importantes mercados alcistas. La reducción en el nuevo suministro, combinada con una demanda estable o creciente, ejerce presión alcista sobre el precio.
""",
        "quiz": [
            {
                "question_en": "What is the maximum number of Bitcoin that will ever exist?",
                "question_es": "¿Cuál es el número máximo de Bitcoin que existirá?",
                "options": [
                    "A) 100 million",
                    "B) 21 billion",
                    "C) 21 million",
                    "D) Unlimited",
                ],
                "correct_index": 2,
                "explanation_en": "Bitcoin's protocol enforces a hard cap of exactly 21 million BTC, encoded into consensus rules and enforced by every full node.",
                "explanation_es": "El protocolo de Bitcoin aplica un límite máximo de exactamente 21 millones de BTC.",
            },
            {
                "question_en": "What was Bitcoin's block subsidy after the April 2024 halving?",
                "question_es": "¿Cuál fue el subsidio de bloque de Bitcoin tras el halving de abril de 2024?",
                "options": [
                    "A) 6.25 BTC",
                    "B) 3.125 BTC",
                    "C) 1.5625 BTC",
                    "D) 12.5 BTC",
                ],
                "correct_index": 1,
                "explanation_en": "The April 2024 halving reduced the block subsidy from 6.25 BTC to 3.125 BTC per block.",
                "explanation_es": "El halving de abril de 2024 redujo el subsidio de bloque de 6.25 BTC a 3.125 BTC por bloque.",
            },
        ],
    },
    # =========================================================================
    # 13. Taproot and Schnorr Signatures
    # =========================================================================
    {
        "id": "taproot-schnorr",
        "title_en": "Taproot and Schnorr Signatures",
        "title_es": "Taproot y Firmas Schnorr",
        "description_en": (
            "Explore Bitcoin's most significant protocol upgrade since SegWit "
            "and how Taproot improves privacy, efficiency, and smart contracts."
        ),
        "description_es": (
            "Explora la actualización de protocolo más significativa de Bitcoin "
            "desde SegWit y cómo Taproot mejora la privacidad, eficiencia y "
            "contratos inteligentes."
        ),
        "category": "protocol",
        "difficulty": "advanced",
        "duration_min": 14,
        "content_en": """
## Taproot and Schnorr Signatures

Taproot, activated on November 14, 2021, at block 709,632, is the most significant Bitcoin protocol upgrade since SegWit. It introduces Schnorr signatures, MAST (Merklized Alternative Script Trees), and Tapscript — together providing better privacy, lower fees for complex scripts, and a foundation for future Bitcoin innovation.

### Why Taproot Was Needed

Bitcoin's original script system (ECDSA + pay-to-script-hash) had limitations:
- Complex scripts (multisig, timelocks, etc.) revealed their full complexity on-chain when spent
- ECDSA lacked key aggregation — multiple-party signatures required multiple signatures
- Every script path had to be revealed, even unused ones
- Complex scripts were larger and more expensive

Taproot addresses all of these problems.

### Schnorr Signatures (BIP340)

Schnorr is the digital signature algorithm that underpins Taproot. Key advantages over ECDSA:

**Linear key aggregation** — Multiple parties can aggregate their public keys into a single combined key. A 3-of-3 multisig can look exactly like a single-key spend on-chain, thanks to MuSig2 key aggregation.

**Batch verification** — Schnorr signatures from many transactions in a block can be verified simultaneously, which speeds up initial block download and block validation.

**Provable security** — Schnorr's security proof is simpler and more direct than ECDSA's.

**Smaller signatures** — A Schnorr signature is exactly 64 bytes, vs. the variable length (71-72 bytes typical) of a DER-encoded ECDSA signature.

### MAST: Merklized Alternative Script Trees (BIP341)

MAST allows a Bitcoin output to have many possible spending conditions (scripts), where only the condition actually used must be revealed on-chain. The other conditions are hidden in a Merkle tree.

Example: A custody setup where coins can be spent by:
- (1) The owner alone after 6 months
- (2) The owner + one of two trustees immediately
- (3) Both trustees after 1 year if the owner is unreachable

With MAST, if the owner uses path (1), conditions (2) and (3) are never revealed on-chain. Privacy is dramatically improved, and unused script paths don't add to transaction size.

### Key-Path and Script-Path Spends

Taproot outputs can be spent in two ways:

**Key-path** — A simple Schnorr signature from the "tweaked" public key (which has the Merkle root of all script options embedded in it). This looks identical to any other Schnorr signature — maximum privacy.

**Script-path** — Reveal one of the Merkle leaf scripts and satisfy its conditions. This exposes that the output was Taproot and which script was used, but still hides the other options.

### Impact on Privacy

When a Taproot multisig is spent via the key path (all parties cooperate), it is indistinguishable on-chain from a single-key spend. This is a massive privacy improvement: cooperative transactions — which are the vast majority — reveal no information about the spending policy.

### Tapscript (BIP342)

Tapscript updates the Bitcoin Script language with Schnorr compatibility and lays the groundwork for future script improvements through script versioning.

### Taproot and Lightning

Taproot is being integrated into Lightning to improve channel privacy (Taproot channel funding outputs look like regular key-path spends) and enable more complex channel types like Point Time-Locked Contracts (PTLCs), which improve payment privacy over the current HTLC system.
""",
        "content_es": """
## Taproot y Firmas Schnorr

Taproot, activado el 14 de noviembre de 2021, es la actualización de protocolo Bitcoin más significativa desde SegWit. Introduce firmas Schnorr, MAST (Árboles de Script Alternativos Merkleizados) y Tapscript.

### Firmas Schnorr (BIP340)

Schnorr es el algoritmo de firma digital que sustenta Taproot. Ventajas clave sobre ECDSA:

**Agregación lineal de claves** — Múltiples partes pueden agregar sus claves públicas en una sola clave combinada. Un multisig 3-de-3 puede verse exactamente como un gasto de clave única en cadena.

**Verificación por lotes** — Las firmas Schnorr de muchas transacciones en un bloque pueden verificarse simultáneamente.

### Impacto en la Privacidad

Cuando un multisig Taproot se gasta mediante la ruta de clave (todas las partes cooperan), es indistinguible en cadena de un gasto de clave única. Esta es una mejora masiva de privacidad.
""",
        "quiz": [
            {
                "question_en": "What makes Taproot key-path spends private?",
                "question_es": "¿Qué hace privados los gastos de ruta de clave de Taproot?",
                "options": [
                    "A) They are encrypted with AES-256",
                    "B) They look identical to single-key spends on-chain, hiding any complex spending policy",
                    "C) They are not recorded on the blockchain",
                    "D) They require a zero-knowledge proof",
                ],
                "correct_index": 1,
                "explanation_en": "Taproot key-path spends produce a standard Schnorr signature that is indistinguishable from any other key-path spend, hiding whether it's a multisig, a timelocked output, or a simple single-key spend.",
                "explanation_es": "Los gastos de ruta de clave Taproot producen una firma Schnorr estándar indistinguible de cualquier otro gasto de ruta de clave.",
            },
            {
                "question_en": "What is MuSig2 used for?",
                "question_es": "¿Para qué se usa MuSig2?",
                "options": [
                    "A) A second-layer payment channel protocol",
                    "B) Schnorr key aggregation for n-of-n multisig that produces a single signature",
                    "C) A new Bitcoin address format",
                    "D) A fee estimation algorithm",
                ],
                "correct_index": 1,
                "explanation_en": "MuSig2 is a Schnorr-based key aggregation protocol that allows n parties to collaborate to produce a single, compact aggregated signature for n-of-n multisig.",
                "explanation_es": "MuSig2 es un protocolo de agregación de claves basado en Schnorr que permite a n partes colaborar para producir una firma agregada única.",
            },
        ],
    },
    # =========================================================================
    # 14. Multisig Wallets
    # =========================================================================
    {
        "id": "multisig-wallets",
        "title_en": "Multisig Wallets",
        "title_es": "Billeteras Multifirma",
        "description_en": (
            "Learn how multi-signature wallets eliminate single points of failure "
            "and are used for personal savings, collaborative custody, and "
            "corporate treasury management."
        ),
        "description_es": (
            "Aprende cómo las billeteras multifirma eliminan puntos únicos de fallo "
            "y se usan para ahorros personales, custodia colaborativa y gestión "
            "de tesorería corporativa."
        ),
        "category": "security",
        "difficulty": "intermediate",
        "duration_min": 12,
        "content_en": """
## Multisig Wallets

A multi-signature (multisig) wallet requires multiple private keys to authorize a transaction. Instead of one key controlling all funds, you define a policy like "2-of-3" (any 2 of 3 keys can sign) or "3-of-5" (any 3 of 5 keys can sign).

### Why Multisig Matters

Single-key wallets have a single point of failure: if your private key or seed phrase is lost, stolen, or destroyed, your Bitcoin is gone forever. Multisig distributes this risk:

- **Loss protection** — If you lose one key, your other keys can still access the funds (e.g., in a 2-of-3, losing one key still leaves you with 2 of 3, sufficient to spend)
- **Theft protection** — An attacker must steal M keys (not just 1) to steal your Bitcoin
- **Coercion protection** — If someone forces you to sign at gunpoint, you can sign with one key while secretly alerting a trustee to block with their key

### Common Multisig Configurations

**2-of-2** — Both parties must sign. Used for Lightning channels. Risk: if either party loses their key, funds are stuck forever.

**2-of-3** — The most popular personal savings setup. Three keys stored in different locations; any two can spend. One key can be lost without losing access.

**3-of-5** — Corporate or institutional use cases. Higher resilience, but more complexity. Common for exchange cold storage.

**1-of-2** — Emergency access only. One of two designated parties can spend. Useful for inheritance.

### Implementation Options

**P2SH multisig** — The legacy implementation (addresses start with '3'). The script reveals all public keys when spent. Functional but not ideal for privacy.

**P2WSH multisig** — Native SegWit multisig. Cheaper than P2SH. Public keys revealed when spent.

**Taproot + MuSig2** — The most advanced option. N-of-N multisig looks like a single-key spend on-chain (private). Any-threshold policies can be structured as MAST leaves.

### Multisig for Personal Savings

A popular setup for long-term Bitcoin savings:
1. Key 1: Hardware wallet (Coldcard) at home
2. Key 2: Hardware wallet (Trezor) at work or safety deposit box
3. Key 3: Encrypted seed backup at a trusted family member's location

Coordination software like Sparrow Wallet, Specter, or Unchained makes creating and spending from multisig wallets accessible to non-technical users.

### Collaborative Custody Services

Services like Unchained and Casa offer "2-of-3 collaborative custody":
- Key 1: User's hardware wallet
- Key 2: Service's key (co-signer)
- Key 3: Backup key (user or family)

The service can help with signing if you lose a key, but cannot steal your funds alone (they only have 1 of 3 keys). This bridges the gap between full self-custody and full custodial solutions.

### Multisig and Lightning

The Lightning Network relies on multisig: every channel is a 2-of-2 multisig output. This ensures neither party can unilaterally steal funds — they must cooperate (or broadcast the latest commitment transaction) to close the channel.
""",
        "content_es": """
## Billeteras Multifirma

Una billetera multifirma requiere múltiples claves privadas para autorizar una transacción. En lugar de una clave que controle todos los fondos, defines una política como "2-de-3" (cualquier 2 de 3 claves pueden firmar).

### Por Qué Importa el Multifirma

Las billeteras de clave única tienen un único punto de fallo: si tu clave privada o frase semilla se pierde, roba o destruye, tu Bitcoin se pierde para siempre. El multifirma distribuye este riesgo:

- **Protección contra pérdida** — Si pierdes una clave, tus otras claves aún pueden acceder a los fondos
- **Protección contra robo** — Un atacante debe robar M claves (no solo 1) para robar tu Bitcoin
- **Protección contra coacción** — Si alguien te obliga a firmar, puedes firmar con una clave mientras alertas secretamente a un fideicomisario

### Servicios de Custodia Colaborativa

Servicios como Unchained y Casa ofrecen "custodia colaborativa 2-de-3": el servicio puede ayudar con la firma si pierdes una clave, pero no puede robar tus fondos solo (solo tienen 1 de 3 claves).
""",
        "quiz": [
            {
                "question_en": "In a 2-of-3 multisig wallet, how many keys must be available to spend?",
                "question_es": "En una billetera multifirma 2-de-3, ¿cuántas claves deben estar disponibles para gastar?",
                "options": ["A) 1", "B) 2", "C) 3", "D) All 3"],
                "correct_index": 1,
                "explanation_en": "A 2-of-3 multisig requires any 2 of the 3 keys to sign. This means you can lose 1 key and still access your funds, while an attacker must steal 2 keys.",
                "explanation_es": "Un multifirma 2-de-3 requiere cualquier 2 de las 3 claves para firmar. Puedes perder 1 clave y aún acceder a tus fondos.",
            },
            {
                "question_en": "Why is Taproot+MuSig2 the most private multisig option?",
                "question_es": "¿Por qué Taproot+MuSig2 es la opción multifirma más privada?",
                "options": [
                    "A) It encrypts the transaction with AES",
                    "B) N-of-N multisig spends look identical to single-key spends on-chain",
                    "C) It uses zero-knowledge proofs",
                    "D) It avoids the blockchain entirely",
                ],
                "correct_index": 1,
                "explanation_en": "With MuSig2 key aggregation under Taproot, an n-of-n multisig spending via the key path produces a single Schnorr signature indistinguishable from a regular single-key spend.",
                "explanation_es": "Con la agregación de claves MuSig2 bajo Taproot, un multifirma n-de-n que gasta a través de la ruta de clave produce una firma Schnorr única indistinguible de un gasto de clave única.",
            },
        ],
    },
    # =========================================================================
    # 15. Bitcoin and Remittances in El Salvador
    # =========================================================================
    {
        "id": "bitcoin-remittances-el-salvador",
        "title_en": "Bitcoin and Remittances in El Salvador",
        "title_es": "Bitcoin y Remesas en El Salvador",
        "description_en": (
            "Explore how Bitcoin and the Lightning Network are transforming "
            "remittances in El Salvador and what this means for financial "
            "inclusion in the developing world."
        ),
        "description_es": (
            "Explora cómo Bitcoin y la Red Lightning están transformando las "
            "remesas en El Salvador y qué significa esto para la inclusión "
            "financiera en el mundo en desarrollo."
        ),
        "category": "basics",
        "difficulty": "beginner",
        "duration_min": 11,
        "content_en": """
## Bitcoin and Remittances in El Salvador

El Salvador's decision to adopt Bitcoin as legal tender in September 2021 made it the first country in the world to do so. The context is crucial: El Salvador is a country where traditional finance has failed large portions of the population, and where Bitcoin offers a concrete, practical improvement to people's daily financial lives.

### The Remittance Problem

Remittances — money sent home by Salvadorans working abroad — are a cornerstone of El Salvador's economy. In 2022, remittances totaled over $7.5 billion, representing approximately 24% of the country's GDP. The vast majority comes from Salvadorans living in the United States.

The problem: traditional remittance services are expensive and slow.

**Traditional remittance costs:**
- Western Union: 4-8% fee for a $300 transfer
- MoneyGram: Similar fees
- Wire transfers: 3-5% plus 1-3 days delay
- Bank transfers (if banked): 3-5% and require a bank account

For a family receiving $500/month in remittances, traditional fees cost $20-40/month — money that could instead feed a family.

### Bitcoin Lightning as the Solution

Bitcoin's Lightning Network can send any amount internationally within seconds for a fraction of a cent:

**Lightning remittance example:**
- Sender in Dallas: Pays $300 equivalent in BTC via Lightning
- Fee: ~1-2 sats (<$0.01)
- Arrival time: <5 seconds
- Recipient in San Salvador: Receives sats, can spend at Lightning-enabled merchants or convert to dollars

Total cost: less than 1 cent. Savings vs. traditional: $15-24 per $300 transfer.

### Real-World Implementation

**Bitcoin Beach (El Zonte)** — Before El Salvador's Bitcoin Law, the coastal town of El Zonte (nicknamed "Bitcoin Beach") pioneered a circular Bitcoin economy, where residents earned, saved, and spent Bitcoin. The project demonstrated that Bitcoin worked practically for real people in developing communities.

**Chivo Wallet** — The government-issued digital wallet for El Salvador, supporting both Bitcoin and Lightning payments. Despite early technical issues and some political controversy, it demonstrated mass-scale Lightning deployment.

**Strike** — A Lightning-native payment app that allows Salvadorans in the US to send dollar amounts to El Salvador instantly via Lightning, with the recipient able to receive in dollars or Bitcoin.

### The Unbanked Problem

Approximately 70% of El Salvador's population was unbanked before Bitcoin adoption. Traditional banking requires:
- A physical address
- Income documentation
- Credit history
- Minimum balance requirements

Bitcoin requires only a smartphone and internet access. This has brought financial services to communities that traditional banks have never served.

### Volcanic Bitcoin Mining

El Salvador's Bitcoin story is not just about payments. The country is also using geothermal energy from its volcanoes (including the Izalco, San Miguel, and Ahuachapán geothermal plants) to mine Bitcoin. This creates:

- Zero-carbon Bitcoin mining
- Revenue for the Salvadoran state
- A demonstration that Bitcoin mining can be sustainable when powered by renewable energy

### Challenges and Lessons

Bitcoin adoption in El Salvador has not been without challenges:
- **Price volatility** — Families receiving remittances need stability; they must convert to dollars quickly
- **Technical complexity** — Seed phrases and Lightning channels are confusing for non-technical users
- **Infrastructure** — Reliable internet access is not universal

These are real challenges, but they are engineering problems that improve over time. The Lightning Network gets faster, simpler, and more reliable with every iteration. Wallet software becomes more user-friendly. And the fundamental advantage — dramatically lower remittance costs — remains.

### What This Means Globally

El Salvador's experiment is a proof of concept for billions of people in developing economies who:
- Pay high remittance fees
- Lack bank accounts
- Live in countries with inflationary currencies
- Need access to global commerce

Bitcoin, and especially the Lightning Network, offers a permissionless monetary infrastructure that anyone with a smartphone can access. El Salvador is the first chapter of a global story.
""",
        "content_es": """
## Bitcoin y Remesas en El Salvador

La decisión de El Salvador de adoptar Bitcoin como moneda de curso legal en septiembre de 2021 lo convirtió en el primer país del mundo en hacerlo. El contexto es crucial: El Salvador es un país donde las finanzas tradicionales han fallado a grandes porciones de la población.

### El Problema de las Remesas

Las remesas — dinero enviado a casa por salvadoreños trabajando en el exterior — son una piedra angular de la economía de El Salvador. En 2022, las remesas totalizaron más de $7.5 mil millones, representando aproximadamente el 24% del PIB del país.

**Costos de remesas tradicionales:**
- Western Union: comisión del 4-8% para una transferencia de $300
- Transferencias bancarias: 3-5% y 1-3 días de retraso

**Con Lightning:**
- Tarifa: ~1-2 sats (<$0.01)
- Tiempo de llegada: <5 segundos
- Ahorro: $15-24 por cada $300 transferido

### Minería Bitcoin con Energía Volcánica

El Salvador también usa energía geotérmica de sus volcanes para minar Bitcoin. Esto crea minería Bitcoin con cero carbono y demuestra que la minería de Bitcoin puede ser sostenible cuando se alimenta de energía renovable.
""",
        "quiz": [
            {
                "question_en": "Approximately what percentage of El Salvador's GDP came from remittances in 2022?",
                "question_es": "Aproximadamente, ¿qué porcentaje del PIB de El Salvador provino de remesas en 2022?",
                "options": ["A) 5%", "B) 24%", "C) 50%", "D) 70%"],
                "correct_index": 1,
                "explanation_en": "In 2022, remittances totaled over $7.5 billion, representing approximately 24% of El Salvador's GDP — making them crucial to the country's economy.",
                "explanation_es": "En 2022, las remesas totalizaron más de $7.5 mil millones, representando aproximadamente el 24% del PIB de El Salvador.",
            },
            {
                "question_en": "What is Bitcoin Beach (El Zonte)?",
                "question_es": "¿Qué es Bitcoin Beach (El Zonte)?",
                "options": [
                    "A) An exchange based in El Salvador",
                    "B) A coastal town that pioneered a circular Bitcoin economy before the Bitcoin Law",
                    "C) El Salvador's government Bitcoin wallet",
                    "D) A Bitcoin mining facility powered by ocean waves",
                ],
                "correct_index": 1,
                "explanation_en": "El Zonte (Bitcoin Beach) was a small coastal town in El Salvador that pioneered a circular Bitcoin economy where residents earned, saved, and spent Bitcoin — demonstrating real-world feasibility before the national Bitcoin Law.",
                "explanation_es": "El Zonte (Bitcoin Beach) fue una pequeña ciudad costera en El Salvador que fue pionera en una economía circular de Bitcoin donde los residentes ganaban, ahorraban y gastaban Bitcoin.",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_lesson(lesson_id: str) -> dict | None:
    """Retrieve a single lesson by its ID.

    Parameters
    ----------
    lesson_id : str  — the ``id`` field of the desired lesson.

    Returns
    -------
    The lesson dict, or ``None`` if not found.
    """
    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def list_lessons(
    category: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    """Return a filtered list of lessons (summary fields only).

    Filtering is optional — omit both arguments to get all lessons.

    Parameters
    ----------
    category   : Optional category filter (e.g., "basics", "lightning").
    difficulty : Optional difficulty filter ("beginner" | "intermediate" | "advanced").

    Returns
    -------
    List of lesson summary dicts (id, title_en, title_es, description_en,
    description_es, category, difficulty, duration_min).
    """
    results = []
    for lesson in LESSONS:
        if category and lesson.get("category") != category:
            continue
        if difficulty and lesson.get("difficulty") != difficulty:
            continue
        results.append(
            {
                "id": lesson["id"],
                "title_en": lesson["title_en"],
                "title_es": lesson["title_es"],
                "description_en": lesson["description_en"],
                "description_es": lesson["description_es"],
                "category": lesson["category"],
                "difficulty": lesson["difficulty"],
                "duration_min": lesson["duration_min"],
                "quiz_count": len(lesson.get("quiz", [])),
            }
        )
    return results
