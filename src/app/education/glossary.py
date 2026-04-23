"""Bitcoin glossary — bilingual (English / Spanish) reference dictionary.

Each entry in ``GLOSSARY`` is keyed by a canonical snake_case identifier
and contains structured metadata so the front-end can render rich
definition cards, filter by topic, or drive a quiz flow.

Schema per entry
----------------
    term          : str   — display name (English)
    term_es       : str   — display name (Spanish)
    definition_en : str   — full English definition (1-3 sentences)
    definition_es : str   — full Spanish definition
    category      : str   — one of CATEGORIES
    related_terms : list  — list of other GLOSSARY keys
    difficulty    : str   — "beginner" | "intermediate" | "advanced"
    example_en    : str   — optional usage example (English)
    example_es    : str   — optional usage example (Spanish)

Categories
----------
    basics, mining, transactions, lightning, privacy, security,
    protocol, wallet
"""

from __future__ import annotations

CATEGORIES = frozenset(
    {
        "basics",
        "mining",
        "transactions",
        "lightning",
        "privacy",
        "security",
        "protocol",
        "wallet",
    }
)

DIFFICULTY_LEVELS = ("beginner", "intermediate", "advanced")

# ---------------------------------------------------------------------------
# Master glossary dictionary
# ---------------------------------------------------------------------------

