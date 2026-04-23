"""Bilingual notification templates for all Magma Bitcoin app events.

Each key in ``TEMPLATES`` is a template ID.  The value is a dict with:

    subject_en      : str  — email/push subject (English), supports {variables}
    subject_es      : str  — email/push subject (Spanish)
    body_en         : str  — plain-text body (English), supports {variables}
    body_es         : str  — plain-text body (Spanish)
    body_html_en    : str  — HTML body (English), supports {variables}
    body_html_es    : str  — HTML body (Spanish)
    icon            : str  — emoji or icon identifier
    priority        : str  — "low" | "normal" | "high" | "critical"
    category        : str  — grouping category
    sample_data     : dict — sample values for all {variables} used

Template categories
-------------------
    price, fees, savings, achievements, social, security, system, market
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Base HTML wrapper used by all HTML templates
# ---------------------------------------------------------------------------

_HTML_HEADER = """\
<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{subject}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           background: #0d0d0d; color: #f5f5f5; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 40px auto; background: #1a1a1a;
                  border-radius: 12px; overflow: hidden; border: 1px solid #2a2a2a; }}
    .header {{ background: linear-gradient(135deg, #ff6b00, #cc4400);
               padding: 32px 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; color: #fff; }}
    .header .icon {{ font-size: 48px; margin-bottom: 12px; display: block; }}
    .body {{ padding: 32px 24px; }}
    .body p {{ margin: 0 0 16px; line-height: 1.6; color: #e0e0e0; }}
    .highlight {{ background: #2a2a2a; border-left: 4px solid #ff6b00;
                  border-radius: 4px; padding: 16px; margin: 20px 0; }}
    .highlight .value {{ font-size: 28px; font-weight: 700; color: #ff6b00; }}
    .highlight .label {{ font-size: 12px; color: #888; text-transform: uppercase;
                         letter-spacing: 1px; margin-top: 4px; }}
    .cta {{ text-align: center; margin: 28px 0; }}
    .cta a {{ background: #ff6b00; color: #fff; padding: 14px 32px;
              border-radius: 8px; text-decoration: none; font-weight: 600;
              font-size: 16px; display: inline-block; }}
    .footer {{ padding: 20px 24px; text-align: center; border-top: 1px solid #2a2a2a;
               color: #555; font-size: 12px; }}
    .footer a {{ color: #ff6b00; text-decoration: none; }}
  </style>
</head>
<body>
<div class="container">
"""

_HTML_FOOTER = """\
  <div class="footer">
    <p>Magma &mdash; Stack sats, stay sovereign. 🌋</p>
    <p><a href="{unsubscribe_url}">Unsubscribe</a> &nbsp;|&nbsp;
       <a href="https://magma.app">Open Magma</a></p>
  </div>
</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Master templates dictionary
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict] = {

    # -----------------------------------------------------------------------
    # P R I C E   A L E R T S
    # -----------------------------------------------------------------------

    "price_alert_above": {
        "subject_en": "🚀 Bitcoin above {price_usd} — your alert triggered",
        "subject_es": "🚀 Bitcoin superó {price_usd} — tu alerta se activó",
        "body_en": (
            "Good news! Bitcoin has crossed above your target of {price_usd}.\n\n"
            "Current price: {current_price_usd} ({change_pct}% in 24h)\n"
            "Your stack: {user_sats} sats ({stack_value_usd} USD)\n\n"
            "This alert was set on {alert_created_date}. You can manage your "
            "alerts in the Magma app."
        ),
        "body_es": (
            "¡Buenas noticias! Bitcoin ha superado tu objetivo de {price_usd}.\n\n"
            "Precio actual: {current_price_usd} ({change_pct}% en 24h)\n"
            "Tu stack: {user_sats} sats ({stack_value_usd} USD)\n\n"
            "Esta alerta fue configurada el {alert_created_date}. Puedes gestionar "
            "tus alertas en la app Magma."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">🚀</span>
    <h1>Price Alert Triggered!</h1>
  </div>
  <div class="body">
    <p>Bitcoin has crossed <strong>above</strong> your target price.</p>
    <div class="highlight">
      <div class="value">{current_price_usd}</div>
      <div class="label">Current Bitcoin Price</div>
    </div>
    <p>Target: {price_usd} &nbsp;|&nbsp; 24h Change: {change_pct}%</p>
    <p>Your stack value: <strong>{stack_value_usd}</strong> ({user_sats} sats)</p>
    <div class="cta"><a href="https://magma.app/portfolio">View Portfolio</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">🚀</span>
    <h1>¡Alerta de precio activada!</h1>
  </div>
  <div class="body">
    <p>Bitcoin ha superado <strong>tu precio objetivo</strong>.</p>
    <div class="highlight">
      <div class="value">{current_price_usd}</div>
      <div class="label">Precio actual de Bitcoin</div>
    </div>
    <p>Objetivo: {price_usd} &nbsp;|&nbsp; Cambio 24h: {change_pct}%</p>
    <p>Valor de tu stack: <strong>{stack_value_usd}</strong> ({user_sats} sats)</p>
    <div class="cta"><a href="https://magma.app/portfolio">Ver portafolio</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🚀",
        "priority": "high",
        "category": "price",
        "sample_data": {
            "price_usd": "$70,000",
            "current_price_usd": "$72,500",
            "change_pct": "+3.6",
            "user_sats": "500,000",
            "stack_value_usd": "$362.50",
            "alert_created_date": "2024-11-01",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Bitcoin above $70,000 — your alert triggered",
            "lang": "en",
        },
    },

    "price_alert_below": {
        "subject_en": "📉 Bitcoin below {price_usd} — your alert triggered",
        "subject_es": "📉 Bitcoin cayó bajo {price_usd} — tu alerta se activó",
        "body_en": (
            "Bitcoin has dropped below your target of {price_usd}.\n\n"
            "Current price: {current_price_usd} ({change_pct}% in 24h)\n"
            "Your stack: {user_sats} sats ({stack_value_usd} USD)\n\n"
            "This might be a good DCA opportunity. Check your savings plan in Magma."
        ),
        "body_es": (
            "Bitcoin ha caído por debajo de tu objetivo de {price_usd}.\n\n"
            "Precio actual: {current_price_usd} ({change_pct}% en 24h)\n"
            "Tu stack: {user_sats} sats ({stack_value_usd} USD)\n\n"
            "Esta podría ser una buena oportunidad para hacer DCA. "
            "Revisa tu plan de ahorro en Magma."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #1565c0, #0d47a1);">
    <span class="icon">📉</span>
    <h1>Price Alert Triggered</h1>
  </div>
  <div class="body">
    <p>Bitcoin has dropped <strong>below</strong> your target price.</p>
    <div class="highlight">
      <div class="value" style="color:#42a5f5;">{current_price_usd}</div>
      <div class="label">Current Bitcoin Price</div>
    </div>
    <p>Target: {price_usd} &nbsp;|&nbsp; 24h Change: {change_pct}%</p>
    <p>Consider this a DCA opportunity. Stack more sats at a lower price!</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#1565c0;">Stack Sats Now</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #1565c0, #0d47a1);">
    <span class="icon">📉</span>
    <h1>Alerta de precio activada</h1>
  </div>
  <div class="body">
    <p>Bitcoin ha caído <strong>por debajo</strong> de tu precio objetivo.</p>
    <div class="highlight">
      <div class="value" style="color:#42a5f5;">{current_price_usd}</div>
      <div class="label">Precio actual de Bitcoin</div>
    </div>
    <p>Objetivo: {price_usd} &nbsp;|&nbsp; Cambio 24h: {change_pct}%</p>
    <p>¡Considera esto una oportunidad de DCA. Apila más sats a menor precio!</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#1565c0;">Apilar Sats Ahora</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "📉",
        "priority": "high",
        "category": "price",
        "sample_data": {
            "price_usd": "$50,000",
            "current_price_usd": "$48,200",
            "change_pct": "-3.6",
            "user_sats": "500,000",
            "stack_value_usd": "$241.00",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Bitcoin below $50,000 — your alert triggered",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # F E E   A L E R T S
    # -----------------------------------------------------------------------

    "fee_alert_low": {
        "subject_en": "⚡ Low fees now — great time for on-chain transactions",
        "subject_es": "⚡ Tarifas bajas ahora — buen momento para transacciones en cadena",
        "body_en": (
            "Bitcoin mempool fees are currently LOW.\n\n"
            "Current fee rate: {fee_rate_sat_vb} sat/vB\n"
            "Estimated confirmation: {est_confirm_time}\n\n"
            "This is a great time to:\n"
            "  - Open or close Lightning channels\n"
            "  - Consolidate UTXOs\n"
            "  - Move Bitcoin to cold storage\n"
            "  - Make on-chain withdrawals\n\n"
            "Low fees don't last forever — act while it lasts."
        ),
        "body_es": (
            "Las tarifas del mempool de Bitcoin están BAJAS actualmente.\n\n"
            "Tasa de tarifa actual: {fee_rate_sat_vb} sat/vB\n"
            "Confirmación estimada: {est_confirm_time}\n\n"
            "Este es un gran momento para:\n"
            "  - Abrir o cerrar canales Lightning\n"
            "  - Consolidar UTXOs\n"
            "  - Mover Bitcoin al almacenamiento en frío\n"
            "  - Hacer retiros en cadena\n\n"
            "Las tarifas bajas no duran para siempre."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #2e7d32, #1b5e20);">
    <span class="icon">⚡</span>
    <h1>Low Bitcoin Fees Right Now</h1>
  </div>
  <div class="body">
    <p>Bitcoin network fees are currently at a low level. This is your window!</p>
    <div class="highlight">
      <div class="value" style="color:#66bb6a;">{fee_rate_sat_vb} sat/vB</div>
      <div class="label">Current Fee Rate &nbsp;|&nbsp; Confirm in {est_confirm_time}</div>
    </div>
    <p>Now is the time to consolidate UTXOs, open Lightning channels, or move Bitcoin to cold storage.</p>
    <div class="cta"><a href="https://magma.app/send" style="background:#2e7d32;">Make a Transaction</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #2e7d32, #1b5e20);">
    <span class="icon">⚡</span>
    <h1>Tarifas de Bitcoin bajas ahora</h1>
  </div>
  <div class="body">
    <p>Las tarifas de la red Bitcoin están actualmente en un nivel bajo. ¡Esta es tu ventana!</p>
    <div class="highlight">
      <div class="value" style="color:#66bb6a;">{fee_rate_sat_vb} sat/vB</div>
      <div class="label">Tasa actual &nbsp;|&nbsp; Confirma en {est_confirm_time}</div>
    </div>
    <p>Ahora es el momento de consolidar UTXOs, abrir canales Lightning o mover Bitcoin al frío.</p>
    <div class="cta"><a href="https://magma.app/send" style="background:#2e7d32;">Hacer una transacción</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "⚡",
        "priority": "normal",
        "category": "fees",
        "sample_data": {
            "fee_rate_sat_vb": "2",
            "est_confirm_time": "~30 minutes",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Low fees now — great time for on-chain transactions",
            "lang": "en",
        },
    },

    "fee_alert_high": {
        "subject_en": "🔥 High Bitcoin fees — consider waiting or using Lightning",
        "subject_es": "🔥 Tarifas altas de Bitcoin — considera esperar o usar Lightning",
        "body_en": (
            "Bitcoin mempool fees are currently HIGH.\n\n"
            "Current fee rate: {fee_rate_sat_vb} sat/vB\n"
            "Mempool size: {mempool_size_mb} MB\n\n"
            "Recommendations:\n"
            "  - Use Lightning for small payments\n"
            "  - Delay non-urgent on-chain transactions\n"
            "  - If you must transact, set fees carefully\n\n"
            "We'll notify you when fees drop below {alert_threshold_sat_vb} sat/vB."
        ),
        "body_es": (
            "Las tarifas del mempool de Bitcoin están ALTAS actualmente.\n\n"
            "Tasa de tarifa actual: {fee_rate_sat_vb} sat/vB\n"
            "Tamaño del mempool: {mempool_size_mb} MB\n\n"
            "Recomendaciones:\n"
            "  - Usa Lightning para pagos pequeños\n"
            "  - Retrasa transacciones en cadena no urgentes\n"
            "  - Si debes transaccionar, configura las tarifas con cuidado\n\n"
            "Te notificaremos cuando las tarifas bajen de {alert_threshold_sat_vb} sat/vB."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #b71c1c, #7f0000);">
    <span class="icon">🔥</span>
    <h1>High Bitcoin Fees Warning</h1>
  </div>
  <div class="body">
    <p>Bitcoin network fees are currently elevated. Consider alternatives.</p>
    <div class="highlight">
      <div class="value" style="color:#ef5350;">{fee_rate_sat_vb} sat/vB</div>
      <div class="label">Current Fee Rate &nbsp;|&nbsp; Mempool: {mempool_size_mb} MB</div>
    </div>
    <p>Use Lightning for everyday payments. We'll alert you when fees return to normal.</p>
    <div class="cta"><a href="https://magma.app/lightning" style="background:#b71c1c;">Pay with Lightning</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #b71c1c, #7f0000);">
    <span class="icon">🔥</span>
    <h1>Advertencia de tarifas altas</h1>
  </div>
  <div class="body">
    <p>Las tarifas de la red Bitcoin están elevadas. Considera alternativas.</p>
    <div class="highlight">
      <div class="value" style="color:#ef5350;">{fee_rate_sat_vb} sat/vB</div>
      <div class="label">Tasa actual &nbsp;|&nbsp; Mempool: {mempool_size_mb} MB</div>
    </div>
    <p>Usa Lightning para pagos cotidianos. Te avisaremos cuando las tarifas vuelvan a la normalidad.</p>
    <div class="cta"><a href="https://magma.app/lightning" style="background:#b71c1c;">Pagar con Lightning</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🔥",
        "priority": "normal",
        "category": "fees",
        "sample_data": {
            "fee_rate_sat_vb": "85",
            "mempool_size_mb": "342",
            "alert_threshold_sat_vb": "10",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "High Bitcoin fees — consider waiting or using Lightning",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # S A V I N G S   &   D E P O S I T S
    # -----------------------------------------------------------------------

    "deposit_confirmed": {
        "subject_en": "✅ Deposit confirmed — {sats_received} sats added to your stack",
        "subject_es": "✅ Depósito confirmado — {sats_received} sats añadidos a tu stack",
        "body_en": (
            "Your deposit has been confirmed on the Bitcoin blockchain.\n\n"
            "Received: {sats_received} sats ({usd_value} USD)\n"
            "Transaction: {txid}\n"
            "Confirmations: {confirmations}\n"
            "Total stack: {total_sats} sats ({total_usd} USD)\n\n"
            "Keep stacking. Every sat counts."
        ),
        "body_es": (
            "Tu depósito ha sido confirmado en la blockchain de Bitcoin.\n\n"
            "Recibido: {sats_received} sats ({usd_value} USD)\n"
            "Transacción: {txid}\n"
            "Confirmaciones: {confirmations}\n"
            "Stack total: {total_sats} sats ({total_usd} USD)\n\n"
            "Sigue apilando. Cada sat cuenta."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">✅</span>
    <h1>Deposit Confirmed!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">+{sats_received} sats</div>
      <div class="label">Received &nbsp;|&nbsp; {usd_value} USD</div>
    </div>
    <p>Transaction ID: <code style="font-size:11px; color:#aaa;">{txid}</code></p>
    <p>Confirmations: {confirmations} &nbsp;|&nbsp; Total stack: <strong>{total_sats} sats</strong> ({total_usd})</p>
    <div class="cta"><a href="https://magma.app/portfolio">View Portfolio</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">✅</span>
    <h1>¡Depósito confirmado!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">+{sats_received} sats</div>
      <div class="label">Recibido &nbsp;|&nbsp; {usd_value} USD</div>
    </div>
    <p>ID de transacción: <code style="font-size:11px; color:#aaa;">{txid}</code></p>
    <p>Confirmaciones: {confirmations} &nbsp;|&nbsp; Stack total: <strong>{total_sats} sats</strong> ({total_usd})</p>
    <div class="cta"><a href="https://magma.app/portfolio">Ver portafolio</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "✅",
        "priority": "normal",
        "category": "savings",
        "sample_data": {
            "sats_received": "21,000",
            "usd_value": "$13.23",
            "txid": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "confirmations": "6",
            "total_sats": "521,000",
            "total_usd": "$327.23",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Deposit confirmed — 21,000 sats added to your stack",
            "lang": "en",
        },
    },

    "goal_reached": {
        "subject_en": "🎯 Savings goal reached! You've stacked {goal_sats} sats",
        "subject_es": "🎯 ¡Meta de ahorro alcanzada! Has apilado {goal_sats} sats",
        "body_en": (
            "Congratulations! You've reached your savings goal of {goal_sats} sats.\n\n"
            "Goal: {goal_name}\n"
            "Achieved: {goal_sats} sats ({goal_usd} USD)\n"
            "Time to complete: {days_taken} days\n"
            "Average buy price: {avg_price_usd}/BTC\n\n"
            "It's time to set your next goal and keep stacking!"
        ),
        "body_es": (
            "¡Felicidades! Has alcanzado tu meta de ahorro de {goal_sats} sats.\n\n"
            "Meta: {goal_name}\n"
            "Logrado: {goal_sats} sats ({goal_usd} USD)\n"
            "Tiempo para completar: {days_taken} días\n"
            "Precio promedio de compra: {avg_price_usd}/BTC\n\n"
            "¡Es hora de fijar tu próxima meta y seguir apilando!"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #f57f17, #e65100);">
    <span class="icon">🎯</span>
    <h1>Savings Goal Reached!</h1>
  </div>
  <div class="body">
    <p>You crushed it! Your goal <strong>{goal_name}</strong> is complete.</p>
    <div class="highlight">
      <div class="value">{goal_sats} sats</div>
      <div class="label">{goal_usd} USD &nbsp;|&nbsp; {days_taken} days to complete</div>
    </div>
    <p>Average buy price: {avg_price_usd}/BTC</p>
    <p>Ready to set your next target? Every sat gets you closer to financial sovereignty.</p>
    <div class="cta"><a href="https://magma.app/goals">Set Next Goal</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #f57f17, #e65100);">
    <span class="icon">🎯</span>
    <h1>¡Meta de ahorro alcanzada!</h1>
  </div>
  <div class="body">
    <p>¡Lo lograste! Tu meta <strong>{goal_name}</strong> está completa.</p>
    <div class="highlight">
      <div class="value">{goal_sats} sats</div>
      <div class="label">{goal_usd} USD &nbsp;|&nbsp; {days_taken} días para completar</div>
    </div>
    <p>Precio promedio de compra: {avg_price_usd}/BTC</p>
    <p>¿Listo para fijar tu próximo objetivo? Cada sat te acerca a la soberanía financiera.</p>
    <div class="cta"><a href="https://magma.app/goals">Fijar próxima meta</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🎯",
        "priority": "high",
        "category": "savings",
        "sample_data": {
            "goal_name": "Emergency Fund (1M sats)",
            "goal_sats": "1,000,000",
            "goal_usd": "$628.00",
            "days_taken": "183",
            "avg_price_usd": "$62,800",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Savings goal reached! You've stacked 1,000,000 sats",
            "lang": "en",
        },
    },

    "milestone_reached": {
        "subject_en": "🏔 Milestone: {milestone_sats} sats stacked!",
        "subject_es": "🏔 Hito: ¡{milestone_sats} sats apilados!",
        "body_en": (
            "You've reached a major milestone: {milestone_sats} sats!\n\n"
            "This represents {milestone_btc} BTC — {milestone_description_en}.\n\n"
            "Total time stacking: {days_active} days\n"
            "Current value: {current_usd} USD\n\n"
            "The orange pill is working. Keep going!"
        ),
        "body_es": (
            "¡Has alcanzado un hito importante: {milestone_sats} sats!\n\n"
            "Esto representa {milestone_btc} BTC — {milestone_description_es}.\n\n"
            "Tiempo total apilando: {days_active} días\n"
            "Valor actual: {current_usd} USD\n\n"
            "La pastilla naranja está funcionando. ¡Sigue adelante!"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">🏔</span>
    <h1>Milestone Reached!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{milestone_sats} sats</div>
      <div class="label">{milestone_btc} BTC &nbsp;|&nbsp; ~{current_usd} USD</div>
    </div>
    <p>{milestone_description_en}</p>
    <p>Stacking for {days_active} days. The orange pill is working!</p>
    <div class="cta"><a href="https://magma.app/portfolio">View Your Journey</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">🏔</span>
    <h1>¡Hito alcanzado!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{milestone_sats} sats</div>
      <div class="label">{milestone_btc} BTC &nbsp;|&nbsp; ~{current_usd} USD</div>
    </div>
    <p>{milestone_description_es}</p>
    <p>Apilando durante {days_active} días. ¡La pastilla naranja está funcionando!</p>
    <div class="cta"><a href="https://magma.app/portfolio">Ver tu progreso</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🏔",
        "priority": "normal",
        "category": "savings",
        "sample_data": {
            "milestone_sats": "1,000,000",
            "milestone_btc": "0.01",
            "milestone_description_en": "You own 1 million satoshis — a true sat-stacker milestone!",
            "milestone_description_es": "¡Posees 1 millón de satoshis — un verdadero hito de apilador!",
            "days_active": "120",
            "current_usd": "$628.00",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Milestone: 1,000,000 sats stacked!",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # G A M I F I C A T I O N
    # -----------------------------------------------------------------------

    "achievement_earned": {
        "subject_en": "🏆 Achievement unlocked: {achievement_name}",
        "subject_es": "🏆 Logro desbloqueado: {achievement_name}",
        "body_en": (
            "You've unlocked a new achievement: {achievement_name}!\n\n"
            "{achievement_description_en}\n\n"
            "Reward: +{xp_earned} XP\n"
            "Your total XP: {total_xp}\n"
            "Current level: {current_level} ({level_name})\n\n"
            "Keep stacking sats and learning to unlock more achievements!"
        ),
        "body_es": (
            "¡Has desbloqueado un nuevo logro: {achievement_name}!\n\n"
            "{achievement_description_es}\n\n"
            "Recompensa: +{xp_earned} XP\n"
            "Tu XP total: {total_xp}\n"
            "Nivel actual: {current_level} ({level_name})\n\n"
            "¡Sigue apilando sats y aprendiendo para desbloquear más logros!"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">🏆</span>
    <h1>Achievement Unlocked!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{achievement_name}</div>
      <div class="label">+{xp_earned} XP Earned</div>
    </div>
    <p>{achievement_description_en}</p>
    <p>Level: <strong>{current_level} — {level_name}</strong> &nbsp;|&nbsp; Total XP: {total_xp}</p>
    <div class="cta"><a href="https://magma.app/achievements">View All Achievements</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">🏆</span>
    <h1>¡Logro desbloqueado!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{achievement_name}</div>
      <div class="label">+{xp_earned} XP ganados</div>
    </div>
    <p>{achievement_description_es}</p>
    <p>Nivel: <strong>{current_level} — {level_name}</strong> &nbsp;|&nbsp; XP total: {total_xp}</p>
    <div class="cta"><a href="https://magma.app/achievements">Ver todos los logros</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🏆",
        "priority": "normal",
        "category": "achievements",
        "sample_data": {
            "achievement_name": "Sat Stacker",
            "achievement_description_en": "You stacked your first 100,000 sats. The journey begins!",
            "achievement_description_es": "Apilaste tus primeros 100,000 sats. ¡El viaje comienza!",
            "xp_earned": "500",
            "total_xp": "1,250",
            "current_level": "3",
            "level_name": "Pleb",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Achievement unlocked: Sat Stacker",
            "lang": "en",
        },
    },

    "level_up": {
        "subject_en": "⬆️ Level up! You're now level {new_level}: {level_name}",
        "subject_es": "⬆️ ¡Subiste de nivel! Ahora eres nivel {new_level}: {level_name}",
        "body_en": (
            "You've leveled up in Magma!\n\n"
            "New level: {new_level} — {level_name}\n"
            "XP earned this level: {xp_this_level}\n"
            "Total XP: {total_xp}\n\n"
            "New perks unlocked: {perks_unlocked_en}\n\n"
            "Keep stacking sats to reach the next level!"
        ),
        "body_es": (
            "¡Has subido de nivel en Magma!\n\n"
            "Nuevo nivel: {new_level} — {level_name}\n"
            "XP ganado este nivel: {xp_this_level}\n"
            "XP total: {total_xp}\n\n"
            "Nuevas ventajas desbloqueadas: {perks_unlocked_es}\n\n"
            "¡Sigue apilando sats para alcanzar el próximo nivel!"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #6a1b9a, #4a148c);">
    <span class="icon">⬆️</span>
    <h1>Level Up!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ce93d8;">Level {new_level}: {level_name}</div>
      <div class="label">Total XP: {total_xp}</div>
    </div>
    <p>New perks: {perks_unlocked_en}</p>
    <div class="cta"><a href="https://magma.app/profile" style="background:#6a1b9a;">View Profile</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #6a1b9a, #4a148c);">
    <span class="icon">⬆️</span>
    <h1>¡Subiste de nivel!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ce93d8;">Nivel {new_level}: {level_name}</div>
      <div class="label">XP total: {total_xp}</div>
    </div>
    <p>Nuevas ventajas: {perks_unlocked_es}</p>
    <div class="cta"><a href="https://magma.app/profile" style="background:#6a1b9a;">Ver perfil</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "⬆️",
        "priority": "high",
        "category": "achievements",
        "sample_data": {
            "new_level": "5",
            "level_name": "Hodler",
            "xp_this_level": "2,500",
            "total_xp": "5,000",
            "perks_unlocked_en": "Advanced analytics, custom alerts",
            "perks_unlocked_es": "Análisis avanzado, alertas personalizadas",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Level up! You're now level 5: Hodler",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # S T R E A K S
    # -----------------------------------------------------------------------

    "streak_reminder": {
        "subject_en": "🔥 Don't break your {streak_days}-day stacking streak!",
        "subject_es": "🔥 ¡No rompas tu racha de {streak_days} días apilando!",
        "body_en": (
            "Your {streak_days}-day stacking streak is at risk!\n\n"
            "You haven't stacked sats today yet. Complete any savings action "
            "in Magma before midnight to keep your streak alive.\n\n"
            "Current streak: {streak_days} days\n"
            "Longest streak: {best_streak_days} days\n\n"
            "Don't let the streak die — stack even 1 sat."
        ),
        "body_es": (
            "¡Tu racha de {streak_days} días apilando está en riesgo!\n\n"
            "Todavía no has apilado sats hoy. Completa cualquier acción de ahorro "
            "en Magma antes de medianoche para mantener tu racha.\n\n"
            "Racha actual: {streak_days} días\n"
            "Mejor racha: {best_streak_days} días\n\n"
            "No dejes morir la racha — apila aunque sea 1 sat."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #e65100, #bf360c);">
    <span class="icon">🔥</span>
    <h1>Streak at Risk!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ff8f00;">{streak_days} days</div>
      <div class="label">Current Stacking Streak — Don't break it!</div>
    </div>
    <p>Stack at least 1 sat before midnight to keep the fire burning.</p>
    <p>Best streak: {best_streak_days} days</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#e65100;">Stack Sats Now</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #e65100, #bf360c);">
    <span class="icon">🔥</span>
    <h1>¡Racha en riesgo!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ff8f00;">{streak_days} días</div>
      <div class="label">Racha de apilado actual — ¡No la rompas!</div>
    </div>
    <p>Apila al menos 1 sat antes de la medianoche para mantener el fuego ardiendo.</p>
    <p>Mejor racha: {best_streak_days} días</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#e65100;">Apilar sats ahora</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🔥",
        "priority": "high",
        "category": "social",
        "sample_data": {
            "streak_days": "21",
            "best_streak_days": "45",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Don't break your 21-day stacking streak!",
            "lang": "en",
        },
    },

    "streak_broken": {
        "subject_en": "😢 Streak broken — but your {sats_stacked} sats are safe",
        "subject_es": "😢 Racha rota — pero tus {sats_stacked} sats están seguros",
        "body_en": (
            "Your stacking streak has ended after {previous_streak} days.\n\n"
            "Don't worry — your Bitcoin is safe. You've stacked {sats_stacked} sats "
            "since joining Magma. That's real money, and no streak can take it away.\n\n"
            "Start a new streak today and beat your record of {previous_streak} days!"
        ),
        "body_es": (
            "Tu racha de apilado ha terminado después de {previous_streak} días.\n\n"
            "No te preocupes — tu Bitcoin está seguro. Has apilado {sats_stacked} sats "
            "desde que te uniste a Magma. Ese es dinero real, y ninguna racha puede quitártelo.\n\n"
            "¡Comienza una nueva racha hoy y supera tu récord de {previous_streak} días!"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #37474f, #263238);">
    <span class="icon">😢</span>
    <h1>Streak Broken</h1>
  </div>
  <div class="body">
    <p>Your {previous_streak}-day stacking streak has ended. But your stack is safe!</p>
    <div class="highlight">
      <div class="value">{sats_stacked} sats</div>
      <div class="label">Total Stacked — Your Bitcoin is Yours Forever</div>
    </div>
    <p>Start fresh today and break your record of {previous_streak} days.</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#37474f;">Start New Streak</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #37474f, #263238);">
    <span class="icon">😢</span>
    <h1>Racha rota</h1>
  </div>
  <div class="body">
    <p>Tu racha de {previous_streak} días ha terminado. ¡Pero tu stack está seguro!</p>
    <div class="highlight">
      <div class="value">{sats_stacked} sats</div>
      <div class="label">Total apilado — Tu Bitcoin es tuyo para siempre</div>
    </div>
    <p>Empieza de nuevo hoy y supera tu récord de {previous_streak} días.</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#37474f;">Comenzar nueva racha</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "😢",
        "priority": "normal",
        "category": "social",
        "sample_data": {
            "previous_streak": "21",
            "sats_stacked": "500,000",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Streak broken — but your 500,000 sats are safe",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # R E P O R T S
    # -----------------------------------------------------------------------

    "weekly_summary": {
        "subject_en": "📊 Your Bitcoin weekly summary — {week_label}",
        "subject_es": "📊 Tu resumen semanal de Bitcoin — {week_label}",
        "body_en": (
            "Here's your Bitcoin summary for the week of {week_label}:\n\n"
            "Sats stacked this week: {weekly_sats}\n"
            "USD invested: {weekly_usd}\n"
            "Average buy price: {avg_price_usd}/BTC\n"
            "Portfolio change: {portfolio_change_pct}%\n"
            "Total stack: {total_sats} sats ({total_value_usd})\n\n"
            "Bitcoin price: {btc_price_usd} ({btc_weekly_change_pct}% this week)\n\n"
            "Keep stacking, keep learning. See you next week!"
        ),
        "body_es": (
            "Aquí está tu resumen de Bitcoin para la semana de {week_label}:\n\n"
            "Sats apilados esta semana: {weekly_sats}\n"
            "USD invertidos: {weekly_usd}\n"
            "Precio promedio de compra: {avg_price_usd}/BTC\n"
            "Cambio en portafolio: {portfolio_change_pct}%\n"
            "Stack total: {total_sats} sats ({total_value_usd})\n\n"
            "Precio de Bitcoin: {btc_price_usd} ({btc_weekly_change_pct}% esta semana)\n\n"
            "Sigue apilando, sigue aprendiendo. ¡Hasta la próxima semana!"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">📊</span>
    <h1>Weekly Bitcoin Summary</h1>
  </div>
  <div class="body">
    <p><strong>Week of {week_label}</strong></p>
    <div class="highlight">
      <div class="value">+{weekly_sats} sats</div>
      <div class="label">Stacked this week ({weekly_usd} invested)</div>
    </div>
    <p>Avg buy price: {avg_price_usd}/BTC &nbsp;|&nbsp; Portfolio: {portfolio_change_pct}%</p>
    <p>Total stack: <strong>{total_sats} sats</strong> = {total_value_usd}</p>
    <p>BTC Price: {btc_price_usd} ({btc_weekly_change_pct}% this week)</p>
    <div class="cta"><a href="https://magma.app/analytics">Full Analytics</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">📊</span>
    <h1>Resumen semanal de Bitcoin</h1>
  </div>
  <div class="body">
    <p><strong>Semana del {week_label}</strong></p>
    <div class="highlight">
      <div class="value">+{weekly_sats} sats</div>
      <div class="label">Apilados esta semana ({weekly_usd} invertidos)</div>
    </div>
    <p>Precio promedio: {avg_price_usd}/BTC &nbsp;|&nbsp; Portafolio: {portfolio_change_pct}%</p>
    <p>Stack total: <strong>{total_sats} sats</strong> = {total_value_usd}</p>
    <p>Precio BTC: {btc_price_usd} ({btc_weekly_change_pct}% esta semana)</p>
    <div class="cta"><a href="https://magma.app/analytics">Análisis completo</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "📊",
        "priority": "low",
        "category": "reports",
        "sample_data": {
            "week_label": "Apr 14–20, 2025",
            "weekly_sats": "15,432",
            "weekly_usd": "$10.00",
            "avg_price_usd": "$64,800",
            "portfolio_change_pct": "+4.2",
            "total_sats": "432,000",
            "total_value_usd": "$271.30",
            "btc_price_usd": "$64,800",
            "btc_weekly_change_pct": "+4.2",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Your Bitcoin weekly summary — Apr 14–20, 2025",
            "lang": "en",
        },
    },

    "monthly_report": {
        "subject_en": "📈 Monthly Bitcoin report — {month_label}",
        "subject_es": "📈 Reporte mensual de Bitcoin — {month_label}",
        "body_en": (
            "Your Bitcoin monthly report for {month_label}:\n\n"
            "Sats stacked: {monthly_sats}\n"
            "Total invested: {monthly_usd}\n"
            "Avg buy price: {avg_price_usd}/BTC\n"
            "Best day: {best_day} (+{best_day_sats} sats)\n"
            "Streak maintained: {streak_days} days\n"
            "Lessons completed: {lessons_completed}\n\n"
            "Year-to-date stack: {ytd_sats} sats ({ytd_usd})\n"
            "Year-to-date return: {ytd_return_pct}%\n\n"
            "One more month down. Stack accordingly."
        ),
        "body_es": (
            "Tu reporte mensual de Bitcoin para {month_label}:\n\n"
            "Sats apilados: {monthly_sats}\n"
            "Total invertido: {monthly_usd}\n"
            "Precio promedio: {avg_price_usd}/BTC\n"
            "Mejor día: {best_day} (+{best_day_sats} sats)\n"
            "Racha mantenida: {streak_days} días\n"
            "Lecciones completadas: {lessons_completed}\n\n"
            "Stack acumulado en el año: {ytd_sats} sats ({ytd_usd})\n"
            "Retorno acumulado en el año: {ytd_return_pct}%\n\n"
            "Un mes más. Apila en consecuencia."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">📈</span>
    <h1>Monthly Report: {month_label}</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">+{monthly_sats} sats</div>
      <div class="label">{monthly_usd} invested &nbsp;|&nbsp; avg {avg_price_usd}/BTC</div>
    </div>
    <p>Streak: {streak_days} days &nbsp;|&nbsp; Lessons: {lessons_completed}</p>
    <p>YTD stack: <strong>{ytd_sats} sats</strong> ({ytd_usd}) &mdash; {ytd_return_pct}% return</p>
    <div class="cta"><a href="https://magma.app/analytics">Full Report</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header">
    <span class="icon">📈</span>
    <h1>Reporte mensual: {month_label}</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">+{monthly_sats} sats</div>
      <div class="label">{monthly_usd} invertidos &nbsp;|&nbsp; prom {avg_price_usd}/BTC</div>
    </div>
    <p>Racha: {streak_days} días &nbsp;|&nbsp; Lecciones: {lessons_completed}</p>
    <p>Stack YTD: <strong>{ytd_sats} sats</strong> ({ytd_usd}) &mdash; {ytd_return_pct}% retorno</p>
    <div class="cta"><a href="https://magma.app/analytics">Reporte completo</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "📈",
        "priority": "low",
        "category": "reports",
        "sample_data": {
            "month_label": "March 2025",
            "monthly_sats": "62,500",
            "monthly_usd": "$40.00",
            "avg_price_usd": "$64,000",
            "best_day": "March 15",
            "best_day_sats": "8,200",
            "streak_days": "18",
            "lessons_completed": "3",
            "ytd_sats": "185,000",
            "ytd_usd": "$116.00",
            "ytd_return_pct": "+12.4",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Monthly Bitcoin report — March 2025",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # S E C U R I T Y
    # -----------------------------------------------------------------------

    "security_alert": {
        "subject_en": "🔐 Security alert on your Magma account",
        "subject_es": "🔐 Alerta de seguridad en tu cuenta de Magma",
        "body_en": (
            "SECURITY ALERT — Action may be required.\n\n"
            "Event: {security_event_en}\n"
            "Time: {event_time}\n"
            "Location: {event_location}\n"
            "Device: {event_device}\n\n"
            "If this was you, no action is needed.\n\n"
            "If this was NOT you, secure your account immediately:\n"
            "1. Change your Nostr private key\n"
            "2. Review your active sessions\n"
            "3. Contact support at support@magma.app"
        ),
        "body_es": (
            "ALERTA DE SEGURIDAD — Puede requerirse acción.\n\n"
            "Evento: {security_event_es}\n"
            "Hora: {event_time}\n"
            "Ubicación: {event_location}\n"
            "Dispositivo: {event_device}\n\n"
            "Si fuiste tú, no se requiere ninguna acción.\n\n"
            "Si NO fuiste tú, asegura tu cuenta de inmediato:\n"
            "1. Cambia tu clave privada Nostr\n"
            "2. Revisa tus sesiones activas\n"
            "3. Contacta soporte en support@magma.app"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #b71c1c, #4a0000);">
    <span class="icon">🔐</span>
    <h1>Security Alert</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ef5350; font-size:18px;">{security_event_en}</div>
      <div class="label">{event_time} &nbsp;|&nbsp; {event_location} &nbsp;|&nbsp; {event_device}</div>
    </div>
    <p>If this was <strong>not you</strong>, secure your account immediately.</p>
    <div class="cta"><a href="https://magma.app/security" style="background:#b71c1c;">Review Security</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #b71c1c, #4a0000);">
    <span class="icon">🔐</span>
    <h1>Alerta de seguridad</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ef5350; font-size:18px;">{security_event_es}</div>
      <div class="label">{event_time} &nbsp;|&nbsp; {event_location} &nbsp;|&nbsp; {event_device}</div>
    </div>
    <p>Si <strong>no fuiste tú</strong>, asegura tu cuenta de inmediato.</p>
    <div class="cta"><a href="https://magma.app/security" style="background:#b71c1c;">Revisar seguridad</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🔐",
        "priority": "critical",
        "category": "security",
        "sample_data": {
            "security_event_en": "New login from unknown device",
            "security_event_es": "Inicio de sesión nuevo desde dispositivo desconocido",
            "event_time": "2025-04-22 14:32 UTC",
            "event_location": "San Salvador, SV",
            "event_device": "iPhone 15 — iOS 18",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Security alert on your Magma account",
            "lang": "en",
        },
    },

    "new_login": {
        "subject_en": "👤 New login to your Magma account",
        "subject_es": "👤 Nuevo inicio de sesión en tu cuenta Magma",
        "body_en": (
            "A new login was detected on your Magma account.\n\n"
            "Time: {login_time}\n"
            "Device: {device}\n"
            "IP: {ip_address}\n"
            "Location: {location}\n\n"
            "If this was you, everything is fine.\n"
            "If not, please secure your account immediately."
        ),
        "body_es": (
            "Se detectó un nuevo inicio de sesión en tu cuenta Magma.\n\n"
            "Hora: {login_time}\n"
            "Dispositivo: {device}\n"
            "IP: {ip_address}\n"
            "Ubicación: {location}\n\n"
            "Si fuiste tú, todo está bien.\n"
            "Si no, por favor asegura tu cuenta de inmediato."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #1565c0, #0d47a1);">
    <span class="icon">👤</span>
    <h1>New Login Detected</h1>
  </div>
  <div class="body">
    <p>A new session was started on your Magma account.</p>
    <div class="highlight">
      <div class="value" style="color:#42a5f5; font-size:16px;">{device}</div>
      <div class="label">{location} &nbsp;|&nbsp; {login_time}</div>
    </div>
    <p>If this wasn't you, secure your account now.</p>
    <div class="cta"><a href="https://magma.app/security" style="background:#1565c0;">Review Sessions</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #1565c0, #0d47a1);">
    <span class="icon">👤</span>
    <h1>Nuevo inicio de sesión detectado</h1>
  </div>
  <div class="body">
    <p>Se inició una nueva sesión en tu cuenta Magma.</p>
    <div class="highlight">
      <div class="value" style="color:#42a5f5; font-size:16px;">{device}</div>
      <div class="label">{location} &nbsp;|&nbsp; {login_time}</div>
    </div>
    <p>Si no fuiste tú, asegura tu cuenta ahora.</p>
    <div class="cta"><a href="https://magma.app/security" style="background:#1565c0;">Revisar sesiones</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "👤",
        "priority": "high",
        "category": "security",
        "sample_data": {
            "login_time": "2025-04-22 10:15 UTC",
            "device": "Chrome on Windows 11",
            "ip_address": "192.168.1.1",
            "location": "San Salvador, SV",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "New login to your Magma account",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # S Y S T E M
    # -----------------------------------------------------------------------

    "system_maintenance": {
        "subject_en": "🛠 Scheduled maintenance — {maintenance_date}",
        "subject_es": "🛠 Mantenimiento programado — {maintenance_date}",
        "body_en": (
            "Magma will undergo scheduled maintenance.\n\n"
            "Date: {maintenance_date}\n"
            "Duration: {maintenance_duration}\n"
            "Affected services: {affected_services_en}\n\n"
            "During this window, on-chain and Lightning functionality will be "
            "temporarily unavailable. Your funds are safe and will not be affected.\n\n"
            "Thank you for your patience."
        ),
        "body_es": (
            "Magma realizará mantenimiento programado.\n\n"
            "Fecha: {maintenance_date}\n"
            "Duración: {maintenance_duration}\n"
            "Servicios afectados: {affected_services_es}\n\n"
            "Durante esta ventana, la funcionalidad en cadena y Lightning no estará "
            "disponible temporalmente. Tus fondos están seguros.\n\n"
            "Gracias por tu paciencia."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #37474f, #1c2b33);">
    <span class="icon">🛠</span>
    <h1>Scheduled Maintenance</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#90a4ae; font-size:18px;">{maintenance_date}</div>
      <div class="label">Duration: {maintenance_duration}</div>
    </div>
    <p>Affected: {affected_services_en}</p>
    <p>Your funds are <strong>100% safe</strong> during maintenance.</p>
    <div class="cta"><a href="https://magma.app/status" style="background:#37474f;">Check Status</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #37474f, #1c2b33);">
    <span class="icon">🛠</span>
    <h1>Mantenimiento programado</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#90a4ae; font-size:18px;">{maintenance_date}</div>
      <div class="label">Duración: {maintenance_duration}</div>
    </div>
    <p>Afectado: {affected_services_es}</p>
    <p>Tus fondos están <strong>100% seguros</strong> durante el mantenimiento.</p>
    <div class="cta"><a href="https://magma.app/status" style="background:#37474f;">Ver estado</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🛠",
        "priority": "normal",
        "category": "system",
        "sample_data": {
            "maintenance_date": "2025-04-25 02:00–04:00 UTC",
            "maintenance_duration": "~2 hours",
            "affected_services_en": "Savings, Lightning payments, Portfolio",
            "affected_services_es": "Ahorros, pagos Lightning, Portafolio",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Scheduled maintenance — 2025-04-25",
            "lang": "en",
        },
    },

    "service_restored": {
        "subject_en": "✅ Magma services restored — all systems operational",
        "subject_es": "✅ Servicios de Magma restaurados — todos los sistemas operativos",
        "body_en": (
            "Maintenance is complete. All Magma services are now operational.\n\n"
            "Downtime: {downtime_duration}\n"
            "Restored at: {restored_at}\n\n"
            "Thank you for your patience. Stack sats!"
        ),
        "body_es": (
            "El mantenimiento está completo. Todos los servicios de Magma están operativos.\n\n"
            "Tiempo de inactividad: {downtime_duration}\n"
            "Restaurado a las: {restored_at}\n\n"
            "Gracias por tu paciencia. ¡Apila sats!"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #2e7d32, #1b5e20);">
    <span class="icon">✅</span>
    <h1>All Systems Operational</h1>
  </div>
  <div class="body">
    <p>Magma is back online. All services have been fully restored.</p>
    <div class="highlight">
      <div class="value" style="color:#66bb6a;">Online</div>
      <div class="label">Restored at {restored_at} &nbsp;|&nbsp; Downtime: {downtime_duration}</div>
    </div>
    <div class="cta"><a href="https://magma.app" style="background:#2e7d32;">Open Magma</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #2e7d32, #1b5e20);">
    <span class="icon">✅</span>
    <h1>Todos los sistemas operativos</h1>
  </div>
  <div class="body">
    <p>Magma está de vuelta en línea. Todos los servicios han sido restaurados.</p>
    <div class="highlight">
      <div class="value" style="color:#66bb6a;">En línea</div>
      <div class="label">Restaurado a las {restored_at} &nbsp;|&nbsp; Inactividad: {downtime_duration}</div>
    </div>
    <div class="cta"><a href="https://magma.app" style="background:#2e7d32;">Abrir Magma</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "✅",
        "priority": "normal",
        "category": "system",
        "sample_data": {
            "downtime_duration": "1h 47m",
            "restored_at": "2025-04-25 03:47 UTC",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Magma services restored — all systems operational",
            "lang": "en",
        },
    },

    # -----------------------------------------------------------------------
    # M A R K E T   E V E N T S
    # -----------------------------------------------------------------------

    "halving_countdown": {
        "subject_en": "⏳ Bitcoin halving in {days_until_halving} days",
        "subject_es": "⏳ Halving de Bitcoin en {days_until_halving} días",
        "body_en": (
            "The next Bitcoin halving is approaching!\n\n"
            "Days until halving: {days_until_halving}\n"
            "Estimated halving date: {halving_date}\n"
            "Current block height: {current_block}\n"
            "Blocks remaining: {blocks_remaining}\n"
            "Current subsidy: {current_subsidy} BTC/block\n"
            "Post-halving subsidy: {post_halving_subsidy} BTC/block\n\n"
            "The halving reduces new Bitcoin supply by 50%. Historically, "
            "it has preceded significant price appreciation. Stack accordingly."
        ),
        "body_es": (
            "¡El próximo halving de Bitcoin se acerca!\n\n"
            "Días hasta el halving: {days_until_halving}\n"
            "Fecha estimada de halving: {halving_date}\n"
            "Altura de bloque actual: {current_block}\n"
            "Bloques restantes: {blocks_remaining}\n"
            "Subsidio actual: {current_subsidy} BTC/bloque\n"
            "Subsidio post-halving: {post_halving_subsidy} BTC/bloque\n\n"
            "El halving reduce el nuevo suministro de Bitcoin en un 50%. "
            "Históricamente ha precedido apreciaciones significativas del precio."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #f57f17, #e65100);">
    <span class="icon">⏳</span>
    <h1>Bitcoin Halving Countdown</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{days_until_halving} days</div>
      <div class="label">Until the next halving — est. {halving_date}</div>
    </div>
    <p>Block {current_block} of {halving_target_block} &nbsp;|&nbsp; {blocks_remaining} blocks to go</p>
    <p>Subsidy drops: {current_subsidy} → {post_halving_subsidy} BTC/block</p>
    <p>Stack now before supply shock hits.</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#f57f17;">Stack Sats</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #f57f17, #e65100);">
    <span class="icon">⏳</span>
    <h1>Cuenta regresiva del halving</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{days_until_halving} días</div>
      <div class="label">Hasta el próximo halving — est. {halving_date}</div>
    </div>
    <p>Bloque {current_block} de {halving_target_block} &nbsp;|&nbsp; {blocks_remaining} bloques restantes</p>
    <p>El subsidio cae: {current_subsidy} → {post_halving_subsidy} BTC/bloque</p>
    <p>Apila ahora antes del shock de oferta.</p>
    <div class="cta"><a href="https://magma.app/savings" style="background:#f57f17;">Apilar sats</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "⏳",
        "priority": "normal",
        "category": "market",
        "sample_data": {
            "days_until_halving": "30",
            "halving_date": "April 20, 2028",
            "current_block": "930,000",
            "halving_target_block": "1,050,000",
            "blocks_remaining": "120,000",
            "current_subsidy": "3.125",
            "post_halving_subsidy": "1.5625",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Bitcoin halving in 30 days",
            "lang": "en",
        },
    },

    "halving_occurred": {
        "subject_en": "🧡 Bitcoin halving just happened! Block {block_height}",
        "subject_es": "🧡 ¡El halving de Bitcoin acaba de ocurrir! Bloque {block_height}",
        "body_en": (
            "History was made. The Bitcoin halving just occurred at block {block_height}.\n\n"
            "New block subsidy: {new_subsidy} BTC/block\n"
            "Previous subsidy: {previous_subsidy} BTC/block\n"
            "Total Bitcoin mined: ~{total_mined_btc} BTC\n"
            "Remaining to mine: ~{remaining_btc} BTC\n\n"
            "The supply cut has happened. Stack sats. HODL.\n"
            "You are early — less than 2 million Bitcoin remain to be mined."
        ),
        "body_es": (
            "La historia fue hecha. El halving de Bitcoin acaba de ocurrir en el bloque {block_height}.\n\n"
            "Nuevo subsidio de bloque: {new_subsidy} BTC/bloque\n"
            "Subsidio anterior: {previous_subsidy} BTC/bloque\n"
            "Bitcoin total minado: ~{total_mined_btc} BTC\n"
            "Restante por minar: ~{remaining_btc} BTC\n\n"
            "El corte de suministro ha ocurrido. Apila sats. HODL.\n"
            "Eres temprano — quedan menos de 2 millones de Bitcoin por minar."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #ff6b00, #cc2200);">
    <span class="icon">🧡</span>
    <h1>The Bitcoin Halving Has Occurred!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">Block {block_height}</div>
      <div class="label">New subsidy: {new_subsidy} BTC &nbsp;|&nbsp; Was: {previous_subsidy} BTC</div>
    </div>
    <p>Total mined: ~{total_mined_btc} BTC &nbsp;|&nbsp; Remaining: ~{remaining_btc} BTC</p>
    <p>This is one of Bitcoin's most anticipated events. The supply cut is now live.</p>
    <div class="cta"><a href="https://magma.app/portfolio">View Your Stack</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #ff6b00, #cc2200);">
    <span class="icon">🧡</span>
    <h1>¡El halving de Bitcoin ha ocurrido!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">Bloque {block_height}</div>
      <div class="label">Nuevo subsidio: {new_subsidy} BTC &nbsp;|&nbsp; Era: {previous_subsidy} BTC</div>
    </div>
    <p>Total minado: ~{total_mined_btc} BTC &nbsp;|&nbsp; Restante: ~{remaining_btc} BTC</p>
    <p>Este es uno de los eventos más esperados de Bitcoin. El corte de suministro ya está activo.</p>
    <div class="cta"><a href="https://magma.app/portfolio">Ver tu stack</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🧡",
        "priority": "high",
        "category": "market",
        "sample_data": {
            "block_height": "1,050,000",
            "new_subsidy": "1.5625",
            "previous_subsidy": "3.125",
            "total_mined_btc": "~19,950,000",
            "remaining_btc": "~1,050,000",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Bitcoin halving just happened! Block 1,050,000",
            "lang": "en",
        },
    },

    "market_ath": {
        "subject_en": "🌋 Bitcoin hits new all-time high: {ath_price_usd}",
        "subject_es": "🌋 Bitcoin alcanza nuevo máximo histórico: {ath_price_usd}",
        "body_en": (
            "Bitcoin has reached a new all-time high!\n\n"
            "New ATH: {ath_price_usd}\n"
            "Previous ATH: {previous_ath_usd}\n"
            "Gain over previous ATH: {ath_gain_pct}%\n\n"
            "Your stack is currently worth: {stack_value_usd} ({user_sats} sats)\n"
            "Your unrealized gain: {unrealized_gain_pct}% ({unrealized_gain_usd})\n\n"
            "Price discovery mode. HODL. The volcano is erupting."
        ),
        "body_es": (
            "¡Bitcoin ha alcanzado un nuevo máximo histórico!\n\n"
            "Nuevo ATH: {ath_price_usd}\n"
            "ATH anterior: {previous_ath_usd}\n"
            "Ganancia sobre ATH anterior: {ath_gain_pct}%\n\n"
            "Tu stack vale actualmente: {stack_value_usd} ({user_sats} sats)\n"
            "Tu ganancia no realizada: {unrealized_gain_pct}% ({unrealized_gain_usd})\n\n"
            "Modo de descubrimiento de precio. HODL. El volcán está en erupción."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #ff6b00, #ff0000);">
    <span class="icon">🌋</span>
    <h1>New All-Time High!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{ath_price_usd}</div>
      <div class="label">New ATH &nbsp;|&nbsp; +{ath_gain_pct}% vs previous ({previous_ath_usd})</div>
    </div>
    <p>Your stack: <strong>{stack_value_usd}</strong> ({user_sats} sats)</p>
    <p>Unrealized gain: <strong style="color:#ff6b00;">{unrealized_gain_pct}%</strong> ({unrealized_gain_usd})</p>
    <div class="cta"><a href="https://magma.app/portfolio">View Portfolio</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #ff6b00, #ff0000);">
    <span class="icon">🌋</span>
    <h1>¡Nuevo máximo histórico!</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value">{ath_price_usd}</div>
      <div class="label">Nuevo ATH &nbsp;|&nbsp; +{ath_gain_pct}% vs anterior ({previous_ath_usd})</div>
    </div>
    <p>Tu stack: <strong>{stack_value_usd}</strong> ({user_sats} sats)</p>
    <p>Ganancia no realizada: <strong style="color:#ff6b00;">{unrealized_gain_pct}%</strong> ({unrealized_gain_usd})</p>
    <div class="cta"><a href="https://magma.app/portfolio">Ver portafolio</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🌋",
        "priority": "high",
        "category": "market",
        "sample_data": {
            "ath_price_usd": "$109,000",
            "previous_ath_usd": "$73,800",
            "ath_gain_pct": "+47.7",
            "user_sats": "500,000",
            "stack_value_usd": "$545.00",
            "unrealized_gain_pct": "+68.4",
            "unrealized_gain_usd": "+$221.00",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Bitcoin hits new all-time high: $109,000",
            "lang": "en",
        },
    },

    "whale_alert": {
        "subject_en": "🐋 Whale alert: {amount_btc} BTC moved on-chain",
        "subject_es": "🐋 Alerta ballena: {amount_btc} BTC movidos en cadena",
        "body_en": (
            "A large Bitcoin transaction has been detected.\n\n"
            "Amount: {amount_btc} BTC ({amount_usd} USD)\n"
            "From: {from_label}\n"
            "To: {to_label}\n"
            "Transaction: {txid_short}...\n"
            "Confirmations: {confirmations}\n\n"
            "Large movements can signal exchange inflows/outflows and may affect "
            "short-term price action. Stay informed, not emotional."
        ),
        "body_es": (
            "Se ha detectado una gran transacción de Bitcoin.\n\n"
            "Cantidad: {amount_btc} BTC ({amount_usd} USD)\n"
            "De: {from_label}\n"
            "A: {to_label}\n"
            "Transacción: {txid_short}...\n"
            "Confirmaciones: {confirmations}\n\n"
            "Los grandes movimientos pueden indicar flujos de entrada/salida de "
            "exchanges y pueden afectar la acción del precio a corto plazo. "
            "Mantente informado, no emocional."
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #0d47a1, #002171);">
    <span class="icon">🐋</span>
    <h1>Whale Alert</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#42a5f5;">{amount_btc} BTC</div>
      <div class="label">{amount_usd} &nbsp;|&nbsp; {from_label} → {to_label}</div>
    </div>
    <p>TXID: <code style="font-size:11px; color:#aaa;">{txid_short}...</code> &nbsp;|&nbsp; {confirmations} confirmations</p>
    <p>Large moves can signal exchange flows. HODL through the noise.</p>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #0d47a1, #002171);">
    <span class="icon">🐋</span>
    <h1>Alerta ballena</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#42a5f5;">{amount_btc} BTC</div>
      <div class="label">{amount_usd} &nbsp;|&nbsp; {from_label} → {to_label}</div>
    </div>
    <p>TXID: <code style="font-size:11px; color:#aaa;">{txid_short}...</code> &nbsp;|&nbsp; {confirmations} confirmaciones</p>
    <p>Los grandes movimientos pueden indicar flujos de exchange. Mantén el HODL.</p>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "🐋",
        "priority": "low",
        "category": "market",
        "sample_data": {
            "amount_btc": "1,500",
            "amount_usd": "$97,500,000",
            "from_label": "Unknown Wallet",
            "to_label": "Coinbase",
            "txid_short": "a1b2c3d4e5f6",
            "confirmations": "3",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Whale alert: 1,500 BTC moved on-chain",
            "lang": "en",
        },
    },

    "market_crash": {
        "subject_en": "📉 Bitcoin down {drop_pct}% — DCA opportunity?",
        "subject_es": "📉 Bitcoin baja {drop_pct}% — ¿Oportunidad de DCA?",
        "body_en": (
            "Bitcoin has experienced a significant price drop.\n\n"
            "Current price: {current_price_usd}\n"
            "Drop from recent high: {drop_pct}%\n"
            "Drop from ATH: {drop_from_ath_pct}%\n\n"
            "Your stack: {user_sats} sats (now worth {stack_value_usd})\n\n"
            "Remember: Every Bitcoin bear market in history has been followed by "
            "a new all-time high. Volatility is the price we pay for 21 million cap.\n\n"
            "Consider: Is this a DCA opportunity for you?"
        ),
        "body_es": (
            "Bitcoin ha experimentado una caída significativa de precio.\n\n"
            "Precio actual: {current_price_usd}\n"
            "Caída desde máximo reciente: {drop_pct}%\n"
            "Caída desde ATH: {drop_from_ath_pct}%\n\n"
            "Tu stack: {user_sats} sats (ahora vale {stack_value_usd})\n\n"
            "Recuerda: Cada mercado bajista de Bitcoin en la historia ha sido seguido "
            "por un nuevo máximo histórico. La volatilidad es el precio que pagamos "
            "por el límite de 21 millones.\n\n"
            "Considera: ¿Es esta una oportunidad de DCA para ti?"
        ),
        "body_html_en": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #37474f, #263238);">
    <span class="icon">📉</span>
    <h1>Market Dip Alert</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ef5350;">{current_price_usd}</div>
      <div class="label">-{drop_pct}% from recent high &nbsp;|&nbsp; -{drop_from_ath_pct}% from ATH</div>
    </div>
    <p>Your stack: {user_sats} sats = {stack_value_usd}</p>
    <p>Every bear market in Bitcoin history ended with a new ATH. HODL or DCA.</p>
    <div class="cta"><a href="https://magma.app/savings">Stack More Sats</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "body_html_es": (
            _HTML_HEADER
            + """
  <div class="header" style="background: linear-gradient(135deg, #37474f, #263238);">
    <span class="icon">📉</span>
    <h1>Alerta de caída del mercado</h1>
  </div>
  <div class="body">
    <div class="highlight">
      <div class="value" style="color:#ef5350;">{current_price_usd}</div>
      <div class="label">-{drop_pct}% desde máximo reciente &nbsp;|&nbsp; -{drop_from_ath_pct}% desde ATH</div>
    </div>
    <p>Tu stack: {user_sats} sats = {stack_value_usd}</p>
    <p>Cada mercado bajista de Bitcoin terminó con un nuevo ATH. HODL o DCA.</p>
    <div class="cta"><a href="https://magma.app/savings">Apilar más sats</a></div>
  </div>
"""
            + _HTML_FOOTER
        ),
        "icon": "📉",
        "priority": "normal",
        "category": "market",
        "sample_data": {
            "current_price_usd": "$42,000",
            "drop_pct": "30",
            "drop_from_ath_pct": "43",
            "user_sats": "500,000",
            "stack_value_usd": "$210.00",
            "unsubscribe_url": "https://magma.app/unsubscribe/token",
            "subject": "Bitcoin down 30% — DCA opportunity?",
            "lang": "en",
        },
    },
}
