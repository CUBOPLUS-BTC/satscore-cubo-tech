/** Magma Miner — Simple Bitcoin quiz questions for the revive mechanic */

export interface QuizQuestion {
	question: { en: string; es: string };
	options: { en: string[]; es: string[] };
	correct: number; // 0-based index
}

export const QUESTIONS: QuizQuestion[] = [
	{
		question: { en: 'How many bitcoin will ever exist?', es: '¿Cuántos bitcoin van a existir?' },
		options: {
			en: ['1 billion', '21 million', '100 million', 'Unlimited'],
			es: ['1,000 millones', '21 millones', '100 millones', 'Ilimitado'],
		},
		correct: 1,
	},
	{
		question: { en: 'Who created Bitcoin?', es: '¿Quién creó Bitcoin?' },
		options: {
			en: ['Elon Musk', 'Satoshi Nakamoto', 'Mark Zuckerberg', 'Vitalik Buterin'],
			es: ['Elon Musk', 'Satoshi Nakamoto', 'Mark Zuckerberg', 'Vitalik Buterin'],
		},
		correct: 1,
	},
	{
		question: { en: 'What year was Bitcoin created?', es: '¿En qué año se creó Bitcoin?' },
		options: {
			en: ['2005', '2009', '2013', '2015'],
			es: ['2005', '2009', '2013', '2015'],
		},
		correct: 1,
	},
	{
		question: { en: 'What is a "halving"?', es: '¿Qué es un "halving"?' },
		options: {
			en: ['Bitcoin\'s price drops 50%', 'Mining reward is cut in half', 'Half of all bitcoin are burned', 'Transaction fees double'],
			es: ['El precio baja 50%', 'La recompensa de minería se reduce a la mitad', 'Se queman la mitad de los bitcoin', 'Las comisiones se duplican'],
		},
		correct: 1,
	},
	{
		question: { en: 'What country made Bitcoin legal tender first?', es: '¿Qué país hizo a Bitcoin moneda de curso legal primero?' },
		options: {
			en: ['United States', 'Japan', 'El Salvador', 'Switzerland'],
			es: ['Estados Unidos', 'Japón', 'El Salvador', 'Suiza'],
		},
		correct: 2,
	},
	{
		question: { en: 'What powers Bitcoin mining in El Salvador?', es: '¿Qué alimenta la minería de Bitcoin en El Salvador?' },
		options: {
			en: ['Solar panels', 'Wind turbines', 'Volcano energy', 'Coal plants'],
			es: ['Paneles solares', 'Turbinas de viento', 'Energía de volcanes', 'Plantas de carbón'],
		},
		correct: 2,
	},
	{
		question: { en: 'What is the smallest unit of bitcoin called?', es: '¿Cómo se llama la unidad más pequeña de bitcoin?' },
		options: {
			en: ['Mini-coin', 'Satoshi', 'Bit', 'Nano-btc'],
			es: ['Mini-coin', 'Satoshi', 'Bit', 'Nano-btc'],
		},
		correct: 1,
	},
	{
		question: { en: 'How many satoshis are in 1 bitcoin?', es: '¿Cuántos satoshis hay en 1 bitcoin?' },
		options: {
			en: ['1,000', '1 million', '100 million', '1 billion'],
			es: ['1,000', '1 millón', '100 millones', '1,000 millones'],
		},
		correct: 2,
	},
	{
		question: { en: 'What is Lightning Network?', es: '¿Qué es Lightning Network?' },
		options: {
			en: ['A weather app', 'Fast & cheap Bitcoin payments', 'A mining machine', 'A new cryptocurrency'],
			es: ['Una app del clima', 'Pagos rápidos y baratos de Bitcoin', 'Una máquina de minería', 'Una nueva criptomoneda'],
		},
		correct: 1,
	},
	{
		question: { en: 'Can anyone see Bitcoin transactions?', es: '¿Cualquiera puede ver las transacciones de Bitcoin?' },
		options: {
			en: ['No, they\'re secret', 'Only banks can', 'Yes, they\'re public', 'Only the government'],
			es: ['No, son secretas', 'Solo los bancos', 'Sí, son públicas', 'Solo el gobierno'],
		},
		correct: 2,
	},
	{
		question: { en: 'What do Bitcoin miners actually do?', es: '¿Qué hacen realmente los mineros de Bitcoin?' },
		options: {
			en: ['Dig underground', 'Verify and process transactions', 'Print new money', 'Hack computers'],
			es: ['Cavan bajo tierra', 'Verifican y procesan transacciones', 'Imprimen dinero nuevo', 'Hackean computadoras'],
		},
		correct: 1,
	},
	{
		question: { en: 'Does Bitcoin need a bank to work?', es: '¿Bitcoin necesita un banco para funcionar?' },
		options: {
			en: ['Yes, always', 'No, it\'s peer-to-peer', 'Only for big amounts', 'Only in some countries'],
			es: ['Sí, siempre', 'No, es de persona a persona', 'Solo para montos grandes', 'Solo en algunos países'],
		},
		correct: 1,
	},
	{
		question: { en: 'What does "HODL" mean?', es: '¿Qué significa "HODL"?' },
		options: {
			en: ['A type of wallet', 'Hold on for dear life (don\'t sell)', 'A mining technique', 'A trading strategy'],
			es: ['Un tipo de billetera', 'Aguantar y no vender', 'Una técnica de minería', 'Una estrategia de trading'],
		},
		correct: 1,
	},
	{
		question: { en: 'What is a Bitcoin wallet?', es: '¿Qué es una billetera de Bitcoin?' },
		options: {
			en: ['A physical wallet for coins', 'An app that stores your keys', 'A bank account', 'A website'],
			es: ['Una billetera física para monedas', 'Una app que guarda tus llaves', 'Una cuenta bancaria', 'Un sitio web'],
		},
		correct: 1,
	},
	{
		question: { en: 'Can someone print more bitcoin?', es: '¿Alguien puede imprimir más bitcoin?' },
		options: {
			en: ['Yes, the government', 'Yes, the developers', 'No, the limit is in the code', 'Yes, miners can'],
			es: ['Sí, el gobierno', 'Sí, los desarrolladores', 'No, el límite está en el código', 'Sí, los mineros pueden'],
		},
		correct: 2,
	},
	{
		question: { en: 'About how long does a Bitcoin block take?', es: '¿Cuánto tarda aproximadamente un bloque de Bitcoin?' },
		options: {
			en: ['1 second', '10 minutes', '1 hour', '1 day'],
			es: ['1 segundo', '10 minutos', '1 hora', '1 día'],
		},
		correct: 1,
	},
	{
		question: { en: 'What happens if you lose your Bitcoin keys?', es: '¿Qué pasa si perdés tus llaves de Bitcoin?' },
		options: {
			en: ['The bank recovers them', 'You can reset the password', 'Your bitcoin are lost forever', 'The government helps you'],
			es: ['El banco las recupera', 'Podés resetear la contraseña', 'Tus bitcoin se pierden para siempre', 'El gobierno te ayuda'],
		},
		correct: 2,
	},
	{
		question: { en: 'Why is Bitcoin compared to gold?', es: '¿Por qué comparan a Bitcoin con el oro?' },
		options: {
			en: ['It\'s yellow', 'Both are scarce and valuable', 'Both are heavy', 'It was made from gold'],
			es: ['Es amarillo', 'Ambos son escasos y valiosos', 'Ambos son pesados', 'Se hizo del oro'],
		},
		correct: 1,
	},
];

/** Pick a random question, optionally excluding already-used indices */
export function pickQuestion(usedIndices: Set<number>): { question: QuizQuestion; index: number } | null {
	const available = QUESTIONS.map((q, i) => ({ q, i })).filter(({ i }) => !usedIndices.has(i));
	if (available.length === 0) return null;
	const pick = available[Math.floor(Math.random() * available.length)];
	return { question: pick.q, index: pick.i };
}