GLOSSARY: dict[str, dict] = {
    # -----------------------------------------------------------------------
    # B A S I C S
    # -----------------------------------------------------------------------
    "bitcoin": {
        "term": "Bitcoin",
        "term_es": "Bitcoin",
        "definition_en": (
            "Bitcoin is a decentralized digital currency created in 2009 by the "
            "pseudonymous Satoshi Nakamoto. It operates on a peer-to-peer network "
            "without a central authority, using cryptographic proof instead of trust "
            "to secure transactions and control the issuance of new units."
        ),
        "definition_es": (
            "Bitcoin es una moneda digital descentralizada creada en 2009 por el "
            "seudónimo Satoshi Nakamoto. Opera en una red entre pares sin autoridad "
            "central, usando prueba criptográfica en lugar de confianza para asegurar "
            "las transacciones y controlar la emisión de nuevas unidades."
        ),
        "category": "basics",
        "related_terms": ["satoshi", "blockchain", "mining", "node"],
        "difficulty": "beginner",
        "example_en": "I saved 0.01 Bitcoin this month as part of my DCA strategy.",
        "example_es": "Ahorré 0.01 Bitcoin este mes como parte de mi estrategia DCA.",
    },
    "satoshi": {
        "term": "Satoshi (sat)",
        "term_es": "Satoshi (sat)",
        "definition_en": (
            "The smallest denomination of Bitcoin, named after its creator Satoshi "
            "Nakamoto. One Bitcoin equals 100,000,000 satoshis (10^8 sats). Satoshis "
            "are the native unit used by the Lightning Network and on-chain "
            "transaction outputs."
        ),
        "definition_es": (
            "La denominación más pequeña de Bitcoin, nombrada en honor a su creador "
            "Satoshi Nakamoto. Un Bitcoin equivale a 100,000,000 satoshis (10^8 sats). "
            "Los satoshis son la unidad nativa usada por la Red Lightning y las salidas "
            "de transacciones en cadena."
        ),
        "category": "basics",
        "related_terms": ["bitcoin", "sats", "invoice"],
        "difficulty": "beginner",
        "example_en": "A cup of coffee costs about 2,000 sats at current prices.",
        "example_es": "Una taza de café cuesta aproximadamente 2,000 sats a precios actuales.",
    },
    "sats": {
        "term": "Sats",
        "term_es": "Sats",
        "definition_en": (
            "Informal abbreviation for satoshis — the smallest unit of Bitcoin "
            "(1 BTC = 100,000,000 sats). The phrase 'stacking sats' refers to the "
            "practice of accumulating small amounts of Bitcoin over time."
        ),
        "definition_es": (
            "Abreviatura informal de satoshis — la unidad más pequeña de Bitcoin "
            "(1 BTC = 100,000,000 sats). La frase 'apilar sats' se refiere a la "
            "práctica de acumular pequeñas cantidades de Bitcoin con el tiempo."
        ),
        "category": "basics",
        "related_terms": ["satoshi", "bitcoin", "dca"],
        "difficulty": "beginner",
        "example_en": "Stack sats daily with automated purchases.",
        "example_es": "Apila sats diariamente con compras automatizadas.",
    },
    "address": {
        "term": "Bitcoin Address",
        "term_es": "Dirección Bitcoin",
        "definition_en": (
            "A Bitcoin address is an identifier that represents a possible destination "
            "for a Bitcoin payment. It is derived from a public key using hashing and "
            "encoding. Modern address formats include P2PKH (starting with 1), P2SH "
            "(starting with 3), Bech32 SegWit (starting with bc1q), and Bech32m "
            "Taproot (starting with bc1p)."
        ),
        "definition_es": (
            "Una dirección Bitcoin es un identificador que representa un posible destino "
            "para un pago. Se deriva de una clave pública usando hashing y codificación. "
            "Los formatos modernos incluyen P2PKH (comienza con 1), P2SH (comienza con 3), "
            "Bech32 SegWit (comienza con bc1q) y Bech32m Taproot (comienza con bc1p)."
        ),
        "category": "basics",
        "related_terms": ["p2pkh", "p2sh", "p2wpkh", "p2tr", "pubkey"],
        "difficulty": "beginner",
        "example_en": "Share your address to receive Bitcoin from anyone, anytime.",
        "example_es": "Comparte tu dirección para recibir Bitcoin de cualquiera, en cualquier momento.",
    },
    "blockchain": {
        "term": "Blockchain",
        "term_es": "Cadena de bloques",
        "definition_en": (
            "The blockchain is Bitcoin's public ledger — a chronological, immutable "
            "chain of blocks, each containing a set of validated transactions. Every "
            "full node on the network maintains a complete copy, making double-spending "
            "computationally infeasible without controlling the majority of hash rate."
        ),
        "definition_es": (
            "La cadena de bloques es el libro mayor público de Bitcoin — una cadena "
            "cronológica e inmutable de bloques, cada uno con un conjunto de "
            "transacciones validadas. Cada nodo completo mantiene una copia, haciendo "
            "inviable el doble gasto sin controlar la mayor parte del hash rate."
        ),
        "category": "basics",
        "related_terms": ["block", "genesis_block", "node", "mining"],
        "difficulty": "beginner",
        "example_en": "You can verify any Bitcoin transaction by inspecting the blockchain.",
        "example_es": "Puedes verificar cualquier transacción examinando la cadena de bloques.",
    },
    "block": {
        "term": "Block",
        "term_es": "Bloque",
        "definition_en": (
            "A block is a data structure that bundles a set of Bitcoin transactions "
            "together with a header containing metadata: the previous block hash, a "
            "Merkle root of all transactions, a timestamp, the difficulty target, and a "
            "nonce. Miners compete to find a valid nonce that makes the block hash "
            "satisfy the current difficulty target."
        ),
        "definition_es": (
            "Un bloque es una estructura de datos que agrupa transacciones Bitcoin con "
            "una cabecera que contiene metadatos: el hash del bloque anterior, la raíz "
            "Merkle de todas las transacciones, una marca de tiempo, el objetivo de "
            "dificultad y un nonce. Los mineros compiten para encontrar un nonce válido "
            "que haga que el hash del bloque satisfaga el objetivo de dificultad."
        ),
        "category": "basics",
        "related_terms": ["blockchain", "nonce", "mining", "merkle_tree"],
        "difficulty": "beginner",
        "example_en": "A new Bitcoin block is mined approximately every 10 minutes.",
        "example_es": "Un nuevo bloque Bitcoin se mina aproximadamente cada 10 minutos.",
    },
    "genesis_block": {
        "term": "Genesis Block",
        "term_es": "Bloque Génesis",
        "definition_en": (
            "The genesis block (block 0) is the very first block in the Bitcoin "
            "blockchain, mined by Satoshi Nakamoto on January 3, 2009. It contains the "
            "famous embedded message: 'The Times 03/Jan/2009 Chancellor on brink of "
            "second bailout for banks', referencing a newspaper headline as a timestamp "
            "and political statement."
        ),
        "definition_es": (
            "El bloque génesis (bloque 0) es el primer bloque de la cadena de bloques "
            "de Bitcoin, minado por Satoshi Nakamoto el 3 de enero de 2009. Contiene el "
            "famoso mensaje: 'The Times 03/Jan/2009 Chancellor on brink of second "
            "bailout for banks', referenciando un titular de periódico como sello de "
            "tiempo y declaración política."
        ),
        "category": "basics",
        "related_terms": ["blockchain", "block", "bitcoin"],
        "difficulty": "beginner",
        "example_en": "The genesis block reward of 50 BTC can never be spent.",
        "example_es": "La recompensa de 50 BTC del bloque génesis nunca puede gastarse.",
    },
    "hodl": {
        "term": "HODL",
        "term_es": "HODL",
        "definition_en": (
            "HODL originated from a 2013 BitcoinTalk forum post with a typo of 'hold'. "
            "It has since been backronymed to 'Hold On for Dear Life'. In Bitcoin "
            "culture, HODLing means holding Bitcoin long-term regardless of price "
            "volatility, based on the belief in its long-term value proposition."
        ),
        "definition_es": (
            "HODL surgió de un post de 2013 en el foro BitcoinTalk con un error "
            "tipográfico de 'hold'. Desde entonces se ha retroacronomizado como 'Hold "
            "On for Dear Life'. En la cultura Bitcoin, hacer HODL significa mantener "
            "Bitcoin a largo plazo sin importar la volatilidad del precio."
        ),
        "category": "basics",
        "related_terms": ["dca", "cold_storage", "wallet"],
        "difficulty": "beginner",
        "example_en": "Despite the market downturn, she chose to HODL her Bitcoin.",
        "example_es": "A pesar de la caída del mercado, ella eligió hacer HODL con su Bitcoin.",
    },
    "dca": {
        "term": "DCA (Dollar-Cost Averaging)",
        "term_es": "Promedio del Costo en Dólares",
        "definition_en": (
            "Dollar-Cost Averaging is an investment strategy where a fixed amount of "
            "money is used to purchase Bitcoin at regular intervals (e.g., weekly or "
            "monthly) regardless of price. Over time this reduces the impact of "
            "volatility by averaging the purchase price across market cycles."
        ),
        "definition_es": (
            "El Promedio del Costo en Dólares es una estrategia de inversión donde se "
            "usa una cantidad fija de dinero para comprar Bitcoin a intervalos regulares "
            "(p.ej., semanal o mensual) independientemente del precio. Con el tiempo "
            "reduce el impacto de la volatilidad promediando el precio de compra."
        ),
        "category": "basics",
        "related_terms": ["hodl", "satoshi", "savings"],
        "difficulty": "beginner",
        "example_en": "She DCA's $50 into Bitcoin every Friday via Magma.",
        "example_es": "Ella hace DCA de $50 en Bitcoin cada viernes a través de Magma.",
    },
    # -----------------------------------------------------------------------
    # M I N I N G
    # -----------------------------------------------------------------------
    "mining": {
        "term": "Bitcoin Mining",
        "term_es": "Minería Bitcoin",
        "definition_en": (
            "Bitcoin mining is the process by which new transactions are validated and "
            "added to the blockchain. Miners repeatedly hash block header data with "
            "different nonces until the resulting hash meets the current difficulty "
            "target. The winning miner earns the block subsidy plus transaction fees."
        ),
        "definition_es": (
            "La minería Bitcoin es el proceso mediante el cual se validan nuevas "
            "transacciones y se añaden a la cadena de bloques. Los mineros hacen "
            "hash de la cabecera del bloque con diferentes nonces hasta que el hash "
            "resultante cumple el objetivo de dificultad. El minero ganador obtiene "
            "el subsidio de bloque más las tarifas de transacción."
        ),
        "category": "mining",
        "related_terms": ["hash_rate", "difficulty", "nonce", "proof_of_work", "halving"],
        "difficulty": "beginner",
        "example_en": "El Salvador uses geothermal energy for environmentally friendly Bitcoin mining.",
        "example_es": "El Salvador usa energía geotérmica para la minería de Bitcoin respetuosa con el medio ambiente.",
    },
    "proof_of_work": {
        "term": "Proof of Work (PoW)",
        "term_es": "Prueba de Trabajo",
        "definition_en": (
            "Proof of Work is the consensus mechanism used by Bitcoin. It requires "
            "miners to expend real-world energy to produce a hash below a target "
            "threshold. PoW makes Sybil attacks expensive, ensures unforgeable costliness "
            "for each block, and is the foundation of Bitcoin's security model."
        ),
        "definition_es": (
            "La Prueba de Trabajo es el mecanismo de consenso de Bitcoin. Requiere "
            "que los mineros gasten energía del mundo real para producir un hash "
            "por debajo de un umbral objetivo. PoW hace costosos los ataques Sybil, "
            "asegura un costo no falsificable para cada bloque y es la base del "
            "modelo de seguridad de Bitcoin."
        ),
        "category": "mining",
        "related_terms": ["mining", "hash_rate", "difficulty", "nonce"],
        "difficulty": "intermediate",
        "example_en": "Proof of Work ensures that altering past blocks requires redoing all subsequent work.",
        "example_es": "La Prueba de Trabajo asegura que alterar bloques pasados requiere rehacer todo el trabajo posterior.",
    },
    "hash_rate": {
        "term": "Hash Rate",
        "term_es": "Tasa de Hash",
        "definition_en": (
            "Hash rate measures the computational power being applied to the Bitcoin "
            "network, expressed in hashes per second (H/s). A higher network hash rate "
            "means greater security and makes a 51% attack more expensive. Hash rate "
            "is commonly measured in EH/s (exahashes per second) for the entire network."
        ),
        "definition_es": (
            "La tasa de hash mide el poder computacional aplicado a la red Bitcoin, "
            "expresado en hashes por segundo (H/s). Una mayor tasa de hash en la red "
            "significa mayor seguridad y hace un ataque del 51% más costoso. Se mide "
            "comúnmente en EH/s (exahashes por segundo) para toda la red."
        ),
        "category": "mining",
        "related_terms": ["mining", "difficulty", "proof_of_work"],
        "difficulty": "intermediate",
        "example_en": "The Bitcoin network hash rate reached 500 EH/s in 2024.",
        "example_es": "La tasa de hash de la red Bitcoin alcanzó 500 EH/s en 2024.",
    },
    "difficulty": {
        "term": "Difficulty",
        "term_es": "Dificultad",
        "definition_en": (
            "Bitcoin's mining difficulty is a measure of how hard it is to find a valid "
            "block hash. It automatically adjusts every 2016 blocks (~2 weeks) to "
            "maintain an average block time of 10 minutes, regardless of how much "
            "hash rate joins or leaves the network."
        ),
        "definition_es": (
            "La dificultad de minería de Bitcoin mide cuán difícil es encontrar un "
            "hash de bloque válido. Se ajusta automáticamente cada 2016 bloques "
            "(~2 semanas) para mantener un tiempo promedio de bloque de 10 minutos, "
            "independientemente de cuánto hash rate se una o abandone la red."
        ),
        "category": "mining",
        "related_terms": ["mining", "hash_rate", "proof_of_work", "block"],
        "difficulty": "intermediate",
        "example_en": "Bitcoin's difficulty adjustment is one of its most elegant innovations.",
        "example_es": "El ajuste de dificultad de Bitcoin es una de sus innovaciones más elegantes.",
    },
    "nonce": {
        "term": "Nonce",
        "term_es": "Nonce",
        "definition_en": (
            "A nonce (Number used ONCE) is a 32-bit field in the Bitcoin block header "
            "that miners increment repeatedly while trying to produce a block hash "
            "below the difficulty target. When the nonce space is exhausted (2^32 "
            "attempts), miners modify other fields such as the extra nonce in the "
            "coinbase transaction."
        ),
        "definition_es": (
            "Un nonce (Número usado UNA VEZ) es un campo de 32 bits en la cabecera "
            "del bloque Bitcoin que los mineros incrementan repetidamente al intentar "
            "producir un hash de bloque por debajo del objetivo de dificultad. Cuando "
            "se agota el espacio del nonce, los mineros modifican otros campos como "
            "el extra nonce en la transacción coinbase."
        ),
        "category": "mining",
        "related_terms": ["mining", "proof_of_work", "block", "hash_rate"],
        "difficulty": "advanced",
        "example_en": "A miner may try billions of nonce values before finding a valid block.",
        "example_es": "Un minero puede probar miles de millones de valores nonce antes de encontrar un bloque válido.",
    },
    "halving": {
        "term": "Halving",
        "term_es": "Halving (reducción a la mitad)",
        "definition_en": (
            "The Bitcoin halving is an event that occurs approximately every 210,000 "
            "blocks (~4 years) where the block subsidy paid to miners is cut in half. "
            "Starting at 50 BTC in 2009, the subsidy halves progressively until all "
            "21 million bitcoins have been mined (around 2140). Halvings are a "
            "deflationary mechanism hardcoded into the Bitcoin protocol."
        ),
        "definition_es": (
            "El halving de Bitcoin es un evento que ocurre aproximadamente cada "
            "210,000 bloques (~4 años) donde el subsidio de bloque pagado a los "
            "mineros se reduce a la mitad. Comenzando en 50 BTC en 2009, el subsidio "
            "se reduce progresivamente hasta que se hayan minado los 21 millones de "
            "bitcoins (~año 2140). Los halvings son un mecanismo deflacionario "
            "programado en el protocolo Bitcoin."
        ),
        "category": "mining",
        "related_terms": ["mining", "block", "subsidy", "scarcity"],
        "difficulty": "beginner",
        "example_en": "The 2024 halving reduced the block reward from 6.25 to 3.125 BTC.",
        "example_es": "El halving de 2024 redujo la recompensa de bloque de 6.25 a 3.125 BTC.",
    },
    # -----------------------------------------------------------------------
    # T R A N S A C T I O N S
    # -----------------------------------------------------------------------
    "transaction": {
        "term": "Transaction",
        "term_es": "Transacción",
        "definition_en": (
            "A Bitcoin transaction is a digitally signed message that transfers "
            "ownership of satoshis from one or more inputs (previously received UTXOs) "
            "to one or more outputs. Transactions are broadcast to the network, "
            "collected into blocks by miners, and confirmed once included in the chain."
        ),
        "definition_es": (
            "Una transacción Bitcoin es un mensaje firmado digitalmente que transfiere "
            "la propiedad de satoshis de una o más entradas (UTXOs recibidos "
            "previamente) a una o más salidas. Las transacciones se difunden a la "
            "red, los mineros las recopilan en bloques y se confirman una vez "
            "incluidas en la cadena."
        ),
        "category": "transactions",
        "related_terms": ["utxo", "input", "output", "fee_rate", "txid", "mempool"],
        "difficulty": "beginner",
        "example_en": "A typical Bitcoin transaction has 1 input and 2 outputs (payment + change).",
        "example_es": "Una transacción Bitcoin típica tiene 1 entrada y 2 salidas (pago + cambio).",
    },
    "utxo": {
        "term": "UTXO (Unspent Transaction Output)",
        "term_es": "UTXO (Salida de Transacción No Gastada)",
        "definition_en": (
            "An Unspent Transaction Output is a discrete chunk of Bitcoin that has "
            "been received but not yet spent. Your wallet balance is the sum of all "
            "UTXOs you control. When you spend Bitcoin, you consume one or more UTXOs "
            "as inputs and create new UTXOs as outputs — there is no concept of a "
            "single account balance on-chain."
        ),
        "definition_es": (
            "Una Salida de Transacción No Gastada es una cantidad discreta de Bitcoin "
            "recibida pero aún no gastada. El saldo de tu billetera es la suma de "
            "todos los UTXOs que controlas. Al gastar Bitcoin, consumes uno o más "
            "UTXOs como entradas y creas nuevos UTXOs como salidas — no existe el "
            "concepto de saldo de cuenta única en la cadena."
        ),
        "category": "transactions",
        "related_terms": ["transaction", "input", "output", "coin_control"],
        "difficulty": "intermediate",
        "example_en": "Good UTXO management can significantly reduce future transaction fees.",
        "example_es": "Una buena gestión de UTXOs puede reducir significativamente las tarifas futuras.",
    },
    "input": {
        "term": "Transaction Input",
        "term_es": "Entrada de Transacción",
        "definition_en": (
            "A transaction input references a previous UTXO by its transaction ID and "
            "output index, and provides a scriptSig (or witness for SegWit) that "
            "unlocks it. Inputs prove that the spender has the right to consume the "
            "referenced output. The sum of input values must equal the sum of output "
            "values plus the miner fee."
        ),
        "definition_es": (
            "Una entrada de transacción referencia un UTXO anterior por su ID de "
            "transacción e índice de salida, y proporciona un scriptSig (o witness "
            "para SegWit) que lo desbloquea. Las entradas prueban que el gastador "
            "tiene derecho a consumir la salida referenciada."
        ),
        "category": "transactions",
        "related_terms": ["utxo", "output", "transaction", "script"],
        "difficulty": "intermediate",
        "example_en": "A coin-join transaction combines many inputs from different users.",
        "example_es": "Una transacción coin-join combina muchas entradas de diferentes usuarios.",
    },
    "output": {
        "term": "Transaction Output",
        "term_es": "Salida de Transacción",
        "definition_en": (
            "A transaction output specifies an amount of satoshis and a locking script "
            "(scriptPubKey) that defines the conditions under which those satoshis can "
            "be spent. Once an output is created it becomes a UTXO until it is "
            "referenced as an input in a future transaction."
        ),
        "definition_es": (
            "Una salida de transacción especifica una cantidad de satoshis y un script "
            "de bloqueo (scriptPubKey) que define las condiciones bajo las cuales esos "
            "satoshis pueden gastarse. Una vez creada, la salida se convierte en un "
            "UTXO hasta que es referenciada como entrada en una transacción futura."
        ),
        "category": "transactions",
        "related_terms": ["utxo", "input", "transaction", "script"],
        "difficulty": "intermediate",
        "example_en": "The change output returns leftover satoshis back to the sender's wallet.",
        "example_es": "La salida de cambio devuelve los satoshis sobrantes a la billetera del remitente.",
    },
    "txid": {
        "term": "TXID (Transaction ID)",
        "term_es": "TXID (ID de Transacción)",
        "definition_en": (
            "A Transaction ID is the double-SHA256 hash of a serialised transaction, "
            "displayed in hex (little-endian). It uniquely identifies every transaction "
            "on the Bitcoin network and is used by block explorers, wallets, and "
            "other software to look up transaction details."
        ),
        "definition_es": (
            "Un ID de Transacción es el hash SHA256 doble de una transacción "
            "serializada, mostrado en hexadecimal (little-endian). Identifica "
            "de forma única cada transacción en la red Bitcoin y es usado por "
            "exploradores de bloques, billeteras y otro software."
        ),
        "category": "transactions",
        "related_terms": ["transaction", "utxo", "blockchain"],
        "difficulty": "beginner",
        "example_en": "Paste the TXID into a block explorer to track your payment confirmation.",
        "example_es": "Pega el TXID en un explorador de bloques para rastrear la confirmación de tu pago.",
    },
    "fee_rate": {
        "term": "Fee Rate",
        "term_es": "Tasa de Tarifa",
        "definition_en": (
            "The fee rate is the price per unit of transaction weight, expressed in "
            "satoshis per virtual byte (sat/vB). Miners prioritize transactions with "
            "higher fee rates when filling block space. Fee rates fluctuate with "
            "demand for block space and can range from 1 sat/vB during quiet periods "
            "to hundreds of sat/vB during congestion."
        ),
        "definition_es": (
            "La tasa de tarifa es el precio por unidad de peso de transacción, "
            "expresado en satoshis por byte virtual (sat/vB). Los mineros priorizan "
            "transacciones con tasas más altas al llenar el espacio de bloque. Las "
            "tasas fluctúan con la demanda de espacio en bloque y pueden ir de "
            "1 sat/vB en períodos tranquilos a cientos durante congestión."
        ),
        "category": "transactions",
        "related_terms": ["mempool", "vbyte", "rbf", "cpfp", "transaction"],
        "difficulty": "intermediate",
        "example_en": "She set a fee rate of 5 sat/vB for a low-priority transaction.",
        "example_es": "Ella estableció una tasa de 5 sat/vB para una transacción de baja prioridad.",
    },
    "vbyte": {
        "term": "Virtual Byte (vByte, vB)",
        "term_es": "Byte Virtual (vByte, vB)",
        "definition_en": (
            "A virtual byte is the unit of transaction size used for fee calculations "
            "after the SegWit upgrade. Transaction weight in weight units (WU) is "
            "divided by 4 to get vbytes. Witness data is discounted — it counts as "
            "1 WU per byte rather than 4 WU — which makes SegWit transactions cheaper "
            "per sat transferred."
        ),
        "definition_es": (
            "Un byte virtual es la unidad de tamaño de transacción usada para cálculo "
            "de tarifas tras la actualización SegWit. El peso de la transacción en "
            "unidades de peso (WU) se divide entre 4 para obtener vbytes. Los datos "
            "witness tienen descuento — cuentan como 1 WU por byte en vez de 4 — lo "
            "que hace más baratas las transacciones SegWit."
        ),
        "category": "transactions",
        "related_terms": ["fee_rate", "segwit", "witness", "transaction"],
        "difficulty": "advanced",
        "example_en": "A native SegWit transaction is typically 30-40% smaller in vbytes.",
        "example_es": "Una transacción SegWit nativa es típicamente 30-40% más pequeña en vbytes.",
    },
    "mempool": {
        "term": "Mempool",
        "term_es": "Mempool",
        "definition_en": (
            "The memory pool (mempool) is each node's local holding area for unconfirmed "
            "transactions that have been broadcast but not yet included in a block. "
            "Miners select transactions from the mempool — typically by fee rate — to "
            "fill new blocks. During high-demand periods the mempool can hold thousands "
            "of transactions and fee rates rise accordingly."
        ),
        "definition_es": (
            "El pool de memoria (mempool) es el área de espera local de cada nodo "
            "para transacciones no confirmadas que han sido difundidas pero aún no "
            "incluidas en un bloque. Los mineros seleccionan transacciones del mempool "
            "— típicamente por tasa de tarifa — para llenar nuevos bloques. En "
            "períodos de alta demanda puede contener miles de transacciones."
        ),
        "category": "transactions",
        "related_terms": ["transaction", "fee_rate", "node", "rbf", "cpfp"],
        "difficulty": "intermediate",
        "example_en": "Check the mempool before sending to choose an appropriate fee rate.",
        "example_es": "Consulta el mempool antes de enviar para elegir una tarifa apropiada.",
    },
    "rbf": {
        "term": "RBF (Replace-By-Fee)",
        "term_es": "RBF (Reemplazar por Tarifa)",
        "definition_en": (
            "Replace-By-Fee (BIP125) allows a sender to replace an unconfirmed "
            "transaction in the mempool with a new version that pays a higher fee rate. "
            "This is useful when a transaction is stuck due to an insufficient fee. "
            "The new transaction must use at least one of the same inputs and offer a "
            "higher absolute fee than the original."
        ),
        "definition_es": (
            "Replace-By-Fee (BIP125) permite al remitente reemplazar una transacción "
            "no confirmada en el mempool con una nueva versión que paga una tarifa más "
            "alta. Útil cuando una transacción queda atascada por tarifa insuficiente. "
            "La nueva transacción debe usar al menos una de las mismas entradas y "
            "ofrecer una tarifa absoluta más alta."
        ),
        "category": "transactions",
        "related_terms": ["mempool", "fee_rate", "cpfp", "transaction"],
        "difficulty": "intermediate",
        "example_en": "Use RBF to speed up a stuck transaction by bumping the fee.",
        "example_es": "Usa RBF para acelerar una transacción atascada aumentando la tarifa.",
    },
    "cpfp": {
        "term": "CPFP (Child Pays for Parent)",
        "term_es": "CPFP (El Hijo Paga por el Padre)",
        "definition_en": (
            "Child Pays for Parent is a fee-bumping technique where the recipient of "
            "an unconfirmed transaction creates a new transaction spending one of its "
            "outputs with a very high fee. Since miners must include the parent to "
            "confirm the child, they are incentivized to mine both transactions "
            "together, effectively boosting the parent's confirmation priority."
        ),
        "definition_es": (
            "El Hijo Paga por el Padre es una técnica para aumentar tarifas donde "
            "el receptor de una transacción no confirmada crea una nueva transacción "
            "gastando una de sus salidas con tarifa muy alta. Dado que los mineros "
            "deben incluir al padre para confirmar al hijo, se incentivan a minar "
            "ambas transacciones juntas, aumentando la prioridad de confirmación."
        ),
        "category": "transactions",
        "related_terms": ["rbf", "mempool", "fee_rate", "transaction", "utxo"],
        "difficulty": "advanced",
        "example_en": "If RBF is not enabled, CPFP is the alternative fee-bumping option.",
        "example_es": "Si RBF no está habilitado, CPFP es la alternativa para aumentar la tarifa.",
    },
    "op_return": {
        "term": "OP_RETURN",
        "term_es": "OP_RETURN",
        "definition_en": (
            "OP_RETURN is a Bitcoin script opcode that marks a transaction output as "
            "provably unspendable. It allows up to 80 bytes of arbitrary data to be "
            "embedded in the blockchain without polluting the UTXO set. Applications "
            "include timestamping, colored coins, and anchoring data hashes to the "
            "Bitcoin blockchain for proof of existence."
        ),
        "definition_es": (
            "OP_RETURN es un código de operación de script Bitcoin que marca una salida "
            "de transacción como irremediablemente no gastable. Permite incrustar hasta "
            "80 bytes de datos arbitrarios en la cadena sin contaminar el conjunto UTXO. "
            "Las aplicaciones incluyen marcas de tiempo, colored coins y anclaje de "
            "hashes de datos para prueba de existencia."
        ),
        "category": "transactions",
        "related_terms": ["script", "output", "transaction"],
        "difficulty": "advanced",
        "example_en": "OP_RETURN can embed a document hash as timestamped proof of existence.",
        "example_es": "OP_RETURN puede incrustar un hash de documento como prueba de existencia con marca de tiempo.",
    },
    "orphan": {
        "term": "Orphan Block",
        "term_es": "Bloque Huérfano",
        "definition_en": (
            "An orphan block (also called stale block) is a valid block that is not "
            "included in the main chain because another block at the same height was "
            "accepted first by the network. Orphans occur naturally when two miners "
            "find valid blocks nearly simultaneously; the network resolves the tie by "
            "always extending the chain with the most accumulated proof of work."
        ),
        "definition_es": (
            "Un bloque huérfano (también llamado bloque obsoleto) es un bloque válido "
            "que no está incluido en la cadena principal porque otro bloque a la misma "
            "altura fue aceptado primero por la red. Los huérfanos ocurren naturalmente "
            "cuando dos mineros encuentran bloques válidos casi simultáneamente."
        ),
        "category": "mining",
        "related_terms": ["block", "blockchain", "reorg", "mining"],
        "difficulty": "advanced",
        "example_en": "Orphan blocks become rare as network latency decreases.",
        "example_es": "Los bloques huérfanos se vuelven raros a medida que disminuye la latencia de red.",
    },
    "reorg": {
        "term": "Chain Reorganization (Reorg)",
        "term_es": "Reorganización de cadena (Reorg)",
        "definition_en": (
            "A blockchain reorganization occurs when a node switches from one chain "
            "to a longer competing chain, effectively undoing previously seen blocks. "
            "Shallow reorgs (1-2 blocks) happen occasionally due to network latency. "
            "Deep reorgs would require an attacker to control the majority of the "
            "network's hash rate (51% attack)."
        ),
        "definition_es": (
            "Una reorganización de cadena ocurre cuando un nodo cambia de una cadena "
            "a una cadena competidora más larga, deshaciendo efectivamente bloques "
            "vistos anteriormente. Las reorgs superficiales (1-2 bloques) ocurren "
            "ocasionalmente por latencia de red. Las reorgs profundas requerirían "
            "que un atacante controle la mayoría del hash rate (ataque del 51%)."
        ),
        "category": "protocol",
        "related_terms": ["orphan", "blockchain", "hash_rate", "mining"],
        "difficulty": "advanced",
        "example_en": "Exchanges typically require 6 confirmations to guard against shallow reorgs.",
        "example_es": "Los exchanges típicamente requieren 6 confirmaciones para protegerse de reorgs superficiales.",
    },
    # -----------------------------------------------------------------------
    # L I G H T N I N G
    # -----------------------------------------------------------------------
    "lightning": {
        "term": "Lightning Network",
        "term_es": "Red Lightning",
        "definition_en": (
            "The Lightning Network is a layer-2 payment protocol built on top of "
            "Bitcoin that enables instant, near-zero-fee transactions through a network "
            "of bidirectional payment channels. Payments route through the channel "
            "network without touching the main blockchain until a channel is closed. "
            "It is defined by the BOLT specifications."
        ),
        "definition_es": (
            "La Red Lightning es un protocolo de pago de capa 2 construido sobre "
            "Bitcoin que permite transacciones instantáneas y casi sin comisiones "
            "a través de una red de canales de pago bidireccionales. Los pagos se "
            "enrutan a través de la red de canales sin tocar la blockchain principal "
            "hasta que un canal es cerrado. Está definida por las especificaciones BOLT."
        ),
        "category": "lightning",
        "related_terms": ["channel", "invoice", "bolt", "node", "htlc"],
        "difficulty": "beginner",
        "example_en": "Pay for coffee in seconds with Lightning without a mining fee.",
        "example_es": "Paga un café en segundos con Lightning sin tarifa de minería.",
    },
    "channel": {
        "term": "Payment Channel",
        "term_es": "Canal de Pago",
        "definition_en": (
            "A Lightning payment channel is a 2-of-2 multisig UTXO (the 'funding "
            "transaction') that two parties use to exchange Bitcoin off-chain. "
            "The channel balance can be updated unlimited times through signed "
            "commitment transactions; only the opening and closing transactions "
            "are recorded on-chain."
        ),
        "definition_es": (
            "Un canal de pago Lightning es un UTXO multisig 2-de-2 (la 'transacción "
            "de financiamiento') que dos partes usan para intercambiar Bitcoin fuera "
            "de la cadena. El saldo del canal puede actualizarse ilimitadas veces "
            "mediante transacciones de compromiso firmadas; solo las transacciones "
            "de apertura y cierre se registran en cadena."
        ),
        "category": "lightning",
        "related_terms": ["lightning", "multisig", "htlc", "invoice"],
        "difficulty": "intermediate",
        "example_en": "Opening a channel requires one on-chain transaction and some sats as collateral.",
        "example_es": "Abrir un canal requiere una transacción en cadena y algunos sats como colateral.",
    },
    "invoice": {
        "term": "Lightning Invoice",
        "term_es": "Factura Lightning",
        "definition_en": (
            "A Lightning invoice is a payment request encoded as a string (BOLT11 "
            "format) that specifies the recipient node, amount, payment hash, and "
            "expiry time. The payer decodes the invoice and routes a payment through "
            "the Lightning Network. Invoices are single-use by design."
        ),
        "definition_es": (
            "Una factura Lightning es una solicitud de pago codificada como cadena "
            "(formato BOLT11) que especifica el nodo receptor, el monto, el hash "
            "de pago y el tiempo de expiración. El pagador decodifica la factura "
            "y enruta un pago a través de la Red Lightning. Las facturas son de "
            "un solo uso por diseño."
        ),
        "category": "lightning",
        "related_terms": ["lightning", "bolt", "channel", "node"],
        "difficulty": "beginner",
        "example_en": "Scan the Lightning invoice QR code to pay instantly.",
        "example_es": "Escanea el código QR de la factura Lightning para pagar instantáneamente.",
    },
    "bolt": {
        "term": "BOLT (Basis of Lightning Technology)",
        "term_es": "BOLT (Base de la Tecnología Lightning)",
        "definition_en": (
            "BOLT is the set of specifications that define the Lightning Network "
            "protocol. Individual BOLTs cover topics such as the base layer encoding "
            "(BOLT1), peer protocol (BOLT2), onion routing (BOLT4), payment channels "
            "(BOLT3), and invoice format (BOLT11). Interoperability between Lightning "
            "implementations depends on compliance with these specs."
        ),
        "definition_es": (
            "BOLT es el conjunto de especificaciones que definen el protocolo de la "
            "Red Lightning. Los BOLTs individuales cubren temas como la codificación "
            "de capa base (BOLT1), protocolo entre pares (BOLT2), enrutamiento cebolla "
            "(BOLT4), canales de pago (BOLT3) y formato de factura (BOLT11)."
        ),
        "category": "lightning",
        "related_terms": ["lightning", "invoice", "channel", "node"],
        "difficulty": "advanced",
        "example_en": "BOLT11 defines the widely-used Lightning invoice format.",
        "example_es": "BOLT11 define el formato de factura Lightning ampliamente utilizado.",
    },
    "htlc": {
        "term": "HTLC (Hash Time-Locked Contract)",
        "term_es": "HTLC (Contrato de Hash Bloqueado por Tiempo)",
        "definition_en": (
            "A Hash Time-Locked Contract is a conditional payment used in the Lightning "
            "Network that requires the recipient to provide the preimage of a specific "
            "hash (proving they control the destination) within a time window. HTLCs "
            "allow trustless multi-hop payments to be routed through the channel "
            "network without each hop needing to trust the others."
        ),
        "definition_es": (
            "Un Contrato de Hash Bloqueado por Tiempo es un pago condicional usado en "
            "la Red Lightning que requiere que el receptor proporcione la preimagen de "
            "un hash específico dentro de una ventana de tiempo. Los HTLCs permiten "
            "pagos de múltiples saltos sin confianza a través de la red de canales."
        ),
        "category": "lightning",
        "related_terms": ["lightning", "channel", "invoice", "bolt"],
        "difficulty": "advanced",
        "example_en": "HTLCs ensure that intermediate routing nodes cannot steal funds.",
        "example_es": "Los HTLCs garantizan que los nodos intermedios no puedan robar fondos.",
    },
    # -----------------------------------------------------------------------
    # P R O T O C O L
    # -----------------------------------------------------------------------
    "bip": {
        "term": "BIP (Bitcoin Improvement Proposal)",
        "term_es": "BIP (Propuesta de Mejora de Bitcoin)",
        "definition_en": (
            "A Bitcoin Improvement Proposal is a design document providing information "
            "to the Bitcoin community, or describing a new feature, process, or "
            "environment change. BIPs follow a lifecycle: Draft, Proposed, Final, "
            "Withdrawn, or Rejected. Notable BIPs include BIP32 (HD wallets), "
            "BIP39 (mnemonic seeds), BIP141 (SegWit), and BIP340-342 (Taproot/Schnorr)."
        ),
        "definition_es": (
            "Una Propuesta de Mejora de Bitcoin es un documento de diseño que "
            "proporciona información a la comunidad Bitcoin, o describe una nueva "
            "función, proceso o cambio de entorno. Los BIPs siguen un ciclo de vida: "
            "Borrador, Propuesto, Final, Retirado o Rechazado."
        ),
        "category": "protocol",
        "related_terms": ["segwit", "taproot", "hd_wallet", "psbt"],
        "difficulty": "intermediate",
        "example_en": "BIP141 introduced SegWit, fixing transaction malleability.",
        "example_es": "BIP141 introdujo SegWit, solucionando la maleabilidad de transacciones.",
    },
    "segwit": {
        "term": "SegWit (Segregated Witness)",
        "term_es": "SegWit (Testigo Segregado)",
        "definition_en": (
            "Segregated Witness (BIP141) is a protocol upgrade activated in August 2017 "
            "that moves signature (witness) data outside the traditional transaction "
            "structure. This fixed transaction malleability, reduced fee rates for "
            "SegWit transactions via the weight discount, and enabled the Lightning "
            "Network. Native SegWit addresses start with bc1q."
        ),
        "definition_es": (
            "Testigo Segregado (BIP141) es una actualización de protocolo activada en "
            "agosto de 2017 que mueve los datos de firma (witness) fuera de la "
            "estructura de transacción tradicional. Esto solucionó la maleabilidad, "
            "redujo las tarifas para transacciones SegWit y habilitó la Red Lightning. "
            "Las direcciones SegWit nativas comienzan con bc1q."
        ),
        "category": "protocol",
        "related_terms": ["bip", "witness", "vbyte", "p2wpkh", "p2wsh", "taproot"],
        "difficulty": "intermediate",
        "example_en": "Always use native SegWit (bc1q) addresses for lower fees.",
        "example_es": "Siempre usa direcciones SegWit nativas (bc1q) para tarifas más bajas.",
    },
    "taproot": {
        "term": "Taproot",
        "term_es": "Taproot",
        "definition_en": (
            "Taproot (BIPs 340-342) is a Bitcoin protocol upgrade activated in November "
            "2021 that introduces Schnorr signatures, MAST (Merklized Abstract Syntax "
            "Trees), and Tapscript. It improves privacy by making complex multi-party "
            "contracts look like single-key spends on-chain, and improves efficiency. "
            "Taproot addresses start with bc1p."
        ),
        "definition_es": (
            "Taproot (BIPs 340-342) es una actualización de protocolo Bitcoin activada "
            "en noviembre de 2021 que introduce firmas Schnorr, MAST y Tapscript. "
            "Mejora la privacidad haciendo que contratos complejos de múltiples partes "
            "parezcan gastos de clave única en cadena. Las direcciones Taproot "
            "comienzan con bc1p."
        ),
        "category": "protocol",
        "related_terms": ["bip", "schnorr", "segwit", "p2tr", "multisig"],
        "difficulty": "advanced",
        "example_en": "Taproot makes a 2-of-3 multisig look indistinguishable from a single-sig on-chain.",
        "example_es": "Taproot hace que un multisig 2-de-3 sea indistinguible de una firma única en cadena.",
    },
    "schnorr": {
        "term": "Schnorr Signatures",
        "term_es": "Firmas Schnorr",
        "definition_en": (
            "Schnorr signatures (BIP340) are a digital signature scheme that replaced "
            "ECDSA for Taproot key-path spends in Bitcoin. They offer linear key "
            "aggregation (multiple parties can produce a single aggregated signature), "
            "are batch-verifiable (speeding up initial block download), and are "
            "more compact than ECDSA signatures."
        ),
        "definition_es": (
            "Las firmas Schnorr (BIP340) son un esquema de firma digital que reemplazó "
            "a ECDSA para los gastos de ruta de clave en Taproot. Ofrecen agregación "
            "de claves lineal (múltiples partes pueden producir una sola firma "
            "agregada), son verificables en lote y son más compactas que las "
            "firmas ECDSA."
        ),
        "category": "protocol",
        "related_terms": ["taproot", "ecdsa", "bip", "multisig"],
        "difficulty": "advanced",
        "example_en": "Schnorr enables MuSig2 for efficient n-of-n key aggregation.",
        "example_es": "Schnorr permite MuSig2 para agregación eficiente de claves n-de-n.",
    },
    "ecdsa": {
        "term": "ECDSA (Elliptic Curve Digital Signature Algorithm)",
        "term_es": "ECDSA (Algoritmo de Firma Digital de Curva Elíptica)",
        "definition_en": (
            "ECDSA is the digital signature algorithm used in Bitcoin prior to Taproot. "
            "It operates over the secp256k1 elliptic curve. A private key generates a "
            "public key and can produce signatures that prove ownership without "
            "revealing the private key. ECDSA is used for P2PKH, P2SH, P2WPKH, "
            "and P2WSH outputs."
        ),
        "definition_es": (
            "ECDSA es el algoritmo de firma digital usado en Bitcoin antes de Taproot. "
            "Opera sobre la curva elíptica secp256k1. Una clave privada genera una "
            "clave pública y puede producir firmas que prueban la propiedad sin revelar "
            "la clave privada. ECDSA se usa para salidas P2PKH, P2SH, P2WPKH y P2WSH."
        ),
        "category": "security",
        "related_terms": ["schnorr", "pubkey", "script", "taproot"],
        "difficulty": "advanced",
        "example_en": "Each Bitcoin transaction input contains an ECDSA signature proving ownership.",
        "example_es": "Cada entrada de transacción Bitcoin contiene una firma ECDSA que prueba la propiedad.",
    },
    "script": {
        "term": "Bitcoin Script",
        "term_es": "Script de Bitcoin",
        "definition_en": (
            "Bitcoin Script is the stack-based, Turing-incomplete scripting language "
            "used to define spending conditions for transaction outputs. Common script "
            "types include P2PKH, P2SH, P2WPKH, P2WSH, and P2TR. Script intentionally "
            "lacks loops to prevent denial-of-service attacks and ensure deterministic "
            "execution time."
        ),
        "definition_es": (
            "Bitcoin Script es el lenguaje de scripting basado en pila e "
            "intencionalmente no Turing-completo usado para definir las condiciones "
            "de gasto de las salidas de transacción. Los tipos comunes incluyen P2PKH, "
            "P2SH, P2WPKH, P2WSH y P2TR. Script carece intencionalmente de bucles "
            "para prevenir ataques DoS."
        ),
        "category": "protocol",
        "related_terms": ["p2pkh", "p2sh", "p2wpkh", "p2wsh", "p2tr", "multisig", "op_return"],
        "difficulty": "advanced",
        "example_en": "A 2-of-3 multisig is encoded as a P2SH or P2WSH script.",
        "example_es": "Un multisig 2-de-3 se codifica como un script P2SH o P2WSH.",
    },
    "psbt": {
        "term": "PSBT (Partially Signed Bitcoin Transaction)",
        "term_es": "PSBT (Transacción Bitcoin Parcialmente Firmada)",
        "definition_en": (
            "A Partially Signed Bitcoin Transaction (BIP174) is a portable format for "
            "sharing unsigned or partially-signed transactions between signers or "
            "between a wallet and a hardware signing device. PSBTs are essential for "
            "hardware wallet workflows and multi-party signing protocols like multisig "
            "and MuSig2."
        ),
        "definition_es": (
            "Una Transacción Bitcoin Parcialmente Firmada (BIP174) es un formato "
            "portable para compartir transacciones sin firmar o parcialmente firmadas "
            "entre firmantes o entre una billetera y un dispositivo de firma hardware. "
            "Los PSBTs son esenciales para flujos de trabajo con hardware wallets y "
            "protocolos de firma multiparte."
        ),
        "category": "wallet",
        "related_terms": ["multisig", "hd_wallet", "bip", "transaction"],
        "difficulty": "advanced",
        "example_en": "Export a PSBT from your hot wallet and sign it on your hardware device.",
        "example_es": "Exporta un PSBT de tu billetera caliente y fírmalo en tu dispositivo hardware.",
    },
    # -----------------------------------------------------------------------
    # A D D R E S S   T Y P E S
    # -----------------------------------------------------------------------
    "p2pkh": {
        "term": "P2PKH (Pay to Public Key Hash)",
        "term_es": "P2PKH (Pagar al Hash de Clave Pública)",
        "definition_en": (
            "P2PKH is the original Bitcoin address format (legacy), where an output "
            "is locked to the hash of a public key. Addresses begin with '1'. "
            "Spending requires providing the public key and a valid ECDSA signature. "
            "P2PKH transactions are larger and more expensive than native SegWit "
            "alternatives."
        ),
        "definition_es": (
            "P2PKH es el formato de dirección Bitcoin original (legacy), donde una "
            "salida está bloqueada al hash de una clave pública. Las direcciones "
            "comienzan con '1'. Gastar requiere proporcionar la clave pública y una "
            "firma ECDSA válida. Las transacciones P2PKH son más grandes y costosas "
            "que las alternativas SegWit nativas."
        ),
        "category": "transactions",
        "related_terms": ["address", "script", "ecdsa", "pubkey"],
        "difficulty": "intermediate",
        "example_en": "Legacy Bitcoin addresses starting with '1' use the P2PKH format.",
        "example_es": "Las direcciones Bitcoin legacy que comienzan con '1' usan el formato P2PKH.",
    },
    "p2sh": {
        "term": "P2SH (Pay to Script Hash)",
        "term_es": "P2SH (Pagar al Hash de Script)",
        "definition_en": (
            "P2SH (BIP16) allows the locking script to be any arbitrary script whose "
            "hash is published on-chain. The spending party must reveal the full script "
            "and provide the required signatures. P2SH addresses begin with '3'. It "
            "enabled multisig wallets and was later extended to P2SH-wrapped SegWit."
        ),
        "definition_es": (
            "P2SH (BIP16) permite que el script de bloqueo sea cualquier script "
            "arbitrario cuyo hash se publica en cadena. La parte que gasta debe revelar "
            "el script completo y proporcionar las firmas requeridas. Las direcciones "
            "P2SH comienzan con '3'. Habilitó las billeteras multisig."
        ),
        "category": "transactions",
        "related_terms": ["address", "script", "multisig", "p2pkh", "p2wpkh"],
        "difficulty": "intermediate",
        "example_en": "Many multisig wallets use P2SH addresses starting with '3'.",
        "example_es": "Muchas billeteras multisig usan direcciones P2SH que comienzan con '3'.",
    },
    "p2wpkh": {
        "term": "P2WPKH (Pay to Witness Public Key Hash)",
        "term_es": "P2WPKH (Pagar al Hash de Clave Pública Witness)",
        "definition_en": (
            "P2WPKH is the native SegWit address format for single-key outputs, "
            "encoded as Bech32 (BIP173) with the 'bc1q' prefix. It moves signature "
            "data into the witness field, reducing transaction weight and fees. "
            "It is the most widely supported modern Bitcoin address type."
        ),
        "definition_es": (
            "P2WPKH es el formato de dirección SegWit nativa para salidas de clave "
            "única, codificado como Bech32 (BIP173) con el prefijo 'bc1q'. Mueve "
            "los datos de firma al campo witness, reduciendo el peso y las tarifas. "
            "Es el tipo de dirección Bitcoin moderna más ampliamente soportado."
        ),
        "category": "transactions",
        "related_terms": ["segwit", "address", "vbyte", "witness", "p2pkh"],
        "difficulty": "intermediate",
        "example_en": "Use bc1q addresses for the best combination of cost and compatibility.",
        "example_es": "Usa direcciones bc1q para la mejor combinación de costo y compatibilidad.",
    },
    "p2wsh": {
        "term": "P2WSH (Pay to Witness Script Hash)",
        "term_es": "P2WSH (Pagar al Hash de Script Witness)",
        "definition_en": (
            "P2WSH is the native SegWit equivalent of P2SH for complex scripts such "
            "as multisig. It also uses a Bech32 'bc1q' prefix but with a 32-byte "
            "script hash (compared to 20 bytes for P2WPKH). Lightning Network channel "
            "funding outputs use P2WSH."
        ),
        "definition_es": (
            "P2WSH es el equivalente SegWit nativo de P2SH para scripts complejos "
            "como multisig. También usa el prefijo Bech32 'bc1q' pero con un hash de "
            "script de 32 bytes (en comparación con 20 bytes para P2WPKH). Las salidas "
            "de financiamiento de canales de la Red Lightning usan P2WSH."
        ),
        "category": "transactions",
        "related_terms": ["segwit", "p2sh", "multisig", "lightning", "witness"],
        "difficulty": "advanced",
        "example_en": "Lightning funding transactions are P2WSH 2-of-2 multisig outputs.",
        "example_es": "Las transacciones de financiamiento Lightning son salidas P2WSH multisig 2-de-2.",
    },
    "p2tr": {
        "term": "P2TR (Pay to Taproot)",
        "term_es": "P2TR (Pagar a Taproot)",
        "definition_en": (
            "P2TR is the Taproot address format introduced by BIP341, using Bech32m "
            "encoding with the 'bc1p' prefix. Outputs can be spent via a key path "
            "(Schnorr signature) or a script path (revealing a Merklized script). "
            "Key-path spending makes complex contracts look identical to simple "
            "single-key transactions, enhancing privacy."
        ),
        "definition_es": (
            "P2TR es el formato de dirección Taproot introducido por BIP341, usando "
            "codificación Bech32m con el prefijo 'bc1p'. Las salidas pueden gastarse "
            "mediante ruta de clave (firma Schnorr) o ruta de script. El gasto por "
            "ruta de clave hace que contratos complejos parezcan idénticos a "
            "transacciones simples de clave única."
        ),
        "category": "transactions",
        "related_terms": ["taproot", "schnorr", "address", "segwit", "p2wpkh"],
        "difficulty": "advanced",
        "example_en": "Taproot (bc1p) addresses enable the most private and flexible Bitcoin spending.",
        "example_es": "Las direcciones Taproot (bc1p) habilitan el gasto Bitcoin más privado y flexible.",
    },
    # -----------------------------------------------------------------------
    # W A L L E T
    # -----------------------------------------------------------------------
    "wallet": {
        "term": "Bitcoin Wallet",
        "term_es": "Billetera Bitcoin",
        "definition_en": (
            "A Bitcoin wallet is software or hardware that manages private keys and "
            "facilitates creating and signing transactions. It does not 'store' "
            "Bitcoin — the coins exist on the blockchain; the wallet stores the keys "
            "that prove ownership. Wallets range from hot (online) to cold (offline)."
        ),
        "definition_es": (
            "Una billetera Bitcoin es software o hardware que gestiona claves privadas "
            "y facilita la creación y firma de transacciones. No 'almacena' Bitcoin — "
            "las monedas existen en la cadena de bloques; la billetera almacena las "
            "claves que prueban la propiedad. Las billeteras van desde calientes "
            "(en línea) hasta frías (sin conexión)."
        ),
        "category": "wallet",
        "related_terms": ["hd_wallet", "seed", "cold_storage", "custodial", "xpub"],
        "difficulty": "beginner",
        "example_en": "Your wallet's seed phrase is the master key to all your Bitcoin.",
        "example_es": "La frase semilla de tu billetera es la clave maestra de todo tu Bitcoin.",
    },
    "hd_wallet": {
        "term": "HD Wallet (Hierarchical Deterministic Wallet)",
        "term_es": "Billetera HD (Determinista Jerárquica)",
        "definition_en": (
            "A Hierarchical Deterministic wallet (BIP32) derives all key pairs from a "
            "single master seed using a tree structure. Any number of child keys can "
            "be generated deterministically from the seed, allowing full wallet recovery "
            "from a single mnemonic. Account-level extended public keys (xpubs) allow "
            "watch-only wallets without exposing private keys."
        ),
        "definition_es": (
            "Una billetera Determinista Jerárquica (BIP32) deriva todos los pares de "
            "claves de una sola semilla maestra usando una estructura de árbol. "
            "Cualquier número de claves hijas puede generarse deterministamente desde "
            "la semilla, permitiendo la recuperación completa de la billetera desde un "
            "solo mnemónico."
        ),
        "category": "wallet",
        "related_terms": ["seed", "xpub", "bip", "wallet", "cold_storage"],
        "difficulty": "intermediate",
        "example_en": "Most modern Bitcoin wallets are HD wallets derived from a 12 or 24-word seed.",
        "example_es": "La mayoría de billeteras Bitcoin modernas son HD, derivadas de una semilla de 12 o 24 palabras.",
    },
    "seed": {
        "term": "Seed Phrase (Mnemonic)",
        "term_es": "Frase Semilla (Mnemónico)",
        "definition_en": (
            "A seed phrase (BIP39) is a human-readable representation of an HD wallet's "
            "root entropy, typically 12 or 24 words from a standardized wordlist. "
            "The seed phrase is the ultimate backup — anyone who has it can derive "
            "all private keys in the wallet. It must be stored offline and securely, "
            "never digitally."
        ),
        "definition_es": (
            "Una frase semilla (BIP39) es una representación legible por humanos de "
            "la entropía raíz de una billetera HD, típicamente 12 o 24 palabras de "
            "una lista estandarizada. La frase semilla es el respaldo definitivo — "
            "quien la tenga puede derivar todas las claves privadas. Debe almacenarse "
            "sin conexión y de forma segura, nunca digitalmente."
        ),
        "category": "wallet",
        "related_terms": ["hd_wallet", "wallet", "cold_storage", "security"],
        "difficulty": "beginner",
        "example_en": "Write your seed phrase on paper and store it in a fireproof safe.",
        "example_es": "Escribe tu frase semilla en papel y guárdala en una caja fuerte ignífuga.",
    },
    "cold_storage": {
        "term": "Cold Storage",
        "term_es": "Almacenamiento en Frío",
        "definition_en": (
            "Cold storage refers to keeping Bitcoin private keys on a device or medium "
            "that is completely offline and never connected to the internet. Common "
            "cold storage methods include hardware wallets, air-gapped computers, and "
            "metal seed phrase backups. Cold storage is the gold standard for securing "
            "significant Bitcoin holdings."
        ),
        "definition_es": (
            "El almacenamiento en frío se refiere a mantener las claves privadas de "
            "Bitcoin en un dispositivo o medio completamente sin conexión y nunca "
            "conectado a internet. Los métodos comunes incluyen hardware wallets, "
            "computadoras con air-gap y respaldos de frases semilla en metal. "
            "Es el estándar de oro para asegurar holdings significativos de Bitcoin."
        ),
        "category": "security",
        "related_terms": ["wallet", "seed", "hd_wallet", "custodial"],
        "difficulty": "beginner",
        "example_en": "For long-term savings, move Bitcoin off exchanges into cold storage.",
        "example_es": "Para ahorros a largo plazo, mueve Bitcoin fuera de exchanges al almacenamiento en frío.",
    },
    "custodial": {
        "term": "Custodial Wallet",
        "term_es": "Billetera Custodial",
        "definition_en": (
            "A custodial wallet is one where a third party holds the private keys on "
            "behalf of the user. The user has an account with the custodian but does "
            "not control the underlying Bitcoin. Exchange wallets are custodial. "
            "'Not your keys, not your coins' expresses the Bitcoin community's view "
            "that self-custody is preferable."
        ),
        "definition_es": (
            "Una billetera custodial es aquella donde un tercero mantiene las claves "
            "privadas en nombre del usuario. El usuario tiene una cuenta con el "
            "custodio pero no controla el Bitcoin subyacente. Las billeteras de "
            "exchange son custodiales. 'Sin tus claves, no son tus monedas' expresa "
            "la preferencia Bitcoin por la autocustodia."
        ),
        "category": "security",
        "related_terms": ["wallet", "cold_storage", "seed", "self_custody"],
        "difficulty": "beginner",
        "example_en": "Withdraw Bitcoin from custodial exchanges to your own self-custody wallet.",
        "example_es": "Retira Bitcoin de exchanges custodiales a tu propia billetera de autocustodia.",
    },
    "xpub": {
        "term": "xpub (Extended Public Key)",
        "term_es": "xpub (Clave Pública Extendida)",
        "definition_en": (
            "An extended public key (xpub) encodes a public key and a chain code, "
            "allowing the derivation of all child public keys in a BIP32 branch without "
            "knowing the corresponding private keys. Sharing an xpub with a watch-only "
            "wallet allows monitoring of all derived addresses while keeping the "
            "private keys in cold storage."
        ),
        "definition_es": (
            "Una clave pública extendida (xpub) codifica una clave pública y un código "
            "de cadena, permitiendo derivar todas las claves públicas hijas en una "
            "rama BIP32 sin conocer las claves privadas correspondientes. Compartir un "
            "xpub con una billetera solo-lectura permite monitorear todas las "
            "direcciones derivadas mientras las claves privadas permanecen en frío."
        ),
        "category": "wallet",
        "related_terms": ["hd_wallet", "bip", "cold_storage", "pubkey"],
        "difficulty": "advanced",
        "example_en": "Share your xpub with a companion app to track balances without risk.",
        "example_es": "Comparte tu xpub con una app complementaria para rastrear saldos sin riesgo.",
    },
    "pubkey": {
        "term": "Public Key",
        "term_es": "Clave Pública",
        "definition_en": (
            "A public key in Bitcoin is a point on the secp256k1 elliptic curve derived "
            "from the private key by scalar multiplication of the generator point. "
            "It is used to derive addresses (via hashing) and to verify signatures. "
            "Public keys can be safely shared; the private key cannot be derived from "
            "a public key."
        ),
        "definition_es": (
            "Una clave pública en Bitcoin es un punto en la curva elíptica secp256k1 "
            "derivado de la clave privada mediante multiplicación escalar del punto "
            "generador. Se usa para derivar direcciones (mediante hashing) y para "
            "verificar firmas. Las claves públicas pueden compartirse de forma segura; "
            "la clave privada no puede derivarse de una pública."
        ),
        "category": "security",
        "related_terms": ["ecdsa", "schnorr", "address", "xpub"],
        "difficulty": "advanced",
        "example_en": "A compressed public key is 33 bytes on the secp256k1 curve.",
        "example_es": "Una clave pública comprimida mide 33 bytes en la curva secp256k1.",
    },
    "multisig": {
        "term": "Multisig (Multi-signature)",
        "term_es": "Multifirma",
        "definition_en": (
            "Multisig is a Bitcoin spending policy requiring M-of-N signatures to "
            "authorize a transaction (e.g., 2-of-3 means any 2 of 3 keys can sign). "
            "It distributes trust and eliminates single points of failure. Common "
            "implementations include collaborative custody services, corporate treasury "
            "management, and high-security personal savings vaults."
        ),
        "definition_es": (
            "Multifirma es una política de gasto Bitcoin que requiere M-de-N firmas "
            "para autorizar una transacción (p.ej., 2-de-3 significa que cualquier "
            "2 de 3 claves pueden firmar). Distribuye la confianza y elimina puntos "
            "únicos de fallo. Las implementaciones comunes incluyen servicios de "
            "custodia colaborativa y gestión de tesorería corporativa."
        ),
        "category": "security",
        "related_terms": ["wallet", "psbt", "taproot", "schnorr", "p2sh", "p2wsh"],
        "difficulty": "intermediate",
        "example_en": "A 2-of-3 multisig requires any two of your three hardware wallets to sign.",
        "example_es": "Un multisig 2-de-3 requiere que dos de tus tres hardware wallets firmen.",
    },
    "witness": {
        "term": "Witness Data",
        "term_es": "Datos Witness",
        "definition_en": (
            "Witness data is the part of a SegWit transaction that contains signatures "
            "and scripts needed to satisfy the spending conditions of SegWit inputs. "
            "It is serialized separately from the main transaction body and benefits "
            "from a 75% weight discount relative to non-witness data, reducing "
            "effective transaction fees."
        ),
        "definition_es": (
            "Los datos witness son la parte de una transacción SegWit que contiene "
            "firmas y scripts necesarios para satisfacer las condiciones de gasto de "
            "las entradas SegWit. Se serializa por separado del cuerpo principal de "
            "la transacción y se beneficia de un descuento del 75% en peso en "
            "comparación con los datos no-witness."
        ),
        "category": "protocol",
        "related_terms": ["segwit", "vbyte", "p2wpkh", "p2wsh", "p2tr"],
        "difficulty": "advanced",
        "example_en": "Witness data costs 1 weight unit per byte instead of 4.",
        "example_es": "Los datos witness cuestan 1 unidad de peso por byte en lugar de 4.",
    },
    # -----------------------------------------------------------------------
    # P R I V A C Y
    # -----------------------------------------------------------------------
    "coin_control": {
        "term": "Coin Control",
        "term_es": "Control de Monedas",
        "definition_en": (
            "Coin control is the wallet feature that allows users to manually select "
            "which UTXOs to use as inputs in a transaction. By choosing specific coins, "
            "users can avoid linking addresses, consolidate dust, or optimize fees. "
            "It is an important privacy tool that prevents wallets from automatically "
            "merging coins from different sources."
        ),
        "definition_es": (
            "El control de monedas es la función de la billetera que permite a los "
            "usuarios seleccionar manualmente qué UTXOs usar como entradas en una "
            "transacción. Al elegir monedas específicas, los usuarios pueden evitar "
            "vincular direcciones, consolidar polvo u optimizar tarifas. Es una "
            "herramienta de privacidad importante."
        ),
        "category": "privacy",
        "related_terms": ["utxo", "transaction", "privacy"],
        "difficulty": "advanced",
        "example_en": "Use coin control to avoid merging UTXOs from your exchange and your node.",
        "example_es": "Usa el control de monedas para evitar mezclar UTXOs de tu exchange y tu nodo.",
    },
    "coinjoin": {
        "term": "CoinJoin",
        "term_es": "CoinJoin",
        "definition_en": (
            "CoinJoin is a trustless method for combining multiple Bitcoin payments "
            "from multiple spenders into a single transaction. This breaks the common "
            "blockchain analysis assumption that all inputs in a transaction belong to "
            "the same owner, improving privacy. Implementations include Whirlpool, "
            "JoinMarket, and Wasabi Wallet's CoinJoin."
        ),
        "definition_es": (
            "CoinJoin es un método sin confianza para combinar múltiples pagos Bitcoin "
            "de múltiples gastadores en una sola transacción. Esto rompe la suposición "
            "común del análisis blockchain de que todas las entradas pertenecen al "
            "mismo dueño, mejorando la privacidad."
        ),
        "category": "privacy",
        "related_terms": ["coin_control", "utxo", "transaction", "privacy"],
        "difficulty": "advanced",
        "example_en": "CoinJoin breaks the common-input-ownership heuristic used by chain analysis firms.",
        "example_es": "CoinJoin rompe la heurística de propiedad común de entradas usada por firmas de análisis de cadena.",
    },
    "lightning_privacy": {
        "term": "Lightning Privacy",
        "term_es": "Privacidad en Lightning",
        "definition_en": (
            "Lightning payments are inherently more private than on-chain Bitcoin "
            "transactions because payment details are not recorded on the public "
            "blockchain. Onion routing (based on Sphinx) hides payment path details "
            "from intermediate nodes. However, channel graph analysis can still reveal "
            "some information about payment relationships."
        ),
        "definition_es": (
            "Los pagos Lightning son inherentemente más privados que las transacciones "
            "Bitcoin en cadena porque los detalles del pago no se registran en la "
            "blockchain pública. El enrutamiento cebolla oculta los detalles de la "
            "ruta de pago de los nodos intermedios. Sin embargo, el análisis del "
            "gráfico de canales aún puede revelar información."
        ),
        "category": "privacy",
        "related_terms": ["lightning", "channel", "htlc"],
        "difficulty": "advanced",
        "example_en": "Lightning payments leave no public record of sender, receiver, or amount.",
        "example_es": "Los pagos Lightning no dejan registro público de remitente, receptor ni monto.",
    },
    # -----------------------------------------------------------------------
    # S E C U R I T Y
    # -----------------------------------------------------------------------
    "self_custody": {
        "term": "Self-Custody",
        "term_es": "Autocustodia",
        "definition_en": (
            "Self-custody means controlling your own Bitcoin private keys without "
            "relying on a third party. It is the Bitcoiner ideal — 'not your keys, "
            "not your coins'. Self-custody requires responsibility: protecting your "
            "seed phrase, securing devices, and understanding recovery procedures. "
            "It eliminates counterparty risk from exchanges and custodians."
        ),
        "definition_es": (
            "La autocustodia significa controlar tus propias claves privadas de Bitcoin "
            "sin depender de un tercero. Es el ideal Bitcoiner — 'sin tus claves, no "
            "son tus monedas'. La autocustodia requiere responsabilidad: proteger tu "
            "frase semilla, asegurar dispositivos y comprender los procedimientos de "
            "recuperación. Elimina el riesgo de contraparte."
        ),
        "category": "security",
        "related_terms": ["custodial", "cold_storage", "wallet", "seed"],
        "difficulty": "beginner",
        "example_en": "Self-custody means no company can freeze or confiscate your Bitcoin.",
        "example_es": "La autocustodia significa que ninguna empresa puede congelar o confiscar tu Bitcoin.",
    },
    "node": {
        "term": "Bitcoin Node",
        "term_es": "Nodo Bitcoin",
        "definition_en": (
            "A Bitcoin node is software that participates in the Bitcoin peer-to-peer "
            "network. A full node downloads and independently validates every block "
            "and transaction since the genesis block, enforcing all consensus rules "
            "without trusting any third party. Running your own node is the ultimate "
            "expression of Bitcoin sovereignty."
        ),
        "definition_es": (
            "Un nodo Bitcoin es software que participa en la red Bitcoin entre pares. "
            "Un nodo completo descarga y valida independientemente cada bloque y "
            "transacción desde el bloque génesis, haciendo cumplir todas las reglas "
            "de consenso sin confiar en ningún tercero. Ejecutar tu propio nodo es "
            "la expresión definitiva de la soberanía Bitcoin."
        ),
        "category": "protocol",
        "related_terms": ["blockchain", "mining", "lightning", "self_custody"],
        "difficulty": "intermediate",
        "example_en": "Run your own Bitcoin node to verify transactions without trusting anyone.",
        "example_es": "Ejecuta tu propio nodo Bitcoin para verificar transacciones sin confiar en nadie.",
    },
    "merkle_tree": {
        "term": "Merkle Tree",
        "term_es": "Árbol de Merkle",
        "definition_en": (
            "A Merkle tree is a binary hash tree where each leaf is the hash of a "
            "transaction and each parent node is the hash of its two children. The "
            "Merkle root, stored in a block header, cryptographically commits to all "
            "transactions in the block. A Merkle proof can verify a transaction's "
            "inclusion with O(log n) hashes — enabling lightweight SPV clients."
        ),
        "definition_es": (
            "Un árbol de Merkle es un árbol de hash binario donde cada hoja es el "
            "hash de una transacción y cada nodo padre es el hash de sus dos hijos. "
            "La raíz Merkle, almacenada en la cabecera del bloque, compromete "
            "criptográficamente todas las transacciones. Una prueba Merkle puede "
            "verificar la inclusión de una transacción con O(log n) hashes."
        ),
        "category": "protocol",
        "related_terms": ["block", "transaction", "node"],
        "difficulty": "advanced",
        "example_en": "SPV wallets use Merkle proofs to verify payments without downloading full blocks.",
        "example_es": "Las billeteras SPV usan pruebas Merkle para verificar pagos sin descargar bloques completos.",
    },
    "zap": {
        "term": "Zap",
        "term_es": "Zap",
        "definition_en": (
            "In the Bitcoin and Nostr ecosystem, a 'zap' is a Lightning Network payment "
            "attached to a social interaction (post, comment, like) on a Nostr client. "
            "Zaps are standardized by NIP-57. They allow direct, censorship-resistant "
            "value transfer between content creators and their audience using "
            "Lightning invoices."
        ),
        "definition_es": (
            "En el ecosistema Bitcoin y Nostr, un 'zap' es un pago de la Red Lightning "
            "adjunto a una interacción social (publicación, comentario, like) en un "
            "cliente Nostr. Los zaps están estandarizados por NIP-57. Permiten "
            "transferencia directa y resistente a la censura de valor entre creadores "
            "de contenido y su audiencia."
        ),
        "category": "lightning",
        "related_terms": ["lightning", "invoice", "nostr"],
        "difficulty": "beginner",
        "example_en": "Zap your favorite Bitcoiner's post with 1,000 sats of appreciation.",
        "example_es": "Hazle un zap de 1,000 sats a la publicación de tu Bitcoiner favorito.",
    },
    "nostr": {
        "term": "Nostr",
        "term_es": "Nostr",
        "definition_en": (
            "Nostr (Notes and Other Stuff Transmitted by Relays) is a simple, open, "
            "censorship-resistant protocol for decentralized social networking. Each "
            "user has a keypair (secp256k1, same curve as Bitcoin). Nostr clients "
            "connect to relays to publish and receive signed notes. NIP-57 specifies "
            "Lightning zaps for in-protocol tipping."
        ),
        "definition_es": (
            "Nostr (Notas y Otras Cosas Transmitidas por Relés) es un protocolo "
            "simple, abierto y resistente a la censura para redes sociales "
            "descentralizadas. Cada usuario tiene un par de claves (secp256k1, la "
            "misma curva que Bitcoin). Los clientes Nostr se conectan a relés para "
            "publicar y recibir notas firmadas."
        ),
        "category": "protocol",
        "related_terms": ["zap", "lightning", "pubkey"],
        "difficulty": "intermediate",
        "example_en": "Your Nostr public key (npub) is used to identify you across all clients.",
        "example_es": "Tu clave pública Nostr (npub) se usa para identificarte en todos los clientes.",
    },
    "on_chain": {
        "term": "On-chain",
        "term_es": "En cadena",
        "definition_en": (
            "On-chain refers to transactions and data that are recorded directly on "
            "the Bitcoin blockchain. On-chain transactions require mining fees, take "
            "approximately 10-60 minutes to confirm with good security, and are "
            "permanently visible on the public ledger. Contrast with Lightning "
            "Network payments, which are off-chain."
        ),
        "definition_es": (
            "En cadena se refiere a transacciones y datos registrados directamente en "
            "la blockchain de Bitcoin. Las transacciones en cadena requieren tarifas "
            "de minería, tardan aproximadamente 10-60 minutos en confirmarse con buena "
            "seguridad y son permanentemente visibles en el libro mayor público. "
            "Contrasta con los pagos de Lightning, que son fuera de cadena."
        ),
        "category": "basics",
        "related_terms": ["transaction", "blockchain", "lightning", "fee_rate"],
        "difficulty": "beginner",
        "example_en": "For large amounts, an on-chain transaction with 6 confirmations is safest.",
        "example_es": "Para grandes cantidades, una transacción en cadena con 6 confirmaciones es lo más seguro.",
    },
    "scarcity": {
        "term": "Scarcity",
        "term_es": "Escasez",
        "definition_en": (
            "Bitcoin has a fixed maximum supply of 21 million coins, enforced by "
            "consensus rules. New Bitcoin is issued only through the mining block "
            "subsidy, which halves approximately every 4 years. This absolute digital "
            "scarcity — unprecedented in monetary history — is the foundation of "
            "Bitcoin's sound money properties."
        ),
        "definition_es": (
            "Bitcoin tiene un suministro máximo fijo de 21 millones de monedas, "
            "aplicado por las reglas de consenso. El nuevo Bitcoin se emite solo a "
            "través del subsidio de bloque minero, que se reduce a la mitad "
            "aproximadamente cada 4 años. Esta escasez digital absoluta — sin "
            "precedentes en la historia monetaria — es la base de las propiedades "
            "de dinero sólido de Bitcoin."
        ),
        "category": "basics",
        "related_terms": ["halving", "mining", "bitcoin"],
        "difficulty": "beginner",
        "example_en": "Only 21 million Bitcoin will ever exist — scarcity is enforced by code.",
        "example_es": "Solo existirán 21 millones de Bitcoin — la escasez está aplicada por código.",
    },
    "subsidy": {
        "term": "Block Subsidy",
        "term_es": "Subsidio de Bloque",
        "definition_en": (
            "The block subsidy is the amount of newly created Bitcoin awarded to the "
            "miner who successfully mines a block. It started at 50 BTC and halves "
            "every 210,000 blocks. After approximately 2140, the subsidy will reach "
            "zero and miners will be compensated solely by transaction fees. The "
            "subsidy is distinct from the total block reward (subsidy + fees)."
        ),
        "definition_es": (
            "El subsidio de bloque es la cantidad de Bitcoin recién creado otorgada "
            "al minero que extrae exitosamente un bloque. Comenzó en 50 BTC y se "
            "reduce a la mitad cada 210,000 bloques. Aproximadamente en 2140, el "
            "subsidio llegará a cero y los mineros serán compensados solo por tarifas. "
            "El subsidio es distinto de la recompensa total del bloque."
        ),
        "category": "mining",
        "related_terms": ["halving", "mining", "fee_rate", "scarcity"],
        "difficulty": "intermediate",
        "example_en": "After the 2024 halving the block subsidy is 3.125 BTC per block.",
        "example_es": "Tras el halving de 2024, el subsidio de bloque es 3.125 BTC por bloque.",
    },
    "remittance": {
        "term": "Bitcoin Remittance",
        "term_es": "Remesas Bitcoin",
        "definition_en": (
            "Bitcoin remittances use the Lightning Network or on-chain transactions "
            "to send value internationally with minimal fees and no intermediaries. "
            "For countries like El Salvador — where a large portion of GDP comes from "
            "remittances — Bitcoin offers dramatically lower costs compared to "
            "traditional wire transfer services that charge 5-10% fees."
        ),
        "definition_es": (
            "Las remesas Bitcoin usan la Red Lightning o transacciones en cadena para "
            "enviar valor internacionalmente con tarifas mínimas y sin intermediarios. "
            "Para países como El Salvador — donde una gran parte del PIB proviene de "
            "remesas — Bitcoin ofrece costos dramáticamente menores comparados con "
            "los servicios tradicionales de transferencia que cobran 5-10%."
        ),
        "category": "basics",
        "related_terms": ["lightning", "invoice", "on_chain", "bitcoin"],
        "difficulty": "beginner",
        "example_en": "Send a remittance from the US to El Salvador instantly via Lightning.",
        "example_es": "Envía una remesa desde EE.UU. a El Salvador instantáneamente vía Lightning.",
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def search_glossary(query: str, locale: str = "en") -> list[dict]:
    """Search the glossary for terms matching *query*.

    Searches term name, definition, and related terms.  Returns a list
    of matching entry dicts, enriched with a ``key`` field.  Case-
    insensitive.  Locale selects which definition field to search first.

    Parameters
    ----------
    query:  Search string (partial match, case-insensitive).
    locale: "en" or "es" — prefers the corresponding field.

    Returns
    -------
    List of matching glossary entries (each dict has key + all fields).
    """
    query_lower = query.strip().lower()
    if not query_lower:
        return []

    results = []
    for key, entry in GLOSSARY.items():
        # Build a searchable text blob for this entry
        term_en = entry.get("term", "").lower()
        term_es = entry.get("term_es", "").lower()
        def_en = entry.get("definition_en", "").lower()
        def_es = entry.get("definition_es", "").lower()
        related = " ".join(entry.get("related_terms", [])).lower()
        example_en = entry.get("example_en", "").lower()
        example_es = entry.get("example_es", "").lower()

        if locale == "es":
            blob = f"{term_es} {term_en} {def_es} {def_en} {related} {example_es}"
        else:
            blob = f"{term_en} {term_es} {def_en} {def_es} {related} {example_en}"

        if query_lower in blob:
            results.append({"key": key, **entry})

    return results


def get_by_category(category: str) -> list[dict]:
    """Return all glossary entries in *category*.

    Parameters
    ----------
    category: One of CATEGORIES (case-insensitive).

    Returns
    -------
    List of matching glossary entries with their key included.

    Raises
    ------
    ValueError: If *category* is not recognised.
    """
    category_lower = category.strip().lower()
    if category_lower not in CATEGORIES:
        raise ValueError(
            f"Unknown category '{category}'. Valid categories: {sorted(CATEGORIES)}"
        )
    return [
        {"key": k, **v}
        for k, v in GLOSSARY.items()
        if v.get("category") == category_lower
    ]


def get_by_difficulty(level: str) -> list[dict]:
    """Return all glossary entries at difficulty *level*.

    Parameters
    ----------
    level: "beginner", "intermediate", or "advanced" (case-insensitive).

    Returns
    -------
    List of matching glossary entries with their key included.

    Raises
    ------
    ValueError: If *level* is not recognised.
    """
    level_lower = level.strip().lower()
    if level_lower not in DIFFICULTY_LEVELS:
        raise ValueError(
            f"Unknown difficulty '{level}'. Valid levels: {DIFFICULTY_LEVELS}"
        )
    return [
        {"key": k, **v}
        for k, v in GLOSSARY.items()
        if v.get("difficulty") == level_lower
    ]
